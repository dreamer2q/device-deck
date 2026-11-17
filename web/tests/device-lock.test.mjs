import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createContext, runInContext } from 'node:vm'

function loadLock(api) {
  const document = new EventTarget()
  document.visibilityState = 'hidden'
  const window = new EventTarget()
  const cleanup = []
  let kicked = 0
  const context = createContext({
    document, window, api, Math,
    ref: value => ({ value }),
    onBeforeUnmount: fn => cleanup.push(fn),
    setInterval: () => 1, clearInterval() {},
  })
  const source = readFileSync(new URL('../src/lib/useDeviceLock.js', import.meta.url), 'utf8')
    .replace(/^import .*$/gm, '').replace('export function', 'function')
  const create = runInContext(`${source}\n;useDeviceLock`, context)
  const lock = create('test-device', { holder: 'this-tab', onKicked: () => kicked++ })
  return { lock, document, window, get kicked() { return kicked }, async cleanup() {
    for (const fn of cleanup.reverse()) await fn()
  } }
}

test('a hidden tab defers ownership without reporting a conflict; foreground resumes and releases', async () => {
  let acquired = 0, released = 0
  const env = loadLock({
    async acquireLock() { acquired++; return { token: 'test-lease' } },
    async releaseLock() { released++ },
  })
  assert.equal(await env.lock.acquire(), null)
  assert.equal(await env.lock.recover(), false)
  assert.equal(acquired, 0)
  assert.equal(env.lock.readonly.value, false)
  assert.equal(env.kicked, 0)
  env.document.visibilityState = 'visible'
  env.document.dispatchEvent(new Event('visibilitychange'))
  await new Promise(resolve => setImmediate(resolve))
  assert.equal(acquired, 1)
  assert.equal(env.lock.token.value, 'test-lease')
  assert.equal(env.lock.error.value, null)
  await env.cleanup()
  assert.equal(released, 1)
})

test('only an actual ownership conflict marks the device read only', async () => {
  const env = loadLock({ async acquireLock() { throw { status: 409, detail: 'another tab owns it' } } })
  env.document.visibilityState = 'visible'
  assert.equal(await env.lock.recover(), false)
  assert.equal(env.lock.token.value, null)
  assert.equal(env.lock.readonly.value, true)
  assert.equal(env.kicked, 1)
  await env.cleanup()
})

test('transport failure is not mislabeled as another device owner', async () => {
  const env = loadLock({ async acquireLock() { throw new Error('offline') } })
  env.document.visibilityState = 'visible'
  await assert.rejects(env.lock.acquire(), /offline/)
  assert.equal(env.lock.readonly.value, false)
  assert.equal(env.kicked, 0)
  await env.cleanup()
})

import test from 'node:test'
import assert from 'node:assert/strict'
import { mergeResources, resourceCanOpen, resourceStatus, filterResources } from '../src/lib/deviceResources.js'
import { LIFE } from './fixtures/vmLifecycleFixtures.mjs'

const agents = [{ agent_id: 'mac', agent_name: 'Test Mac' }]
const vm = { id: 'v1', platform: 'ios_sim', assigned_agent_id: 'mac', alias: 'iOS regression', lifecycle: LIFE.running }
const live = { serial: 'udid', platform: 'ios_sim', agent_id: 'mac', status: 'online', effective_status: 'online', extra: { vm_instance_id: 'v1', is_virtual: true, readiness: { ready: true } } }

test('one resource survives a simulator stopping and rebooting with stable identity', () => {
  const running = mergeResources([live], [vm], agents)
  const stopped = mergeResources([], [{ ...vm, lifecycle: LIFE.stopped }], agents)
  assert.equal(running.length, 1)
  assert.equal(stopped.length, 1)
  assert.equal(running[0].resource_id, stopped[0].resource_id)
  assert.equal(resourceCanOpen(running[0]), true)
  assert.equal(resourceCanOpen(stopped[0]), false)
  assert.equal(resourceStatus(stopped[0]).label, '已关机')
})

test('a stale device from a different host cannot control the VM', () => {
  const rows = mergeResources([{ ...live, agent_id: 'other' }], [vm], agents)
  assert.equal(rows.length, 2)
  assert.equal(rows[0].serial, '')
  assert.equal(rows.every(d => !resourceCanOpen(d)), true)
  assert.equal(resourceStatus(rows[1]).group, 'not_ready')
})

test('lifecycle is authoritative and missing lifecycle fails closed', () => {
  for (const lifecycle of [LIFE.starting, LIFE.unknownOffline, undefined]) {
    const [d] = mergeResources([live], [{ ...vm, lifecycle }], agents)
    assert.equal(resourceCanOpen(d), false)
    assert.notEqual(resourceStatus(d).group, 'online')
  }
})

test('platform and kind filters distinguish iOS physical from simulator', () => {
  const phone = { ...live, platform: 'ios', serial: 'real', extra: { readiness: { ready: true } } }
  const rows = mergeResources([live, phone], [vm], agents)
  assert.equal(filterResources(rows, { platform: 'ios' }).length, 2)
  assert.equal(filterResources(rows, { platform: 'ios', kind: 'physical' })[0].serial, 'real')
  assert.equal(filterResources(rows, { search: 'regression' }).length, 1)
})

test('WDA host blockers do not mislabel Android or block Simulator for missing physical signing', () => {
  const host = { ...agents[0], ios_environment: { checks: [{ id: 'device_signing', status: 'blocked', title: '真机开发签名' }] } }
  const [d] = mergeResources([{ ...live, extra: { ...live.extra, readiness: { ready: false } } }], [vm], [host])
  assert.equal(resourceStatus(d).label, '控制未就绪')
  const [android] = mergeResources([{ ...live, platform: 'android', extra: { readiness: { ready: false } } }], [], [host])
  assert.equal(resourceStatus(android).label, '控制未就绪')
})

test('a paused or occupied device remains explicit without granting control', () => {
  const [d] = mergeResources([live], [vm], agents)
  assert.equal(resourceStatus({ ...d, lock: { holder_type: 'job', holder: 'run' } }).label, 'Agent 执行中')
  const paused = { ...d, extra: { ...d.extra, mirror_paused: true } }
  assert.equal(resourceCanOpen(paused), false)
  assert.equal(resourceStatus(paused).label, '镜像已暂停')
})

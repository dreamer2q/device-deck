import test from 'node:test'
import assert from 'node:assert/strict'
import { H264Player } from '../src/lib/h264Player.js'

class Decoder {
  constructor(callbacks) { this.callbacks = callbacks; this.decodeQueueSize = 0; this.decoded = [] }
  configure(config) { this.config = config }
  decode(chunk) { this.decoded.push(chunk) }
  close() { this.closed = true }
  reset() { this.resets = (this.resets || 0) + 1; this.decodeQueueSize = 0 }
}
class Chunk { constructor(data) { Object.assign(this, data) } }
const packet = (pts, key = false, extra = {}) => ({ stream_id: 'one', codec: 'avc1.42e01f',
  width: 720, height: 1280, pts, key, data: new Uint8Array([0,0,0,1,0x65]), ...extra })
function player(options = {}) {
  return new H264Player({ canvas: () => ({ width: 720, height: 1280,
    getContext: () => ({ drawImage() {} }) }), Decoder, Chunk, ...options })
}
test('waits for a keyframe; replays cannot rewind established decoder', () => {
  const p = player()
  p.handle(packet(1))
  assert.equal(p.decoder.decoded.length, 0)
  p.handle(packet(2, true)); p.handle(packet(3)); p.handle(packet(2, true))
  assert.deepEqual(p.decoder.decoded.map(x => x.timestamp), [2, 3])
})
test('backlog resets and awaits an independent keyframe', () => {
  const p = player(); p.handle(packet(1, true))
  p.decoder.decodeQueueSize = 7
  p.handle(packet(2)); p.handle(packet(3))
  assert.equal(p.decoder.resets, 1)
  assert.deepEqual(p.decoder.decoded.map(x => x.timestamp), [1])
  p.handle(packet(4, true))
  assert.equal(p.decoder.decoded.at(-1).timestamp, 4)
})
test('rotation changes decoder and closes every rendered or stale frame', () => {
  const p = player(); p.handle(packet(1, true))
  const old = p.decoder
  p.handle(packet(2, true, { width: 1280, height: 720 }))
  assert.ok(old.closed)
  let closed = 0
  old.callbacks.output({ close() { closed++ } })
  p.decoder.callbacks.output({ displayWidth: 1280, displayHeight: 720, close() { closed++ } })
  assert.equal(closed, 2)
})

// Annex-B H.264 access units; no MP4 muxing or playback buffer.
import { mediaBytes } from './mirrorWire.js'

export class H264Player {
  constructor({ canvas, onFrame, onError, onResync, Decoder = globalThis.VideoDecoder,
    Chunk = globalThis.EncodedVideoChunk }) {
    Object.assign(this, { canvas, onFrame, onError, onResync, Decoder, Chunk })
    this.lastPts = -1
    this.needsKey = true
    this.generation = 0
  }
  reset() {
    this.generation++
    try { this.decoder?.close() } catch {}
    this.decoder = null
    this.signature = null
    this.lastPts = -1
    this.needsKey = true
  }
  handle(msg) {
    if (!this.Decoder || !this.Chunk) {
      this.onError?.('当前浏览器不支持 WebCodecs，请使用新版 Chrome 或 Edge')
      return
    }
    const signature = `${msg.stream_id}:${msg.codec}:${msg.width}x${msg.height}`
    if (signature !== this.signature) {
      this.reset()
      this.signature = signature
      const generation = this.generation
      this.decoder = new this.Decoder({
        output: frame => {
          try {
            if (generation !== this.generation) return
            const canvas = this.canvas()
            if (!canvas) return
            if (canvas.width !== frame.displayWidth) canvas.width = frame.displayWidth
            if (canvas.height !== frame.displayHeight) canvas.height = frame.displayHeight
            canvas.getContext('2d', { alpha: false, desynchronized: true }).drawImage(frame, 0, 0)
            this.onFrame?.({ width: canvas.width, height: canvas.height,
              queue: this.decoder?.decodeQueueSize || 0, pts: frame.timestamp })
          } finally { frame.close() }
        },
        error: error => { this.reset(); this.onError?.(error.message); this.onResync?.() },
      })
      try {
        this.decoder.configure({ codec: msg.codec, optimizeForLatency: true,
          hardwareAcceleration: 'no-preference' })
      } catch (error) {
        this.reset(); this.onError?.(error.message); return
      }
    }
    // Replayed GOPs for new viewers must not make established viewers go back.
    if (msg.pts <= this.lastPts) return
    if (this.decoder.decodeQueueSize > 6) {
      this.decoder.reset()
      this.decoder.configure({ codec: msg.codec, optimizeForLatency: true })
      this.needsKey = true
    }
    if (this.needsKey && !msg.key) return
    try {
      this.decoder.decode(new this.Chunk({ type: msg.key ? 'key' : 'delta',
        timestamp: msg.pts, data: mediaBytes(msg.data) }))
      this.lastPts = msg.pts
      this.needsKey = false
    } catch (error) { this.reset(); this.onError?.(error.message); this.onResync?.() }
  }
}

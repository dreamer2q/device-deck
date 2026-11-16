// 浏览器侧 /ws/browser/{serial} 订阅封装，带自动重连。
// 用法：const sub = openDeviceStream('S1', { onMessage, onOpen, onClose })
//      ...  sub.close()

const BACKOFF = [500, 1000, 2000, 5000, 10000]
import { decodeMirrorMessage } from './mirrorWire.js'

export function openDeviceStream(serial, { onMessage, onOpen, onClose } = {}) {
  let stopped = false
  let attempt = 0
  let socket = null
  let pingTimer = null
  let inputSequence = 0

  function scheduleReconnect() {
    if (stopped) return
    const delay = BACKOFF[Math.min(attempt, BACKOFF.length - 1)]
    attempt += 1
    setTimeout(connect, delay)
  }

  function connect() {
    if (stopped) return
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${proto}://${location.host}/ws/browser/${encodeURIComponent(serial)}?mirror=binary-v1`
    socket = new WebSocket(url)
    socket.binaryType = 'arraybuffer'

    socket.onopen = () => {
      attempt = 0
      if (onOpen) onOpen()
      if (pingTimer) clearInterval(pingTimer)
      pingTimer = setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: 'ping', ts: Date.now() / 1000 }))
        }
      }, 15000)
    }

    socket.onmessage = (evt) => {
      let parsed
      try {
        parsed = typeof evt.data === 'string' ? JSON.parse(evt.data) : decodeMirrorMessage(evt.data)
      } catch {
        return
      }
      if (parsed && parsed.type === 'pong') return
      if (onMessage) onMessage(parsed)
    }

    socket.onclose = () => {
      if (pingTimer) {
        clearInterval(pingTimer)
        pingTimer = null
      }
      if (onClose) onClose()
      scheduleReconnect()
    }

    socket.onerror = () => {
      // 让 onclose 统一处理重连
      try {
        socket && socket.close()
      } catch {}
    }
  }

  connect()

  return {
    touch(params) {
      if (!socket || socket.readyState !== WebSocket.OPEN) return false
      if (socket.bufferedAmount > 65536) { socket.close(4002, "input backpressure"); return false }
      socket.send(JSON.stringify({ type: "touch", ...params, seq: ++inputSequence }))
      return true
    },
    resync() {
      // A reconnect replays the Agent's init and resumes at its next keyframe.
      // The HTTP device lease remains held by useDeviceLock.
      if (socket && socket.readyState === WebSocket.OPEN) socket.close(4001, 'mirror resync')
    },
    close() {
      stopped = true
      if (pingTimer) clearInterval(pingTimer)
      if (socket) socket.close()
    },
  }
}

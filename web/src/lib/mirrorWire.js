// APM1 browser mirror envelopes. The JSON form remains supported for old servers.
const decoder = new TextDecoder('utf-8', { fatal: true })
const mediaTypes = new Set(['video_init', 'video_segment', 'mirror_jpeg', 'h264_packet'])

export function mediaBytes(value) {
  if (value instanceof Uint8Array) return value
  if (value instanceof ArrayBuffer) return new Uint8Array(value)
  if (typeof value !== 'string') throw new TypeError('Invalid mirror media')
  const bin = atob(value)
  return Uint8Array.from(bin, c => c.charCodeAt(0))
}

export function decodeMirrorMessage(buffer) {
  const bytes = new Uint8Array(buffer)
  if (bytes.length < 8 || bytes[0] !== 65 || bytes[1] !== 80 || bytes[2] !== 77 || bytes[3] !== 49) {
    throw new Error('Invalid mirror envelope')
  }
  const headerLength = new DataView(buffer).getUint32(4)
  if (!headerLength || headerLength > 16384 || 8 + headerLength > bytes.length) {
    throw new Error('Invalid mirror header length')
  }
  const header = JSON.parse(decoder.decode(bytes.subarray(8, 8 + headerLength)))
  if (!mediaTypes.has(header?.type)) throw new Error('Invalid mirror message type')
  return { ...header, data: bytes.subarray(8 + headerLength) }
}

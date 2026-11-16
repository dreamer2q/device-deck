// Evaluate in the existing foreground workbench after opening latency_target on
// the Android device. Measures synthetic browser pointer-down to decoded canvas
// pixels, including device app response; excludes OS input and physical scanout.
(async () => {
  const source = [...document.querySelectorAll('canvas,video')].find(el =>
    el.getBoundingClientRect().height > 50 && (el.videoWidth || el.width))
  if (!source || document.visibilityState !== 'visible') throw Error('Visible workbench required')
  const c = document.createElement('canvas')
  c.width = source.videoWidth || source.width
  c.height = source.videoHeight || source.height
  const ctx = c.getContext('2d', { willReadFrequently: true })
  const color = () => {
    ctx.drawImage(source, 0, 0)
    const p = ctx.getImageData(Math.floor(c.width * .25), Math.floor(c.height * .65), 1, 1).data
    return p[0] > p[1] ? 'red' : 'green'
  }
  const wait = ms => new Promise(r => setTimeout(r, ms))
  const rect = source.getBoundingClientRect()
  const point = { clientX: rect.x + rect.width / 2, clientY: rect.y + rect.height * .65,
    pointerId: 79, pointerType: 'mouse', button: 0, bubbles: true, cancelable: true }
  const samples = []
  for (let i = 0; i < 30; i++) {
    const before = color(), start = performance.now()
    source.dispatchEvent(new PointerEvent('pointerdown', { ...point, buttons: 1 }))
    await wait(40)
    source.dispatchEvent(new PointerEvent('pointerup', { ...point, buttons: 0 }))
    let changed = false
    while (performance.now() - start < 3000) {
      if (color() !== before) { changed = true; break }
      await wait(8)
    }
    samples.push({ ms: Math.round((performance.now() - start) * 10) / 10, changed })
    await wait(160)
  }
  const times = samples.filter(x => x.changed).map(x => x.ms).sort((a,b) => a-b)
  const result = { kind: source.tagName, dimensions: [c.width,c.height], samples,
    success: times.length, p50_ms: times[Math.ceil(times.length*.5)-1],
    p95_ms: times[Math.ceil(times.length*.95)-1], visibility: document.visibilityState,
    boundary: 'synthetic pointer-down to decoded device-app pixels; physical scanout excluded' }
  window.__deviceDeckLatency = result
  return result
})()

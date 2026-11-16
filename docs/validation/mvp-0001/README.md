# MVP validation — 2026-11-17

This document distinguishes implementation, automated checks, live lab evidence
and user acceptance. The operator requested autonomous implementation and GitHub
publication; user acceptance of the resulting UI is still pending.

## Android comparison

Raw samples: [latency.json](latency.json). Test tools:
[Android browser target](../../../tools/latency_target.py) and
[foreground browser sampling](../../../tools/browser_latency.js).

On the same Android 10 physical phone over USB, the existing compact ai-phone
and DeviceDeck used the same server mirror configuration (440×960, 30 FPS limit
and the same bitrate). Each performed 30 synthetic clicks on a test page which
changes background color on pointer input. The receiving browser stayed visible.
Sampling polled decoded image pixels at approximately 8ms intervals.

| Path | Successful samples | P50 | P95 |
|---|---:|---:|---:|
| Existing fMP4/MSE | 30/30 | 833.3ms | 1039.4ms |
| Device H.264 / WebCodecs | 30/30 | 70.3ms | 95.6ms |

This is about a 90.8% P95 reduction **in this comparison**. It combines changes
to encoding selection, transport/playback and input dispatch, so it does not
isolate any single optimization. The boundary starts at a synthetic browser
pointer-down and ends when decoded device-page pixels change. The script holds
the pointer for 40ms before pointer-up. Physical input hardware and display
scanout are excluded; this is not a full physical click-to-photon measurement.
Only one phone and one local network path are represented. A native scrcpy
window comparison, WAN/packet-loss measurements and fleet load tests remain open.

A separate gesture check observed a changed phone screen while the pointer was
still held, before pointer-up. Six movement events produced four separately
sampled color changes at 100ms intervals; this demonstrates live movement rather
than requiring a complete swipe to be submitted after release. It does not mean
one rendered frame was observed for every movement event.

The standalone raw engine also produced a first independent H.264 keyframe in
approximately 0.783 seconds; parsed 592×1280 dimensions matched independent PyAV
decoding. This was a different probe configuration, not the 440×960 comparison.

## Ownership and live workflow checks

- Authenticated browser displayed real physical-device H.264 in a canvas.
- An owned live WebSocket dispatched continuous input successfully.
- A competing owner received HTTP 409.
- Releasing the lease caused input on the already-open socket to be rejected
  with `lease_lost`, rather than trusting connection-time authorization forever.
- Isolated tests cover expiry cancellation without further client messages,
  invalid/duplicate sequence rejection, rotation cleanup, and an old owner's
  cancellation arriving after a new owner has touched the screen.
- Mirror maintenance refuses an occupied device, prevents reacquisition while
  paused and can resume it; existing read-only viewers cannot block maintenance.
- A native Agent read-only screen task completed successfully in one step,
  preserving the existing model/runner workflow. This is a smoke test, not an
  AI task benchmark or a claim of arbitrary-app reliability.

## Automated checks

The initial web checks passed 122 tests; the production build passed. Dependency
updates within the existing declared ranges yielded a zero-finding npm audit at
the time checked. Relevant backend checks passed before deployment.

An initial broad backend run completed with 3287 passing tests, 43 skipped and
one expected failure; its 12 failures were missing frontend source/test files
in the review upload. Uploading those files and rerunning the affected module
passed all 12. A final complete review run is recorded below when finished; do
not infer a single green full-suite run from that initial aggregate.

## Deployment and limits

The lab entry keeps its existing HTTPS proxy and credentials. Central UI/API and
device nodes use the DeviceDeck source changes, retaining the existing database,
device aliases, task history and VM identity. Backups of changed source, web
assets and service flags are kept on the corresponding hosts.

iOS remains registered with its WDA not-ready state: full Xcode/signing is still
missing. This MVP does not claim working iOS remote control. The Android media
path remains a central binary WebSocket relay, not WebRTC or direct per-region
media. The pause flag is temporary in-memory state and clears on central restart.

## Final verification

- Final full backend run: **3301 passed, 43 skipped, 1 xfailed**, approximately
  328 seconds, using isolated SQLite test databases and the declared test/Harmony
  dependencies in the review environment. No live database was used by pytest.
- Frontend: **122 tests passed** and production build passed. Browser review
  showed the compact workbench and real H.264 canvas without a decoder error.
- The existing Android 15 emulator was stopped through the platform, its Agent
  updated, and the **same VM ID** started again. The browser rendered its new
  WebCodecs stream; a browser pointer click opened Android Settings, independently
  confirmed by the device's resumed activity. Body-orientation controls were
  exercised and restored; an application that stays portrait is not evidence of
  a landscape-frame performance measurement.
- The standalone production web entry was started temporarily against an
  **isolated database**, checked for anonymous 401, authenticated health 200,
  and authenticated SPA deep-link 200, then stopped. Its authentication helpers
  also passed HTTP/WebSocket/internal-header tests.
- A native Agent screen-reading smoke run completed successfully in one step.
- GitHub publication is the final delivery step; no formal release tag or claim
  of user acceptance is implied by pushing the source.

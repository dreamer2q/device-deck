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

The web checks passed 122 tests and the production build passed. Dependency
updates within the existing declared ranges yielded a zero-finding npm audit at
the time checked. The complete macOS backend run passed 3301 tests, with 43 skipped
and one expected failure, against isolated test databases.

Fresh Linux testing reproduced an intermittent shutdown hang in SQLAlchemy's
aiosqlite connection cleanup with aiosqlite 0.22.1. A pending-task dump ended in
`_terminate_graceful_close()` / `Connection.close()`, consistent with the upstream
[driver shutdown report](https://github.com/wapiti-scanner/wapiti/issues/802).
The test-only dependency is capped at `aiosqlite<0.22`; five consecutive Linux
WebSocket integration runs then passed all 16 tests each. Production uses
asyncpg/PostgreSQL. CI additionally uses a 120-second per-test timeout so an
unexpected teardown hang produces a bounded failure and diagnostic stack.

The complete Linux run also exposed an inherited port-test assumption: a
non-listening `SO_REUSEADDR` binding does not reserve a Linux port against another
reuse-enabled listener. The reservation fixture now uses an exclusive bind, and
a separate Linux test independently binds and listens with a real second socket
to verify the reusable case. Reserved ports, active listeners and reusable
TIME_WAIT ports remain covered; all 22 port tests passed in the isolated Linux
environment. This changes test setup, not production port allocation.

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

- [Final GitHub Linux CI](https://github.com/dreamer2q/device-deck/actions/runs/43936780619)
  passed all three jobs on source commit
  `7c3212faed7cc613489f7a9baa31a68cf18dfb44`: **3302 backend tests passed,
  43 skipped, 1 xfailed**, approximately 340 seconds. Web tests/build and the
  Midscene bridge build also passed. Subsequent publication changes are docs only.
- Final full backend run: **3301 passed, 43 skipped, 1 xfailed**, approximately
  328 seconds on macOS, using isolated SQLite test databases and the declared test/Harmony
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
- Source is published at [dreamer2q/device-deck](https://github.com/dreamer2q/device-deck),
  preserving upstream history and MIT attribution. No formal release tag or claim
  of user acceptance is implied by publishing the source.

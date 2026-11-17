# iOS iteration 0002 validation — 2026-11-17

This records a private test deployment of DeviceDeck 0.1.1, not upstream ai-phone
or a release-wide performance guarantee. User acceptance remains pending.

## Environment

Apple M4, 16GB, macOS15.6.1; official Apple Silicon Xcode26.3 (17C529), selected
Developer directory, archive signature and first-launch setup checked. Installed
ARM64 runtimes:26.2 (23C52),26.3.1 (23D8133, display name26.3). No macOS upgrade.
Only one managed Simulator was started: iPhone17Pro with iOS26.2. Physical iPhone
WDA remains unverified because no valid development signing identity/Team exists.

An existing PDF workload remained active. At one post-test snapshot, memory_pressure
reported58% free, with74GiB internal and506GiB external disk space available.
These are point-in-time observations, not capacity guarantees.

## Actual checks

- Created one configuration using the browser form and dispatched it to the Mac.
- Built/installed/started the Simulator WDA runner without physical-device signing.
  First build took332.4seconds under the existing workload; no fixed25-second promise.
- Received410×892 JPEG frames through Server WebSocket from the1206×2622 Simulator.
- With an ordinary device lease, submitted clicks through the platform HTTP API;
  observed the controlled test page change color and increment its counter.
- Submitted text through the same API; the controlled page's input event reported
  the exact expected validation text. Dispatch acceptance alone was not considered success.
- Stopped and reopened the same Server instance twice. The native UDID remained
  unchanged and a test marker inside the installed WDA application's Documents survived.
  This is application-data evidence for that app, not arbitrary business-app compatibility.
- Agent reconnect reclaimed the same native instance. Failed/unknown states were
  inspected or explicitly stopped; no replacement instance was used to mask them.
- Main-Chrome CDP verified the hidden workbench displays waiting, with no lock or
  media opened. Its connection was retained. Native Windows UI automation stopped
  when its browser-URL verification was unavailable; no further native input was used.

## Simulator measurement boundary

Thirty sequential taps, all30 observed. P50 **428.0ms**, P95 **519.7ms**.
[Raw samples](server-input-samples.json).

The clock starts at a Python client on the Mac submitting HTTP input to the local
Server, and stops when that client receives and decodes a changed WebSocket JPEG.
It includes dispatch, Agent/WDA/app response, capture, transport and client decoding.
It excludes browser pointer dispatch, foreground browser painting, physical scanout
and remote-network latency. It cannot be compared directly with the Android browser
P95 reported for iteration0001. This is an initial Simulator baseline, not an
isolated before/after comparison or completion of PRD-002 AC08.

## Automated checks and deployment limits

132 frontend tests and production build passed. Relevant isolated Linux regressions:
81 discovery tests;62 lifecycle-start tests passed with40 platform-specific skips;
116 WDA/driver/probe tests;102 Simulator-manager tests. Counts overlap other full
suites and must not be summed as unique coverage. GitHub CI is tracked separately.

The UI, Server preflight and mini Agent changes were deployed with backups, after
checking no active user leases/tasks. No schema migration or credential change.
The Mac device Agent uses launchd Interactive classification for interactive device
control; unrelated PDF services were preserved. Local-only test HTTP servers and
validation leases were released after measuring.

Still pending: physical-iPhone signing/control, business-app installation through
the web flow, full foreground workbench interaction/paint baseline, and user acceptance.

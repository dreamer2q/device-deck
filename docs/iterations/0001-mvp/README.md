# DeviceDeck MVP — iteration 0001

Started 2026-11-17 by explicit operator instruction. Status: implemented and lab-validated; publication in progress; user acceptance pending.

DeviceDeck is an independent downstream product based on ai-phone, preserving its
MIT attribution and history. The working name is an implementation choice.
Canonical checkout: `projects/device-deck`; do not develop parallel source copies.

## Scope

- Keep the existing compact device inventory, node registration/heartbeat,
  acquisition/release, app tools, task history and native Agent integration.
- Replace the interactive Android path with packetized device H.264 and browser
  WebCodecs, without FFmpeg re-encoding or MP4 fragment buffering.
- Stream continuous down/move/up over an existing authorized WebSocket, validate
  the current lease on every input, cancel held touches on loss/release/expiry.
- Keep iOS WDA and its explicit readiness prerequisites.
- Provide useful diagnostics and mirror recovery as basic maintenance.
- Validate actual devices, browser flows and ownership conflicts; publish an
  independent GitHub repository after implementation and verification.

## Decisions

Use the existing MIT scrcpy client as the first implementation, informed by the
Webscreen packet/control architecture, without copying AGPL implementation code.
This retains the management and Agent baseline while replacing the latency-heavy
path. Hardware encoder selection must be automatic on physical devices; do not
force Android's Google software encoder.

The MVP remains on the existing local test topology. A direct per-node WAN media
path is a subsequent iteration; this release must disclose its central relay.
Do not describe binary WebSocket transport as WebRTC or as a peer-to-peer path.

## Verification gates

| Requirements | Gate | State |
|---|---|---|
| F01/F04 | Inventory, two nodes, device readiness and history retained | Verified in lab / isolated tests |
| F02/F08 | Browser H.264 display, held drag before release, frame diagnostics | Verified in lab / isolated tests |
| F03 | Conflicting claim, stale input, release/disconnect/TTL cancellation | Verified in lab / isolated tests |
| F05 | WDA adapter unchanged; unavailable prerequisites shown honestly | Verified in lab / isolated tests |
| F06 | Existing native task flow retained and a lightweight Agent task exercised | Verified in lab / isolated tests |
| F07 | Scoped mirror recovery and device diagnostics | Verified in lab / isolated tests |
| Publication | Secrets review, attribution, reproducible setup, GitHub push | Final publication step |

Use isolated tests and staging checks before changing the test service. Back up
changed application files and service launchers; preserve database and credentials.
Jack Agent restart can stop its emulator cgroup: stop cleanly, restart Agent, then
start the same registered VM. Never create a replacement VM to hide recovery.

## Deferred

HarmonyOS real-device validation, full multi-tenant RBAC, regional TURN selection,
new scheduling products and completion of Apple-account signing are outside this
MVP. No GUI or Apple account actions may be requested while the operator is away.

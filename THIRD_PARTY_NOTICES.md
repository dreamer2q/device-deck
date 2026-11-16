# Third-Party Notices

## DeviceDeck origin

DeviceDeck derives from dongxinsuperman/ai-phone and the dreamer2q compact fork
at commit `497ec18b48a9ff63a522f3b652f1d27e385e3ba6`. Their original MIT copyright
notice and Git history are retained. DeviceDeck's Android packet transport,
continuous input, authenticated web entry and product additions are downstream
changes, not an official ai-phone release.

The vendored Python scrcpy client in `backend/ai_phone/agent/scrcpy_client/`
originates from [leng-yue/py-scrcpy-client](https://github.com/leng-yue/py-scrcpy-client)
(MIT); existing source attribution remains and the license text is in
`third_party/licenses/LICENSE.py-scrcpy-client.txt`. The packet-mode extension uses the
bundled scrcpy 2.4 protocol. No Webscreen code is bundled in this MVP.

This file summarizes bundled third-party components and notable optional
dependencies used by ai-phone. Each component remains under its own license.
When updating a vendored component or binary, update this file and keep the
upstream license text where required.

The ai-phone project code is licensed under the MIT License. Bundled and optional
third-party components remain under their respective upstream licenses.

## Bundled Components

### WebDriverAgent

- Path: `third_party/WebDriverAgent/`
- Upstream: https://github.com/appium/WebDriverAgent
- License: Apache License 2.0
- License file: `third_party/WebDriverAgent/LICENSE`

### duoctl

- Upstream: https://github.com/skarol/duoctl
- Usage: iPhone Duo simulator hinge and touch helpers
- License: [MIT](./backend/ai_phone/agent/ios_sim/LICENSE.duoctl.txt)

### Jev Phone visual helpers

- Upstream: https://github.com/dongxinsuperman/jev-phone, version 0.2.0, commit `56a0553`
- Usage: visual enhancement for replay localization
- License: [MIT](./backend/ai_phone/agent/trajectory_cache/jev_click/visual_vendor/LICENSE)
- [Vendoring notice](./backend/ai_phone/agent/trajectory_cache/jev_click/visual_vendor/NOTICE.md)

### scrcpy server

- Path: `backend/assets/scrcpy-server.jar`
- Upstream: https://github.com/Genymobile/scrcpy
- Version noted in code/docs: scrcpy server v2.4
- License: Apache License 2.0

### ADBKeyBoard

- Path: `backend/assets/ADBKeyBoard.apk`
- Upstream: https://github.com/senzhk/ADBKeyBoard
- Upstream binary: https://github.com/senzhk/ADBKeyBoard/raw/master/ADBKeyboard.apk
- Purpose: Android Unicode text input through an input method broadcast
- License: GNU GPLv2
- License file: `third_party/licenses/GPL-2.0.txt`
- SHA-256:
  `e698adea5633135a067b038f9a0cf41baa4de09888713a81593fb2b9682cdc59`
- Modification status: unmodified upstream binary. This repository's bundled
  APK has been verified byte-for-byte identical to the upstream binary URL
  listed above.
- Corresponding source code: https://github.com/senzhk/ADBKeyBoard
- Note: The APK is bundled as an independent third-party component. When
  redistributing this repository or a package containing this APK, comply with
  the upstream GPLv2 terms, keep a clear notice of its origin and license, and
  preserve access to the corresponding source code.

## Optional Dependencies

### pymobiledevice3

- Upstream: https://github.com/doronz88/pymobiledevice3
- License: GNU GPLv3
- Usage: optional iOS support installed with `pip install -e ".[ios]"`
- Bundling status: not bundled in this repository

### hmdriver2

- Upstream: https://github.com/codematrixer/hmdriver2
- License: MIT License
- Usage: optional HarmonyOS support installed with `pip install -e ".[harmony]"`
- Bundling status: not bundled in this repository

## Python and Node Dependencies

Runtime Python dependencies are declared in `backend/pyproject.toml`. Web and
Midscene bridge dependencies are declared in their respective `package.json` and
lock files. See each dependency's package metadata for its license terms.

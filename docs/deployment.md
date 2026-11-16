# DeviceDeck deployment

## Components

- Central: PostgreSQL + Python 3.11 API and static web application.
- Node: Python Agent, ADB/scrcpy for Android; optional macOS/Xcode/WDA for iOS.
- Browser: current Chrome/Edge with WebCodecs, using HTTPS or localhost.

The MVP is a single trusted administrative workspace. The browser's Basic login
grants administrative access; it is not multi-tenant RBAC. Machine bearer/Agent
tokens are privileged credentials and must not be included in frontend builds.
Device leases arbitrate control within that workspace; they are not user identity.

## Central installation

Use Python 3.11 and Node 22+. From the repository root:

```sh
python3.11 -m venv backend/.venv
backend/.venv/bin/pip install -e 'backend[dev]'
cd web
npm ci
VITE_GATEWAY_AUTH=true npm run build
```

Prepare a private `backend/.env`, mode 0600, using `backend/.env.example` as the
advanced reference. Minimum deployment values:

```dotenv
AI_PHONE_DB_URL=postgresql+asyncpg://<user>:<password>@<db-host>:5432/<database>
AI_PHONE_AGENT_TOKEN=<unique-random-machine-token>
DEVICE_DECK_USERNAME=<admin-name>
DEVICE_DECK_PASSWORD=<unique-password-at-least-12-characters>
```

Generate real secrets locally, store them in the operator's credential manager,
and never commit this file. Use an existing PostgreSQL instance and a dedicated
database/account. Database initialization creates the platform tables; back up
an existing platform consistently before reusing its database. Do not synchronize
a running PostgreSQL data directory as a backup.

Run from `backend/` so dotenv paths resolve consistently:

```sh
.venv/bin/uvicorn --factory ai_phone.server.webapp:build_webapp --host 127.0.0.1 --port 8000
```

The unified entry point serves `web/dist`, supports SPA deep links, authenticates
HTTP and browser WebSockets, and adds the internal bearer header on the
server after browser authentication. Machine bearer identities remain unchanged;
individual API handlers retain their own token checks. `/ws/agent` retains the
Agent token validation from the core application. `DEVICE_DECK_WEB_DIST` can explicitly select a built web
directory when sources and runtime are installed separately.

Put the loopback service behind the operator's TLS reverse proxy. Forward HTTP
and WebSocket upgrades, avoid response buffering for interactive traffic, and
retain sufficient WebSocket idle timeouts. If a second authentication layer is
used at the proxy, configure compatible forwarding rather than stripping the
application's credentials. Validate anonymous 401, authenticated UI/API access,
and browser/Agent WebSocket connection after publishing the hostname.

Use a single central process/worker: leases and active channel routing are in
memory in this MVP. A central restart invalidates current leases, clients must
reacquire, and temporary mirror pauses are cleared. Do not launch multiple API
workers with independent lock stores.

## Device node

Install the backend into a Python 3.11 environment on each device host. Install
ADB and authorize the selected physical phone once; the platform must not revoke
other tools' ADB keys or run `adb kill-server` as routine recovery.

In the node's private `backend/.env`:

```dotenv
AI_PHONE_SERVER_WS_URL=wss://<platform-host>/ws/agent
AI_PHONE_SERVER_HTTP_BASE=https://<platform-host>
AI_PHONE_AGENT_TOKEN=<same-private-agent-connection-token>
AI_PHONE_AGENT_NAME=<unique-human-readable-node-name>
```

Set these **process environment variables** in the node service:

```sh
export DEVICE_DECK_RAW_MIRROR=1
export AI_PHONE_AGENT_ID=<stable-unique-node-identity>
cd backend
.venv/bin/python -m ai_phone agent
```

`DEVICE_DECK_RAW_MIRROR` is a process switch, not a Pydantic `AI_PHONE_*` setting.
For systemd put it under `[Service] Environment=`; for launchd use
`EnvironmentVariables` or a literal dotenv-loading launcher. Restart the Agent to
change it. Without it the compatibility fMP4 path is used.

Keep a stable, unique Agent ID for a managed VM host. Copying one node's identity
to another would cause ownership conflicts. Private agent/host settings are not
made into browser configuration or published as documentation examples.

Nodes discover attached devices and enroll through the authenticated Agent
channel. A device card is ready only after its health probe succeeds. Verify node
name, platform, readiness, acquire/control/release, and reconnection independently.

## iOS and Agent models

The iOS adapter remains WDA. Install full Xcode, sign WDA for the actual phone,
pair/trust it and enable Developer Mode. Missing signing or unavailable WDA must
remain a visible not-ready state; do not bypass readiness to create a green card.
Details remain in the inherited iOS deployment documentation.

AI tasks reuse the native runner. Configure phone and auxiliary model endpoints
explicitly using the provider settings in `backend/.env.example`. Verify with a
read-only screen task first. The model must support the selected computer-use
wire protocol and image input; an endpoint responding to a text-only request is
not sufficient evidence. Agent tasks and manual sessions share device leases.

## Operations and rollback

- Keep runtime credentials and databases outside the public checkout, and preserve
  all original license notices and bundled component sources/licenses.
- Build/stage and test before replacing active files; keep the old application,
  web assets and service configuration for rollback.
- Suspend a free device's mirrors from the device table before maintenance.
  Occupied devices refuse suspension. This is a temporary session control,
  cleared by a central restart, not a durable physical-maintenance designation.
- Resume the mirrors after maintenance; reconnecting clients may take the usual
  retry backoff to reopen their stream.
- An Agent service cgroup may own a managed emulator. Stop the VM through its
  platform lifecycle before restarting that Agent, then start the same VM ID.
  Do not create a new VM to hide a failed reclaim.
- Limit CPU/memory according to actual host load. Video is no longer transcoded
  in the Android path, but emulators and AI tasks still consume resources.
- Roll back both Agent and central/browser protocol changes together. The legacy
  path is available by removing the raw-mirror process flag and restarting the
  Agent, while keeping compatible browser code. Never restore an old database
  snapshot merely to roll back a UI or media transport change.

## Verification boundaries

See [MVP validation](validation/mvp-0001/README.md). The checked deployment uses
two hosts, an Android physical phone, an Android emulator and an iPhone with WDA
not ready. It does not establish WAN direct routing, all Android device support,
iOS signing success, multi-tenant isolation or physical display scanout latency.

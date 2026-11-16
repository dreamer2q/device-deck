"""Single-origin production UI/API entry point, with HTTP + WebSocket auth.

Run behind TLS with uvicorn ai_phone.server.webapp:app. Agent enrollment retains
its separate shared token. Browser credentials never become JavaScript config.
"""
from __future__ import annotations

import base64
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles

load_dotenv()

from ai_phone.config import get_settings  # noqa: E402
from .app import create_app  # noqa: E402


class BrowserAuth:
    def __init__(self, app, *, username, password, internal_token):
        if not username or len(password) < 12 or not internal_token or internal_token == "dev":
            raise RuntimeError("Set DEVICE_DECK_USERNAME, DEVICE_DECK_PASSWORD (12+ chars) and a private Agent token")
        self.app, self.username, self.password, self.internal_token = app, username, password, internal_token

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"} or scope.get("path") == "/ws/agent":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        auth = headers.get(b"authorization", b"").decode("latin1")
        valid = False
        if auth.startswith("Basic "):
            try:
                value = base64.b64decode(auth[6:], validate=True).decode("utf-8")
                username, password = value.split(":", 1)
                valid = secrets.compare_digest(username.encode(), self.username.encode()) and secrets.compare_digest(password.encode(), self.password.encode())
            except (ValueError, UnicodeError):
                pass
        elif auth.startswith("Bearer "):
            valid = secrets.compare_digest(auth[7:].encode(), self.internal_token.encode())
        if not valid:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 4401})
                return
            response = Response("Authentication required", status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="DeviceDeck", charset="UTF-8"'})
            return await response(scope, receive, send)
        if scope.get("path", "").startswith("/api/internal/"):
            scope = {**scope, "headers": [(k, v) for k, v in scope.get("headers", [])
                if k.lower() != b"authorization"] + [(b"authorization", ("Bearer " + self.internal_token).encode())]}
        await self.app(scope, receive, send)


class SPA(StaticFiles):
    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code != 404 or path.split("/", 1)[0] in {"api", "ws", "files", "assets"}:
                raise
            return await super().get_response("index.html", scope)


def build_webapp():
    settings = get_settings()
    app = create_app()
    app.title = "DeviceDeck"
    app.add_middleware(BrowserAuth, username=os.environ.get("DEVICE_DECK_USERNAME", ""),
        password=os.environ.get("DEVICE_DECK_PASSWORD", ""),
        internal_token=settings.submission_internal_token or settings.agent_token)
    dist = Path(os.environ.get("DEVICE_DECK_WEB_DIST", str(Path(__file__).resolve().parents[3] / "web/dist")))
    if not (dist / "index.html").is_file():
        raise RuntimeError("Build web/ first or set DEVICE_DECK_WEB_DIST")
    app.mount("/", SPA(directory=dist, html=True), name="workbench")
    return app


# uvicorn's factory mode avoids requiring credentials when importing auth helpers
# in isolated tests: --factory ai_phone.server.webapp:build_webapp.

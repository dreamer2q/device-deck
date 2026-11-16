import base64

from fastapi import FastAPI, Request, WebSocket
from fastapi.testclient import TestClient

from ai_phone.server.webapp import BrowserAuth


def test_auth_protects_http_websocket_and_keeps_internal_token_server_side():
    app = FastAPI()
    app.add_middleware(BrowserAuth, username="tester", password="test-password-123",
        internal_token="test-machine-token", agent_token="separate-agent-token")
    @app.get("/api/internal/echo")
    def echo(request: Request):
        # An isolated test endpoint, not installed in the production application.
        return {"internal_authorized": request.headers.get("authorization") == "Bearer test-machine-token"}
    @app.websocket("/ws/agent")
    async def agent(ws: WebSocket):
        await ws.accept(); await ws.send_text("separate-agent-token-guard"); await ws.close()
    @app.websocket("/ws/browser/device")
    async def browser(ws: WebSocket):
        await ws.accept(); await ws.send_text("authorized"); await ws.close()
    with TestClient(app) as client:
        assert client.get("/api/internal/echo").status_code == 401
        assert client.get("/api/internal/echo", auth=("tester", "wrong")).status_code == 401
        assert client.get("/api/internal/echo", auth=("tester", "test-password-123")).json() == {"internal_authorized": True}
        # The outer guard allows node HTTP traffic but does not rewrite its
        # identity into the more privileged internal API credential.
        assert client.get("/api/internal/echo", headers={"Authorization": "Bearer separate-agent-token"}).json() == {"internal_authorized": False}
        assert client.get("/api/internal/echo", headers={"Authorization": "Bearer test-machine-token"}).json() == {"internal_authorized": True}
        with client.websocket_connect("/ws/agent") as ws:
            assert ws.receive_text() == "separate-agent-token-guard"
        header = "Basic " + base64.b64encode(b"tester:test-password-123").decode()
        with client.websocket_connect("/ws/browser/device", headers={"Authorization": header}) as ws:
            assert ws.receive_text() == "authorized"

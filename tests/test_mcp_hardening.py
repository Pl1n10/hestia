"""MCP hardening: audit log, bearer auth, HTTP app wiring."""

from __future__ import annotations

import json

import pytest

from app.mcp import audit
from app.settings import settings


# --- audit --------------------------------------------------------------- #
def test_audit_wrap_preserves_tool_schema():
    from app.mcp.server import build_mcp_server

    server = build_mcp_server()
    tools = {t.name: t for t in server._tool_manager.list_tools()}
    props = tools["subscriptions_add"].parameters["properties"]
    # the typed params must survive the audit wrapper
    assert {"name", "amount", "cycle"} <= set(props)


def test_tool_call_is_recorded(tmp_path, monkeypatch):
    log = tmp_path / "audit.log"
    monkeypatch.setattr(settings, "mcp_audit_log_path", str(log))
    monkeypatch.setattr(settings, "mcp_audit_enabled", True)
    audit.reset_for_tests()

    # audit_wrap takes (handler, name)
    wrapped = audit.audit_wrap(lambda x=1: {"ok": True}, "demo_tool")
    wrapped(x=5)
    audit.reset_for_tests()

    lines = log.read_text().strip().splitlines()
    assert lines, "expected an audit line"
    rec = json.loads(lines[-1])
    assert rec["event"] == "mcp_tool_call"
    assert rec["tool"] == "demo_tool"
    assert rec["status"] == "ok"
    assert "duration_ms" in rec


def test_audit_redacts_sensitive_args(tmp_path, monkeypatch):
    log = tmp_path / "audit.log"
    monkeypatch.setattr(settings, "mcp_audit_log_path", str(log))
    audit.reset_for_tests()

    wrapped = audit.audit_wrap(lambda token=None: {"ok": True}, "secret_tool")
    wrapped(token="super-secret-value")
    audit.reset_for_tests()

    rec = json.loads(log.read_text().strip().splitlines()[-1])
    assert rec["args"]["token"] == "***"


def test_soft_error_result_marked_error(tmp_path, monkeypatch):
    log = tmp_path / "audit.log"
    monkeypatch.setattr(settings, "mcp_audit_log_path", str(log))
    audit.reset_for_tests()

    wrapped = audit.audit_wrap(lambda: {"error": "nope"}, "failing_tool")
    wrapped()
    audit.reset_for_tests()

    rec = json.loads(log.read_text().strip().splitlines()[-1])
    assert rec["status"] == "error"
    assert rec["error"] == "nope"


# --- auth middleware ----------------------------------------------------- #
@pytest.fixture
def guarded_app():
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    from app.mcp.auth import BearerAuthMiddleware

    async def protected(_req):
        return JSONResponse({"ok": True})

    async def healthz(_req):
        return JSONResponse({"status": "ok"})

    app = Starlette(routes=[Route("/mcp", protected), Route("/healthz", healthz)])
    app.add_middleware(BearerAuthMiddleware)
    return app


def test_protected_path_rejects_without_token(guarded_app):
    from starlette.testclient import TestClient

    with TestClient(guarded_app) as c:
        r = c.get("/mcp")
        assert r.status_code == 401
        assert r.headers.get("www-authenticate") == "Bearer"


def test_protected_path_accepts_master_token(guarded_app):
    from starlette.testclient import TestClient

    with TestClient(guarded_app) as c:
        r = c.get("/mcp", headers={"Authorization": f"Bearer {settings.agent_token}"})
        assert r.status_code == 200
        assert r.json() == {"ok": True}


def test_invalid_token_rejected(guarded_app):
    from starlette.testclient import TestClient

    with TestClient(guarded_app) as c:
        r = c.get("/mcp", headers={"Authorization": "Bearer wrong"})
        assert r.status_code == 401


def test_health_is_public(guarded_app):
    from starlette.testclient import TestClient

    with TestClient(guarded_app) as c:
        assert c.get("/healthz").status_code == 200


def test_require_auth_false_opens_everything(guarded_app, monkeypatch):
    from starlette.testclient import TestClient

    monkeypatch.setattr(settings, "mcp_require_auth", False)
    with TestClient(guarded_app) as c:
        assert c.get("/mcp").status_code == 200


# --- http app build ------------------------------------------------------ #
def test_build_http_app_has_health_route():
    from app.mcp.server import build_http_app

    app = build_http_app()
    paths = {getattr(r, "path", None) for r in app.router.routes}
    assert "/healthz" in paths

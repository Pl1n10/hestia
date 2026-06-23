"""Bearer-token gate for the MCP HTTP transport.

Pure ASGI middleware (not BaseHTTPMiddleware) so it never buffers the
streamable-http / SSE response stream — see docs/FAILURES.md F-005.

A request is allowed only if it carries ``Authorization: Bearer <token>`` that
``resolve_principal`` accepts **as an agent** — the exact same resolution the
REST API uses (env master token or a hashed, revocable row in ``api_tokens``).
This is the agent transport, so human/dev/proxy identities are never accepted
here; only agent tokens get in. Health paths are public so systemd/uptime can
probe without a credential.
"""

from __future__ import annotations

from app.mcp.audit import current_principal_name, record_auth
from app.settings import settings

PUBLIC_PATHS = frozenset({"/healthz", "/health"})


class BearerAuthMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in PUBLIC_PATHS or not settings.mcp_require_auth:
            await self.app(scope, receive, send)
            return

        headers = {k.decode().lower(): v.decode() for k, v in (scope.get("headers") or [])}
        authorization = headers.get("authorization", "")

        principal = self._resolve_agent(authorization)
        if principal is None:
            record_auth(ok=False, principal=None, path=path, reason="invalid_or_missing_bearer")
            await self._reject(send)
            return

        token = current_principal_name.set(principal)
        record_auth(ok=True, principal=principal, path=path)
        try:
            await self.app(scope, receive, send)
        finally:
            current_principal_name.reset(token)

    @staticmethod
    def _resolve_agent(authorization: str) -> str | None:
        if not authorization.lower().startswith("bearer "):
            return None
        # Reuse the REST resolver against a short-lived session.
        from app.auth import resolve_principal
        from app.db import SessionLocal

        with SessionLocal() as db:
            p = resolve_principal({"authorization": authorization}, db)
        if p is not None and p.is_agent:
            return p.display_name
        return None

    @staticmethod
    async def _reject(send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"www-authenticate", b"Bearer"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": b'{"error":"unauthorized"}'})

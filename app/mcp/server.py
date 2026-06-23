"""Hestia MCP server.

Reflects over the module registry and exposes every module's tools to agents
(Hermes today; a future Alexa skill or anything MCP-speaking tomorrow). The
tools call the same ``service.py`` functions the REST API does, so the agent and
the app are always in sync.

Transports:
* ``stdio`` (default)        — a local pipe; no network, no auth.
* ``streamable-http`` / ``sse`` — served by uvicorn behind a bearer-auth
  middleware. Put this behind a Cloudflare Tunnel and register it as a custom
  connector on claude.ai.

    HESTIA_MCP_TRANSPORT=streamable-http HESTIA_MCP_PORT=8766 python -m app.mcp.server
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.mcp.audit import audit_wrap
from app.mcp.help import build_help_tool
from app.modules import load_enabled
from app.modules.base import McpTool
from app.settings import settings

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from starlette.applications import Starlette


def collect_tools() -> list[McpTool]:
    # hestia_help leads: it's the agent's entry point to discover the rest.
    tools: list[McpTool] = [build_help_tool()]
    for module in load_enabled().values():
        tools.extend(module.mcp_tools)
    return tools


def build_mcp_server() -> "FastMCP":
    from mcp.server.fastmcp import FastMCP

    server = FastMCP(settings.app_name, host=settings.mcp_host, port=settings.mcp_port)
    for tool in collect_tools():
        # audit_wrap is signature-preserving, so FastMCP still derives the schema.
        server.add_tool(audit_wrap(tool.handler, tool.name), name=tool.name, description=tool.description)
    return server


def build_http_app() -> "Starlette":
    """A Starlette app for HTTP transports, gated by the bearer-auth middleware."""
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    from app import __version__
    from app.mcp.auth import BearerAuthMiddleware

    server = build_mcp_server()

    if settings.mcp_transport == "sse":
        app = server.sse_app()
    else:
        app = server.streamable_http_app()

    async def healthz(_request):
        return JSONResponse({"status": "ok", "app": settings.app_name, "version": __version__})

    app.router.routes.append(Route("/healthz", healthz, methods=["GET"]))
    app.add_middleware(BearerAuthMiddleware)
    return app


def main() -> None:  # pragma: no cover - process entrypoint
    from app.db import init_db

    init_db()

    if settings.mcp_transport in ("streamable-http", "sse"):
        import uvicorn

        uvicorn.run(
            build_http_app(),
            host=settings.mcp_host,
            port=settings.mcp_port,
            log_level="info",
        )
    else:
        build_mcp_server().run(transport="stdio")


if __name__ == "__main__":  # pragma: no cover
    main()

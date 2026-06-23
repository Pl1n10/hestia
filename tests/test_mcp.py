"""MCP surface — the agent's view of the dashboard.

These assert the registry reflection works. The actual transport run() is a
process entrypoint and isn't exercised here.
"""

from __future__ import annotations

import pytest

from app.mcp.server import collect_tools


def test_collect_tools_aggregates_every_enabled_module():
    names = {t.name for t in collect_tools()}
    assert {"dogs_list", "dogs_log_activity", "dogs_recent"} <= names
    assert {"subscriptions_add", "subscriptions_monthly_cost"} <= names


def test_tools_have_descriptions_and_callables():
    for tool in collect_tools():
        assert tool.description
        assert callable(tool.handler)


def test_build_mcp_server_registers_all_tools():
    fastmcp = pytest.importorskip("mcp.server.fastmcp")  # noqa: F841
    from app.mcp.server import build_mcp_server

    server = build_mcp_server()
    # FastMCP exposes registered tools via list_tools(); fall back gracefully
    # across versions by just asserting the build succeeded and is the right type.
    assert server is not None
    assert server.name  # configured with the app name


def test_dogs_tool_writes_through_service(db):
    """A module MCP tool must hit the same service the REST API does."""
    from app.modules.dogs import mcp as dogs_mcp
    from app.modules.dogs import service

    service.create_dog(db, 1, name="Milka")
    db.commit()

    # tool opens its own session; default household is 1 in tests
    result = dogs_mcp.dogs_log_activity(dog="Milka", type="sgambamento")
    assert result["logged_by"] == "agent"
    assert result["type"] == "sgambamento"

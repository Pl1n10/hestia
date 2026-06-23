"""TEMPLATE module - MCP tools (agent surface)."""

from __future__ import annotations

from app.db import SessionLocal
from app.modules.base import McpTool
from app.settings import settings

from . import service
from .schemas import ExampleOut


def example_list() -> list[dict]:
    """List example items."""
    with SessionLocal() as db:
        rows = service.list_items(db, settings.default_household_id)
        return [ExampleOut.model_validate(r).model_dump(mode="json") for r in rows]


TOOLS = [McpTool("example_list", "List example items.", example_list)]

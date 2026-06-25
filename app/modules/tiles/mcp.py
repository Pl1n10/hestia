"""Tiles module - MCP tools (the agent surface).

Hermes can add, read, update, and delete tiles — the same operations
the REST API exposes. All logic lives in service.py (DECISIONS D-002).
"""

from __future__ import annotations

from dateutil import parser as dtparser

from app.db import SessionLocal
from app.modules.base import McpTool
from app.settings import settings

from . import service
from .schemas import TileOut


def _hh() -> int:
    return settings.default_household_id


def tiles_list(active_only: bool = True) -> list[dict]:
    """List dashboard tiles (active only by default)."""
    with SessionLocal() as db:
        rows = service.list_tiles(db, _hh(), active_only=active_only)
        return [TileOut.model_validate(r).model_dump(mode="json") for r in rows]


def tiles_add(
    title: str,
    body: str | None = None,
    color: str = "default",
    size: str = "normal",
    refresh_interval_min: int | None = None,
    next_check_at: str | None = None,
) -> dict:
    """Add a custom dashboard tile.

    Args:
        title: short tile label (e.g. "Manutenzione Cucina").
        body: optional content text shown in the tile.
        color: UI color hint — default | blue | green | yellow | red | purple.
        size: UI size hint — small | normal | large.
        refresh_interval_min: optional auto-refresh interval in minutes.
        next_check_at: optional ISO date (YYYY-MM-DD) for reminder / next check.
    """
    with SessionLocal() as db:
        check = dtparser.isoparse(next_check_at).date() if next_check_at else None
        tile = service.create_tile(
            db,
            _hh(),
            title=title,
            body=body,
            color=color,
            size=size,
            refresh_interval_min=refresh_interval_min,
            next_check_at=check,
        )
        return TileOut.model_validate(tile).model_dump(mode="json")


def tiles_update(
    tile_id: int,
    title: str | None = None,
    body: str | None = None,
    color: str | None = None,
    size: str | None = None,
    refresh_interval_min: int | None = None,
    next_check_at: str | None = None,
    active: bool | None = None,
) -> dict:
    """Edit an existing tile in place (only the fields you pass change).

    Args:
        tile_id: the tile id (from tiles_list).
        title: new label.
        body: new content text.
        color: new color hint.
        size: new size hint.
        refresh_interval_min: new refresh interval in minutes.
        next_check_at: ISO date (YYYY-MM-DD) for the next check/reminder.
        active: set False to hide the tile from the dashboard.
    """
    changes: dict = {}
    for key, value in (
        ("title", title),
        ("body", body),
        ("color", color),
        ("size", size),
        ("refresh_interval_min", refresh_interval_min),
        ("active", active),
    ):
        if value is not None:
            changes[key] = value
    if next_check_at is not None:
        changes["next_check_at"] = dtparser.isoparse(next_check_at).date()
    with SessionLocal() as db:
        tile = service.update_tile(db, _hh(), tile_id, **changes)
        if tile is None:
            return {"error": f"No tile with id {tile_id}."}
        return TileOut.model_validate(tile).model_dump(mode="json")


def tiles_delete(tile_id: int) -> dict:
    """Delete a tile permanently. Call tiles_list first to get the id."""
    with SessionLocal() as db:
        ok = service.delete_tile(db, _hh(), tile_id)
        if not ok:
            return {"error": f"No tile with id {tile_id}."}
        return {"deleted": True, "id": tile_id}


TOOLS = [
    McpTool("tiles_list", "List custom dashboard tiles.", tiles_list),
    McpTool("tiles_add", "Add a custom dashboard tile with optional reminder date.", tiles_add),
    McpTool("tiles_update", "Edit an existing tile in place (avoids duplicates).", tiles_update),
    McpTool("tiles_delete", "Delete a tile permanently.", tiles_delete),
]

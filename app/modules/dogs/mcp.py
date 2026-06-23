"""Dogs module - MCP tools (the agent surface).

These are what Hermes calls. Each opens its own session and resolves the
configured default household, then delegates to ``service.py`` - the exact
same code path the REST API uses.
"""

from __future__ import annotations

from dateutil import parser as dtparser

from app.db import SessionLocal
from app.modules.base import McpTool
from app.settings import settings

from . import service
from .schemas import ActivityOut, DogOut


def _hh() -> int:
    return settings.default_household_id


def dogs_list() -> list[dict]:
    """List the household's dogs with their id, name and breed."""
    with SessionLocal() as db:
        return [DogOut.model_validate(d).model_dump(mode="json") for d in service.list_dogs(db, _hh())]


def dogs_log_activity(
    dog: str,
    type: str = "sgambamento",
    duration_min: int | None = None,
    notes: str | None = None,
    when: str | None = None,
) -> dict:
    """Log a dog activity.

    Args:
        dog: the dog's name (must already exist).
        type: sgambamento | passeggiata | pappa | vet | toelettatura | farmaco.
        duration_min: optional duration in minutes.
        notes: optional free text.
        when: optional ISO-8601 timestamp; defaults to now.
    """
    with SessionLocal() as db:
        target = service.find_dog_by_name(db, _hh(), dog)
        if target is None:
            known = [d.name for d in service.list_dogs(db, _hh())]
            return {"error": f"Unknown dog '{dog}'.", "known_dogs": known}
        occurred = dtparser.isoparse(when) if when else None
        activity = service.log_activity(
            db,
            _hh(),
            target.id,
            type=type,
            occurred_at=occurred,
            duration_min=duration_min,
            notes=notes,
            logged_by="agent",
        )
        return ActivityOut.model_validate(activity).model_dump(mode="json")


def dogs_recent(dog: str | None = None, limit: int = 10) -> list[dict]:
    """List recent dog activities, optionally filtered by dog name."""
    with SessionLocal() as db:
        dog_id = None
        if dog:
            found = service.find_dog_by_name(db, _hh(), dog)
            if found is None:
                return []
            dog_id = found.id
        acts = service.recent_activities(db, _hh(), dog_id=dog_id, limit=limit)
        return [ActivityOut.model_validate(a).model_dump(mode="json") for a in acts]


TOOLS = [
    McpTool("dogs_list", "List the household's dogs.", dogs_list),
    McpTool("dogs_log_activity", "Log a dog activity (sgambamento, walk, meal, vet...) by dog name.", dogs_log_activity),
    McpTool("dogs_recent", "List recent dog activities, optionally filtered by dog.", dogs_recent),
]

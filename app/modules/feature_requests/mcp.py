"""Feature-requests module - MCP tools (the agent surface).

This is the loop the user asked for: Hermes (over Telegram) files a request
for a new dashboard capability; Claude Code reads the open queue, builds it,
and flips the status. Both ends call the same ``service.py`` the REST API does.
"""

from __future__ import annotations

from app.db import SessionLocal
from app.modules.base import McpTool
from app.settings import settings

from . import service
from .models import STATUSES
from .schemas import FeatureRequestOut


def _hh() -> int:
    return settings.default_household_id


def feature_requests_add(
    title: str,
    detail: str | None = None,
    priority: str = "normal",
    requested_by: str | None = None,
) -> dict:
    """File a new feature request for the Hestia dashboard.

    Use this when someone asks for a capability the dashboard does not have yet
    (a new module, a new field, a new automation). Claude Code reads these and
    implements them.

    Args:
        title: a short one-line summary (e.g. "Track car insurance renewals").
        detail: the full description — what's wanted and why; the more the better.
        priority: low | normal | high.
        requested_by: who asked (the human's name); defaults to the agent.
    """
    with SessionLocal() as db:
        req = service.create_request(
            db,
            _hh(),
            title=title,
            detail=detail,
            priority=priority,
            requested_by=requested_by or "hermes",
        )
        return FeatureRequestOut.model_validate(req).model_dump(mode="json")


def feature_requests_list(status: str | None = None, open_only: bool = True) -> list[dict]:
    """List feature requests (open ones by default).

    Args:
        status: filter to exactly one of new | in_progress | done | rejected.
        open_only: when no status is given, return only new/in_progress (default).
    """
    with SessionLocal() as db:
        rows = service.list_requests(db, _hh(), status=status, open_only=open_only)
        return [FeatureRequestOut.model_validate(r).model_dump(mode="json") for r in rows]


def feature_requests_set_status(
    request_id: int, status: str, resolution: str | None = None
) -> dict:
    """Move a feature request along its lifecycle.

    Args:
        request_id: the request id (from feature_requests_list).
        status: new | in_progress | done | rejected.
        resolution: optional note for the implementer / a rejection reason / PR link.
    """
    if status not in STATUSES:
        return {"error": f"Unknown status '{status}'.", "valid": list(STATUSES)}
    with SessionLocal() as db:
        req = service.set_status(db, _hh(), request_id, status, resolution=resolution)
        if req is None:
            return {"error": f"No feature request with id {request_id}."}
        return FeatureRequestOut.model_validate(req).model_dump(mode="json")


TOOLS = [
    McpTool(
        "feature_requests_add",
        "File a new feature request for the dashboard (Claude Code implements it).",
        feature_requests_add,
    ),
    McpTool(
        "feature_requests_list",
        "List feature requests (open ones by default).",
        feature_requests_list,
    ),
    McpTool(
        "feature_requests_set_status",
        "Update a feature request's status (new/in_progress/done/rejected).",
        feature_requests_set_status,
    ),
]

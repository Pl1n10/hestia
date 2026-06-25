"""Projects module - MCP tools (the agent surface).

Hermes can manage the cross-project development overview: add a project,
record last activity, update status, and delete stale entries. Every tool
calls the same service.py the REST API does.
"""

from __future__ import annotations

from app.db import SessionLocal
from app.modules.base import McpTool
from app.settings import settings

from . import service
from .models import STATUSES
from .schemas import ProjectOut


def _hh() -> int:
    return settings.default_household_id


def projects_add(
    name: str,
    description: str | None = None,
    status: str = "active",
    repo_url: str | None = None,
    last_activity: str | None = None,
) -> dict:
    """Add a project to the development overview.

    Args:
        name: project name (e.g. "hestia", "argus").
        description: short description of what the project does.
        status: active | paused | completed.
        repo_url: link to the GitHub (or other) repository.
        last_activity: one-line description of the last notable activity.
    """
    with SessionLocal() as db:
        proj = service.create_project(
            db,
            _hh(),
            name=name,
            description=description,
            status=status,
            repo_url=repo_url,
            last_activity=last_activity,
        )
        return ProjectOut.model_validate(proj).model_dump(mode="json")


def projects_list(status: str | None = None, active_only: bool = False) -> list[dict]:
    """List projects in the development overview.

    Args:
        status: filter to exactly one of active | paused | completed.
        active_only: when no status is given, return only active/paused (default False).
    """
    with SessionLocal() as db:
        rows = service.list_projects(db, _hh(), status=status, active_only=active_only)
        return [ProjectOut.model_validate(p).model_dump(mode="json") for p in rows]


def projects_update(
    project_id: int,
    name: str | None = None,
    description: str | None = None,
    status: str | None = None,
    repo_url: str | None = None,
    last_activity: str | None = None,
) -> dict:
    """Update a project's details or record new activity.

    Args:
        project_id: the project id (from projects_list).
        name: rename the project.
        description: update the description.
        status: active | paused | completed.
        repo_url: update the repository link.
        last_activity: describe the most recent activity (commit, PR, issue).
    """
    changes: dict = {}
    if name is not None:
        changes["name"] = name
    if description is not None:
        changes["description"] = description
    if status is not None:
        if status not in STATUSES:
            return {"error": f"Unknown status '{status}'.", "valid": list(STATUSES)}
        changes["status"] = status
    if repo_url is not None:
        changes["repo_url"] = repo_url
    if last_activity is not None:
        from datetime import datetime, timezone
        changes["last_activity"] = last_activity
        changes["last_activity_at"] = datetime.now(timezone.utc)

    if not changes:
        return {"error": "No fields to update."}

    with SessionLocal() as db:
        proj = service.update_project(db, _hh(), project_id, **changes)
        if proj is None:
            return {"error": f"No project with id {project_id}."}
        return ProjectOut.model_validate(proj).model_dump(mode="json")


def projects_delete(project_id: int) -> dict:
    """Remove a project from the overview.

    Args:
        project_id: the project id (from projects_list).
    """
    with SessionLocal() as db:
        if not service.delete_project(db, _hh(), project_id):
            return {"error": f"No project with id {project_id}."}
        return {"deleted": project_id}


TOOLS = [
    McpTool(
        "projects_add",
        "Add a project to the development overview.",
        projects_add,
    ),
    McpTool(
        "projects_list",
        "List projects in the development overview.",
        projects_list,
    ),
    McpTool(
        "projects_update",
        "Update a project's details or record new activity.",
        projects_update,
    ),
    McpTool(
        "projects_delete",
        "Remove a project from the overview.",
        projects_delete,
    ),
]

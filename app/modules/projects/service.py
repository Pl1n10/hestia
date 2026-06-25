"""Projects module - service layer (single source of truth).

Pure functions over a Session. The REST router and the MCP tools both call
these; nothing else touches the projects table.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.base import ModuleSummary, StatItem, SummaryItem
from app.util import humanize_ago

from .models import ACTIVE_STATUSES, STATUSES, Project

MANIFEST_KEY = "projects"

_STATUS_LABEL = {
    "active": "attivo",
    "paused": "in pausa",
    "completed": "completato",
}
_STATUS_SEVERITY = {
    "active": "info",
    "paused": "warning",
    "completed": "normal",
}


def _clean_status(value: str | None) -> str | None:
    return value if value in STATUSES else None


# --- CRUD ---------------------------------------------------------------- #
def list_projects(
    db: Session,
    household_id: int,
    *,
    status: str | None = None,
    active_only: bool = False,
) -> list[Project]:
    stmt = select(Project).where(Project.household_id == household_id)
    if status is not None:
        stmt = stmt.where(Project.status == status)
    elif active_only:
        stmt = stmt.where(Project.status.in_(ACTIVE_STATUSES))
    stmt = stmt.order_by(Project.name)
    return list(db.execute(stmt).scalars())


def get_project(db: Session, household_id: int, project_id: int) -> Project | None:
    proj = db.get(Project, project_id)
    if proj is None or proj.household_id != household_id:
        return None
    return proj


def create_project(
    db: Session,
    household_id: int,
    *,
    name: str,
    description: str | None = None,
    status: str = "active",
    repo_url: str | None = None,
    last_activity: str | None = None,
    last_activity_at: datetime | None = None,
) -> Project:
    proj = Project(
        household_id=household_id,
        name=name,
        description=description,
        status=_clean_status(status) or "active",
        repo_url=repo_url,
        last_activity=last_activity,
        last_activity_at=last_activity_at,
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


def update_project(
    db: Session, household_id: int, project_id: int, **changes
) -> Project | None:
    proj = get_project(db, household_id, project_id)
    if proj is None:
        return None
    for key, value in changes.items():
        if key == "status":
            cleaned = _clean_status(value)
            if cleaned is None:
                continue  # ignore unknown status rather than corrupt lifecycle
            setattr(proj, key, cleaned)
        else:
            setattr(proj, key, value)
    db.commit()
    db.refresh(proj)
    return proj


def delete_project(db: Session, household_id: int, project_id: int) -> bool:
    proj = get_project(db, household_id, project_id)
    if proj is None:
        return False
    db.delete(proj)
    db.commit()
    return True


# --- summary (home card) ------------------------------------------------- #
def summary(db: Session, household_id: int) -> ModuleSummary:
    all_projects = list_projects(db, household_id)
    active = [p for p in all_projects if p.status == "active"]
    paused = [p for p in all_projects if p.status == "paused"]
    completed = [p for p in all_projects if p.status == "completed"]

    if not all_projects:
        headline = "Nessun progetto"
    elif not active and not paused:
        headline = f"Tutti completati · {len(completed)} progetti"
    else:
        parts = []
        if active:
            parts.append(f"{len(active)} attivi")
        if paused:
            parts.append(f"{len(paused)} in pausa")
        headline = " · ".join(parts)

    # Show active+paused projects; completed ones are noise on the home card.
    visible = active + paused
    items = [
        SummaryItem(
            title=p.name,
            subtitle=p.last_activity,
            when=humanize_ago(p.last_activity_at) if p.last_activity_at else None,
            severity=_STATUS_SEVERITY.get(p.status, "normal"),
        )
        for p in visible
    ]

    return ModuleSummary(
        key=MANIFEST_KEY,
        name="Progetti",
        icon="🗂️",
        headline=headline,
        stats=[
            StatItem(label="Attivi", value=str(len(active))),
            StatItem(label="In pausa", value=str(len(paused))),
            StatItem(label="Completati", value=str(len(completed))),
        ],
        items=items,
    )

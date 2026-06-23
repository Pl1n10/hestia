"""Feature-requests module - service layer (single source of truth).

Pure functions over a Session. The REST router and the MCP tools both call
these; nothing else touches the feature-request table.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.base import ModuleSummary, StatItem, SummaryItem
from app.util import humanize_ago

from .models import OPEN_STATUSES, PRIORITIES, STATUSES, FeatureRequest

MANIFEST_KEY = "feature_requests"

# A high-priority open request should jump out on the home card.
_PRIORITY_SEVERITY = {"high": "warning", "normal": "info", "low": "normal"}


def _clean_status(value: str | None) -> str | None:
    return value if value in STATUSES else None


def _clean_priority(value: str | None) -> str:
    return value if value in PRIORITIES else "normal"


# --- CRUD ---------------------------------------------------------------- #
def list_requests(
    db: Session,
    household_id: int,
    *,
    status: str | None = None,
    open_only: bool = False,
) -> list[FeatureRequest]:
    stmt = select(FeatureRequest).where(FeatureRequest.household_id == household_id)
    if status is not None:
        stmt = stmt.where(FeatureRequest.status == status)
    elif open_only:
        stmt = stmt.where(FeatureRequest.status.in_(OPEN_STATUSES))
    # Open work first (newest first), so the most recent asks are on top.
    stmt = stmt.order_by(FeatureRequest.created_at.desc())
    return list(db.execute(stmt).scalars())


def get_request(db: Session, household_id: int, request_id: int) -> FeatureRequest | None:
    req = db.get(FeatureRequest, request_id)
    if req is None or req.household_id != household_id:
        return None
    return req


def create_request(
    db: Session,
    household_id: int,
    *,
    title: str,
    detail: str | None = None,
    priority: str = "normal",
    requested_by: str | None = None,
) -> FeatureRequest:
    req = FeatureRequest(
        household_id=household_id,
        title=title,
        detail=detail,
        priority=_clean_priority(priority),
        requested_by=requested_by,
        status="new",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def update_request(
    db: Session, household_id: int, request_id: int, **changes
) -> FeatureRequest | None:
    req = get_request(db, household_id, request_id)
    if req is None:
        return None
    for key, value in changes.items():
        if value is None:
            continue
        if key == "status" and _clean_status(value) is None:
            continue  # ignore an unknown status rather than corrupt the lifecycle
        if key == "priority":
            value = _clean_priority(value)
        setattr(req, key, value)
    db.commit()
    db.refresh(req)
    return req


def set_status(
    db: Session,
    household_id: int,
    request_id: int,
    status: str,
    *,
    resolution: str | None = None,
) -> FeatureRequest | None:
    """Convenience wrapper around the lifecycle transition (with optional note)."""
    if _clean_status(status) is None:
        return None
    return update_request(
        db, household_id, request_id, status=status, resolution=resolution
    )


def delete_request(db: Session, household_id: int, request_id: int) -> bool:
    req = get_request(db, household_id, request_id)
    if req is None:
        return False
    db.delete(req)
    db.commit()
    return True


# --- summary (home card) ------------------------------------------------- #
def summary(db: Session, household_id: int) -> ModuleSummary:
    all_requests = list_requests(db, household_id)
    open_requests = [r for r in all_requests if r.status in OPEN_STATUSES]
    in_progress = [r for r in all_requests if r.status == "in_progress"]
    done = [r for r in all_requests if r.status == "done"]

    if not all_requests:
        headline = "Nessuna richiesta"
    elif not open_requests:
        headline = f"Tutto evaso · {len(done)} completate"
    elif in_progress:
        headline = f"{len(open_requests)} aperte · {len(in_progress)} in corso"
    else:
        headline = f"{len(open_requests)} aperte · nessuna in corso"

    items = [
        SummaryItem(
            title=r.title,
            subtitle=(f"{r.status} · {r.priority}"
                      + (f" · {r.requested_by}" if r.requested_by else "")),
            when=humanize_ago(r.created_at),
            severity=(
                "info" if r.status == "in_progress"
                else _PRIORITY_SEVERITY.get(r.priority, "normal")
            ),
        )
        for r in open_requests[:5]
    ]

    return ModuleSummary(
        key=MANIFEST_KEY,
        name="Richieste",
        icon="💡",
        headline=headline,
        stats=[
            StatItem(label="Aperte", value=str(len(open_requests))),
            StatItem(label="In corso", value=str(len(in_progress))),
            StatItem(label="Fatte", value=str(len(done))),
        ],
        items=items,
    )

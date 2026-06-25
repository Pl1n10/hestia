"""Tiles module - service layer (single source of truth).

Pure functions over a Session. Both the REST router and the MCP tools call
these; nothing else touches the tiles_tile table.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.base import ModuleSummary, StatItem, SummaryItem
from app.util import humanize_until

from .models import Tile

MANIFEST_KEY = "tiles"


# --- CRUD ---------------------------------------------------------------- #

def list_tiles(db: Session, household_id: int, *, active_only: bool = True) -> list[Tile]:
    stmt = select(Tile).where(Tile.household_id == household_id)
    if active_only:
        stmt = stmt.where(Tile.active.is_(True))
    stmt = stmt.order_by(Tile.title)
    return list(db.execute(stmt).scalars())


def get_tile(db: Session, household_id: int, tile_id: int) -> Tile | None:
    tile = db.get(Tile, tile_id)
    if tile is None or tile.household_id != household_id:
        return None
    return tile


def create_tile(
    db: Session,
    household_id: int,
    *,
    title: str,
    body: str | None = None,
    color: str = "default",
    size: str = "normal",
    refresh_interval_min: int | None = None,
    next_check_at: date | None = None,
    active: bool = True,
) -> Tile:
    tile = Tile(
        household_id=household_id,
        title=title,
        body=body,
        color=color,
        size=size,
        refresh_interval_min=refresh_interval_min,
        next_check_at=next_check_at,
        active=active,
    )
    db.add(tile)
    db.commit()
    db.refresh(tile)
    return tile


def update_tile(
    db: Session, household_id: int, tile_id: int, **changes
) -> Tile | None:
    tile = get_tile(db, household_id, tile_id)
    if tile is None:
        return None
    for key, value in changes.items():
        setattr(tile, key, value)
    db.commit()
    db.refresh(tile)
    return tile


def delete_tile(db: Session, household_id: int, tile_id: int) -> bool:
    tile = get_tile(db, household_id, tile_id)
    if tile is None:
        return False
    db.delete(tile)
    db.commit()
    return True


# --- analytics ----------------------------------------------------------- #

def overdue_count(db: Session, household_id: int) -> int:
    today = date.today()
    return db.execute(
        select(func.count())
        .select_from(Tile)
        .where(
            Tile.household_id == household_id,
            Tile.active.is_(True),
            Tile.next_check_at.is_not(None),
            Tile.next_check_at < today,
        )
    ).scalar_one()


def _severity_for(next_check_at: date | None) -> str:
    if next_check_at is None:
        return "normal"
    days = (next_check_at - date.today()).days
    if days < 0:
        return "danger"
    if days <= 1:
        return "warning"
    if days <= 7:
        return "info"
    return "normal"


def _sort_key(tile: Tile):
    """Sort tiles: overdue first, then by next_check_at asc, undated last."""
    if tile.next_check_at is None:
        return (1, date.max)
    if tile.next_check_at < date.today():
        return (-1, tile.next_check_at)
    return (0, tile.next_check_at)


# --- summary (home card) ------------------------------------------------- #

def summary(db: Session, household_id: int) -> ModuleSummary:
    active = list_tiles(db, household_id, active_only=True)
    overdue = overdue_count(db, household_id)

    if not active:
        headline = "Nessun riquadro attivo"
    else:
        urgent = [t for t in active if t.next_check_at and t.next_check_at <= date.today()]
        if urgent:
            most_urgent = min(urgent, key=lambda t: t.next_check_at)
            headline = f"⚠ {most_urgent.title} · verifica in scadenza"
        else:
            soon = [t for t in active if t.next_check_at]
            if soon:
                nxt = min(soon, key=lambda t: t.next_check_at)
                headline = f"{nxt.title} · {humanize_until(nxt.next_check_at)}"
            else:
                headline = f"{len(active)} riquadr{'o' if len(active) == 1 else 'i'} attiv{'o' if len(active) == 1 else 'i'}"

    ordered = sorted(active, key=_sort_key)
    items = [
        SummaryItem(
            title=t.title,
            subtitle=t.body,
            when=humanize_until(t.next_check_at) if t.next_check_at else None,
            severity=_severity_for(t.next_check_at),
        )
        for t in ordered
    ]

    return ModuleSummary(
        key=MANIFEST_KEY,
        name="Riquadri",
        icon="📋",
        headline=headline,
        stats=[
            StatItem(label="Attivi", value=str(len(active))),
            StatItem(label="In scadenza", value=str(overdue)),
        ],
        items=items,
    )

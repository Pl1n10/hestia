"""TEMPLATE module - service layer (single source of truth)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.base import ModuleSummary, StatItem

from .models import ExampleItem

MANIFEST_KEY = "example"


def list_items(db: Session, household_id: int) -> list[ExampleItem]:
    return list(
        db.execute(
            select(ExampleItem).where(ExampleItem.household_id == household_id)
        ).scalars()
    )


def create_item(db: Session, household_id: int, *, label: str) -> ExampleItem:
    item = ExampleItem(household_id=household_id, label=label)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def summary(db: Session, household_id: int) -> ModuleSummary:
    items = list_items(db, household_id)
    return ModuleSummary(
        key=MANIFEST_KEY,
        name="Example",
        icon="🧩",
        headline=f"{len(items)} elementi",
        stats=[StatItem(label="Totale", value=str(len(items)))],
        items=[],
    )

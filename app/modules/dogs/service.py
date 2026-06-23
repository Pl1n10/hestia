"""Dogs module - service layer.

Pure functions over a Session. Both the REST router and the MCP tools call
these; nothing else touches the dogs tables.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.base import ModuleSummary, StatItem, SummaryItem
from app.util import humanize_ago

from .models import Dog, DogActivity

MANIFEST_KEY = "dogs"


# --- dogs ---------------------------------------------------------------- #
def list_dogs(db: Session, household_id: int) -> list[Dog]:
    return list(
        db.execute(
            select(Dog).where(Dog.household_id == household_id).order_by(Dog.name)
        ).scalars()
    )


def get_dog(db: Session, household_id: int, dog_id: int) -> Dog | None:
    dog = db.get(Dog, dog_id)
    if dog is None or dog.household_id != household_id:
        return None
    return dog


def find_dog_by_name(db: Session, household_id: int, name: str) -> Dog | None:
    return db.execute(
        select(Dog).where(
            Dog.household_id == household_id, func.lower(Dog.name) == name.strip().lower()
        )
    ).scalar_one_or_none()


def create_dog(
    db: Session,
    household_id: int,
    *,
    name: str,
    breed: str | None = None,
    notes: str | None = None,
) -> Dog:
    dog = Dog(household_id=household_id, name=name, breed=breed, notes=notes)
    db.add(dog)
    db.commit()
    db.refresh(dog)
    return dog


# --- activities ---------------------------------------------------------- #
def log_activity(
    db: Session,
    household_id: int,
    dog_id: int,
    *,
    type: str = "sgambamento",
    occurred_at: datetime | None = None,
    duration_min: int | None = None,
    notes: str | None = None,
    logged_by: str | None = None,
) -> DogActivity:
    activity = DogActivity(
        household_id=household_id,
        dog_id=dog_id,
        type=type,
        occurred_at=occurred_at or datetime.now(timezone.utc),
        duration_min=duration_min,
        notes=notes,
        logged_by=logged_by,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


def recent_activities(
    db: Session, household_id: int, *, dog_id: int | None = None, limit: int = 10
) -> list[DogActivity]:
    stmt = select(DogActivity).where(DogActivity.household_id == household_id)
    if dog_id is not None:
        stmt = stmt.where(DogActivity.dog_id == dog_id)
    stmt = stmt.order_by(DogActivity.occurred_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars())


# --- summary (home card) ------------------------------------------------- #
def summary(db: Session, household_id: int) -> ModuleSummary:
    dogs = list_dogs(db, household_id)
    recent = recent_activities(db, household_id, limit=5)

    if not dogs:
        headline = "Nessun cane registrato"
    else:
        last = recent[0] if recent else None
        if last is not None:
            dog = db.get(Dog, last.dog_id)
            who = dog.name if dog else "?"
            headline = f"{who}: ultimo {last.type} {humanize_ago(last.occurred_at)}"
        else:
            headline = f"{dogs[0].name}: nessuna attività registrata"

    start_of_day = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
    today_count = (
        db.execute(
            select(func.count())
            .select_from(DogActivity)
            .where(
                DogActivity.household_id == household_id,
                DogActivity.occurred_at >= start_of_day,
            )
        ).scalar_one()
    )

    items = [
        SummaryItem(
            title=f"{(db.get(Dog, a.dog_id).name if db.get(Dog, a.dog_id) else '?')} - {a.type}",
            subtitle=a.notes,
            when=humanize_ago(a.occurred_at),
        )
        for a in recent
    ]

    return ModuleSummary(
        key=MANIFEST_KEY,
        name="Cani",
        icon="🐕",
        headline=headline,
        stats=[
            StatItem(label="Cani", value=str(len(dogs))),
            StatItem(label="Attività oggi", value=str(today_count)),
        ],
        items=items,
    )

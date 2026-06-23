"""Dogs module - models. Shape: an append-mostly activity log per dog."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# Reference set; validated in schemas. Free-form is allowed for forward-compat.
ACTIVITY_TYPES = (
    "sgambamento",
    "passeggiata",
    "pappa",
    "vet",
    "toelettatura",
    "farmaco",
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Dog(Base):
    __tablename__ = "dogs_dog"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(80))
    breed: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    activities: Mapped[list["DogActivity"]] = relationship(
        back_populates="dog", cascade="all, delete-orphan"
    )


class DogActivity(Base):
    __tablename__ = "dogs_activity"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(Integer, index=True)
    dog_id: Mapped[int] = mapped_column(ForeignKey("dogs_dog.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(40), default="sgambamento")
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    logged_by: Mapped[str | None] = mapped_column(String(120), nullable=True)

    dog: Mapped[Dog] = relationship(back_populates="activities")

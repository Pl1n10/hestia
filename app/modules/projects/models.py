"""Projects module - ORM model.

Shape: managed entity with a status lifecycle. Tracks active development
projects (GitHub repos, local tools, etc.) so the household has a single
view of cross-project development activity.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

STATUSES = ("active", "paused", "completed")
ACTIVE_STATUSES = ("active", "paused")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects_project"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # active | paused | completed
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    repo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Free-text summary of the most recent notable activity (commit, PR, issue).
    last_activity: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

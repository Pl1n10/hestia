"""Feature-requests module - model.

Shape: a managed entity with a small lifecycle. This is the *meta* module of
the dashboard: it is how the agent (Hermes) asks for the dashboard itself to
grow. Hermes files a request here; Claude Code reads it, builds the feature,
and flips the status. Same data, both surfaces (DECISIONS D-002).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# Lifecycle. `new` -> Hermes just filed it; `in_progress` -> Claude Code is
# building it; `done` -> shipped; `rejected` -> won't do (with a reason in notes).
STATUSES = ("new", "in_progress", "done", "rejected")
OPEN_STATUSES = ("new", "in_progress")
PRIORITIES = ("low", "normal", "high")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FeatureRequest(Base):
    __tablename__ = "featreq_request"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(160))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="new", index=True)
    priority: Mapped[str] = mapped_column(String(8), default="normal")
    # Who asked for it. For agent-filed requests Hermes passes the human's name;
    # falls back to the principal's display name.
    requested_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Free text for the implementer: triage notes, rejection reason, PR link.
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

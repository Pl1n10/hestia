"""TEMPLATE module - models. Copy this folder to start a new module.

`scripts/new_module.py <key>` clones this and replaces the token `example`
(and `Example`) with your module key. This module is NOT auto-loaded.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ExampleItem(Base):
    __tablename__ = "example_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(Integer, index=True)
    label: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

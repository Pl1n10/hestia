"""Tiles module - models.

Shape: user-defined dashboard tiles with optional reminders.
Each tile is a custom widget shown on the dashboard: title, content,
color/size hints for the UI, an optional refresh interval, and an
optional next-check date for reminder-style tiles.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

COLORS = ("default", "blue", "green", "yellow", "red", "purple")
SIZES = ("small", "normal", "large")


class Tile(Base):
    __tablename__ = "tiles_tile"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(String(30), default="default")
    size: Mapped[str] = mapped_column(String(10), default="normal")
    refresh_interval_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_check_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

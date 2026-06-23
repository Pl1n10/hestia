"""Subscriptions module - model.

Shape: managed recurring entities with a renewal date and a cost. The same
pattern generalises to vehicles (bollo/assicurazione) and utilities (bollette),
which is why this module is a deliberate reference implementation.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

CYCLES = ("weekly", "monthly", "quarterly", "yearly")


class Subscription(Base):
    __tablename__ = "subs_subscription"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(120))
    vendor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    cycle: Mapped[str] = mapped_column(String(16), default="monthly")
    next_renewal: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    owner_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

"""Vehicles module - models.

Shape: managed entities (vehicles) each owning a set of dated expenses
(bollo, assicurazione, tagliando). Follows the subscriptions pattern for
money (Numeric + Decimal) and the dogs pattern for a parent + child table.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

EXPENSE_CATEGORIES = ("bollo", "assicurazione", "tagliando")


class Vehicle(Base):
    __tablename__ = "vehicles_vehicle"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(120))
    plate: Mapped[str | None] = mapped_column(String(20), nullable=True)
    make: Mapped[str | None] = mapped_column(String(80), nullable=True)
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    expenses: Mapped[list["VehicleExpense"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan"
    )


class VehicleExpense(Base):
    __tablename__ = "vehicles_expense"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(Integer, index=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles_vehicle.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(20))  # bollo | assicurazione | tagliando
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    paid_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    vehicle: Mapped[Vehicle] = relationship(back_populates="expenses")

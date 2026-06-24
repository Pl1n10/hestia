"""Vehicles module - schemas.

``amount`` is float at the JSON boundary; the DB stores Numeric(10,2).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from .models import EXPENSE_CATEGORIES


class VehicleIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    plate: str | None = None
    make: str | None = None
    model: str | None = None
    year: int | None = None
    notes: str | None = None
    active: bool = True


class VehicleUpdate(BaseModel):
    name: str | None = None
    plate: str | None = None
    make: str | None = None
    model: str | None = None
    year: int | None = None
    notes: str | None = None
    active: bool | None = None


class VehicleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    plate: str | None = None
    make: str | None = None
    model: str | None = None
    year: int | None = None
    notes: str | None = None
    active: bool


class ExpenseIn(BaseModel):
    category: str
    amount: float = Field(default=0.0, ge=0)
    currency: str = "EUR"
    due_date: date | None = None
    paid_date: date | None = None
    notes: str | None = None

    def normalised_category(self) -> str:
        return self.category if self.category in EXPENSE_CATEGORIES else "tagliando"


class ExpenseUpdate(BaseModel):
    category: str | None = None
    amount: float | None = Field(default=None, ge=0)
    currency: str | None = None
    due_date: date | None = None
    paid_date: date | None = None
    notes: str | None = None


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    category: str
    amount: float
    currency: str
    due_date: date | None = None
    paid_date: date | None = None
    notes: str | None = None

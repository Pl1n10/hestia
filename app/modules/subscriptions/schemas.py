"""Subscriptions module - schemas.

Public surfaces expose ``amount`` as a float for clean JSON; the DB stores
Numeric(10,2) and cost rollups are computed in Decimal to avoid drift.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from .models import CYCLES


class SubscriptionIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    vendor: str | None = None
    amount: float = Field(ge=0)
    currency: str = "EUR"
    cycle: str = "monthly"
    next_renewal: date | None = None
    category: str | None = None
    owner_user_id: int | None = None
    active: bool = True
    notes: str | None = None

    def normalised_cycle(self) -> str:
        return self.cycle if self.cycle in CYCLES else "monthly"


class SubscriptionUpdate(BaseModel):
    name: str | None = None
    vendor: str | None = None
    amount: float | None = Field(default=None, ge=0)
    currency: str | None = None
    cycle: str | None = None
    next_renewal: date | None = None
    category: str | None = None
    owner_user_id: int | None = None
    active: bool | None = None
    notes: str | None = None


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    vendor: str | None = None
    amount: float
    currency: str = "EUR"
    cycle: str
    next_renewal: date | None = None
    category: str | None = None
    owner_user_id: int | None = None
    active: bool
    notes: str | None = None


class CostBreakdown(BaseModel):
    currency: str = "EUR"
    monthly: float
    yearly: float
    active_count: int

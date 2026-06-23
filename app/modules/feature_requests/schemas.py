"""Feature-requests module - request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import PRIORITIES, STATUSES


class FeatureRequestIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    detail: str | None = None
    priority: str = "normal"
    requested_by: str | None = None

    def normalised_priority(self) -> str:
        return self.priority if self.priority in PRIORITIES else "normal"


class FeatureRequestUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    detail: str | None = None
    status: str | None = None
    priority: str | None = None
    resolution: str | None = None


class FeatureRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    detail: str | None = None
    status: str
    priority: str
    requested_by: str | None = None
    resolution: str | None = None
    created_at: datetime
    updated_at: datetime


# Exposed so other surfaces/tests can advertise the valid enums without
# reaching into models.
VALID_STATUSES = STATUSES
VALID_PRIORITIES = PRIORITIES

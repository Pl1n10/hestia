"""Projects module - request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import STATUSES


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    status: str = "active"
    repo_url: str | None = None
    last_activity: str | None = None
    last_activity_at: datetime | None = None

    def normalised_status(self) -> str:
        return self.status if self.status in STATUSES else "active"


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    status: str | None = None
    repo_url: str | None = None
    last_activity: str | None = None
    last_activity_at: datetime | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None = None
    status: str
    repo_url: str | None = None
    last_activity: str | None = None
    last_activity_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


VALID_STATUSES = STATUSES

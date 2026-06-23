"""Dogs module - request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DogIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    breed: str | None = None
    notes: str | None = None


class DogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    breed: str | None = None
    notes: str | None = None


class ActivityIn(BaseModel):
    type: str = "sgambamento"
    occurred_at: datetime | None = None
    duration_min: int | None = Field(default=None, ge=0, le=1440)
    notes: str | None = None


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    dog_id: int
    type: str
    occurred_at: datetime
    duration_min: int | None = None
    notes: str | None = None
    logged_by: str | None = None

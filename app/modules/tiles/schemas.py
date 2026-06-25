"""Tiles module - request/response schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class TileIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    body: str | None = None
    color: str = "default"
    size: str = "normal"
    refresh_interval_min: int | None = Field(default=None, ge=1)
    next_check_at: date | None = None


class TileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str | None = None
    color: str
    size: str
    refresh_interval_min: int | None = None
    next_check_at: date | None = None
    active: bool


class TileUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    body: str | None = None
    color: str | None = None
    size: str | None = None
    refresh_interval_min: int | None = Field(default=None, ge=1)
    next_check_at: date | None = None
    active: bool | None = None

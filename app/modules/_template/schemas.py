"""TEMPLATE module - schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExampleIn(BaseModel):
    label: str = Field(min_length=1, max_length=120)


class ExampleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    label: str

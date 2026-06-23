"""TEMPLATE module - REST surface."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import Principal
from app.deps import current_principal, get_db

from . import service
from .schemas import ExampleIn, ExampleOut

router = APIRouter()


@router.get("/items", response_model=list[ExampleOut])
def list_items(p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    return service.list_items(db, p.household_id)


@router.post("/items", response_model=ExampleOut, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ExampleIn,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    return service.create_item(db, p.household_id, label=payload.label)

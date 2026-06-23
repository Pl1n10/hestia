"""Dogs module - REST surface (thin adapter over service.py)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import Principal
from app.deps import current_principal, get_db

from . import service
from .schemas import ActivityIn, ActivityOut, DogIn, DogOut

router = APIRouter()


@router.get("/dogs", response_model=list[DogOut])
def list_dogs(p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    return service.list_dogs(db, p.household_id)


@router.post("/dogs", response_model=DogOut, status_code=status.HTTP_201_CREATED)
def create_dog(
    payload: DogIn,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    return service.create_dog(
        db, p.household_id, name=payload.name, breed=payload.breed, notes=payload.notes
    )


@router.get("/dogs/{dog_id}", response_model=DogOut)
def get_dog(
    dog_id: int, p: Principal = Depends(current_principal), db: Session = Depends(get_db)
):
    dog = service.get_dog(db, p.household_id, dog_id)
    if dog is None:
        raise HTTPException(status_code=404, detail="Dog not found")
    return dog


@router.post(
    "/dogs/{dog_id}/activities",
    response_model=ActivityOut,
    status_code=status.HTTP_201_CREATED,
)
def log_activity(
    dog_id: int,
    payload: ActivityIn,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    if service.get_dog(db, p.household_id, dog_id) is None:
        raise HTTPException(status_code=404, detail="Dog not found")
    return service.log_activity(
        db,
        p.household_id,
        dog_id,
        type=payload.type,
        occurred_at=payload.occurred_at,
        duration_min=payload.duration_min,
        notes=payload.notes,
        logged_by=p.display_name,
    )


@router.get("/dogs/{dog_id}/activities", response_model=list[ActivityOut])
def list_activities(
    dog_id: int,
    limit: int = 20,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    if service.get_dog(db, p.household_id, dog_id) is None:
        raise HTTPException(status_code=404, detail="Dog not found")
    return service.recent_activities(db, p.household_id, dog_id=dog_id, limit=limit)


@router.get("/activities", response_model=list[ActivityOut])
def recent_activities(
    limit: int = 20,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    return service.recent_activities(db, p.household_id, limit=limit)

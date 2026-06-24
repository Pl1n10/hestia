"""Vehicles module - REST surface (thin adapter over service.py)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import Principal
from app.deps import current_principal, get_db

from . import service
from .schemas import ExpenseIn, ExpenseOut, ExpenseUpdate, VehicleIn, VehicleOut, VehicleUpdate

router = APIRouter()


# --- vehicles ---------------------------------------------------------------- #

@router.get("/vehicles", response_model=list[VehicleOut])
def list_vehicles(
    active_only: bool = False,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    return service.list_vehicles(db, p.household_id, active_only=active_only)


@router.post("/vehicles", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    payload: VehicleIn,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    return service.create_vehicle(db, p.household_id, **payload.model_dump())


# /vehicles/upcoming must be declared before /vehicles/{vehicle_id} to avoid
# FastAPI routing the literal string "upcoming" as a vehicle_id.
@router.get("/vehicles/upcoming", response_model=list[ExpenseOut])
def upcoming_expenses(
    days: int = 30,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    return service.upcoming_expenses(db, p.household_id, days=days)


@router.get("/vehicles/{vehicle_id}", response_model=VehicleOut)
def get_vehicle(
    vehicle_id: int,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    v = service.get_vehicle(db, p.household_id, vehicle_id)
    if v is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return v


@router.patch("/vehicles/{vehicle_id}", response_model=VehicleOut)
def update_vehicle(
    vehicle_id: int,
    payload: VehicleUpdate,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    v = service.update_vehicle(
        db, p.household_id, vehicle_id, **payload.model_dump(exclude_unset=True)
    )
    if v is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return v


@router.delete("/vehicles/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(
    vehicle_id: int,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    if not service.delete_vehicle(db, p.household_id, vehicle_id):
        raise HTTPException(status_code=404, detail="Vehicle not found")


# --- expenses ---------------------------------------------------------------- #

@router.get("/vehicles/{vehicle_id}/expenses", response_model=list[ExpenseOut])
def list_expenses(
    vehicle_id: int,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    if service.get_vehicle(db, p.household_id, vehicle_id) is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return service.list_expenses(db, p.household_id, vehicle_id=vehicle_id)


@router.post(
    "/vehicles/{vehicle_id}/expenses",
    response_model=ExpenseOut,
    status_code=status.HTTP_201_CREATED,
)
def create_expense(
    vehicle_id: int,
    payload: ExpenseIn,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    if service.get_vehicle(db, p.household_id, vehicle_id) is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    data = payload.model_dump()
    data["category"] = payload.normalised_category()
    return service.create_expense(db, p.household_id, vehicle_id, **data)


@router.patch(
    "/vehicles/{vehicle_id}/expenses/{expense_id}", response_model=ExpenseOut
)
def update_expense(
    vehicle_id: int,
    expense_id: int,
    payload: ExpenseUpdate,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    if service.get_vehicle(db, p.household_id, vehicle_id) is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    exp = service.update_expense(
        db, p.household_id, expense_id, **payload.model_dump(exclude_unset=True)
    )
    if exp is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    return exp


@router.delete(
    "/vehicles/{vehicle_id}/expenses/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_expense(
    vehicle_id: int,
    expense_id: int,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    if service.get_vehicle(db, p.household_id, vehicle_id) is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if not service.delete_expense(db, p.household_id, expense_id):
        raise HTTPException(status_code=404, detail="Expense not found")

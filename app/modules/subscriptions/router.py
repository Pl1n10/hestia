"""Subscriptions module - REST surface."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import Principal
from app.deps import current_principal, get_db

from . import service
from .schemas import (
    CostBreakdown,
    SubscriptionIn,
    SubscriptionOut,
    SubscriptionUpdate,
)

router = APIRouter()


@router.get("/subscriptions", response_model=list[SubscriptionOut])
def list_subscriptions(
    active_only: bool = False,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    return service.list_subscriptions(db, p.household_id, active_only=active_only)


@router.post(
    "/subscriptions", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED
)
def create_subscription(
    payload: SubscriptionIn,
    allow_duplicate: bool = False,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump()
    data["cycle"] = payload.normalised_cycle()
    try:
        return service.create_subscription(
            db, p.household_id, allow_duplicate=allow_duplicate, **data
        )
    except service.DuplicateSubscriptionError as exc:
        # Don't silently create a second "Netflix"; point the caller at the
        # existing row. Pass ?allow_duplicate=true to override deliberately.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "duplicate_subscription",
                "message": str(exc),
                "existing_id": exc.existing.id,
                "hint": "Update it (PATCH .../subscriptions/{id}) or delete it, "
                "or POST again with ?allow_duplicate=true.",
            },
        ) from exc


@router.get("/subscriptions/cost", response_model=CostBreakdown)
def cost(p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    monthly = service.monthly_cost(db, p.household_id)
    active = service.list_subscriptions(db, p.household_id, active_only=True)
    return CostBreakdown(
        monthly=float(monthly), yearly=float(monthly * 12), active_count=len(active)
    )


@router.get("/subscriptions/upcoming", response_model=list[SubscriptionOut])
def upcoming(
    days: int = 30,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    return service.upcoming(db, p.household_id, days=days)


@router.get("/subscriptions/{sub_id}", response_model=SubscriptionOut)
def get_subscription(
    sub_id: int, p: Principal = Depends(current_principal), db: Session = Depends(get_db)
):
    sub = service.get_subscription(db, p.household_id, sub_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return sub


@router.patch("/subscriptions/{sub_id}", response_model=SubscriptionOut)
def update_subscription(
    sub_id: int,
    payload: SubscriptionUpdate,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    sub = service.update_subscription(
        db, p.household_id, sub_id, **payload.model_dump(exclude_unset=True)
    )
    if sub is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return sub


@router.delete("/subscriptions/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(
    sub_id: int, p: Principal = Depends(current_principal), db: Session = Depends(get_db)
):
    if not service.delete_subscription(db, p.household_id, sub_id):
        raise HTTPException(status_code=404, detail="Subscription not found")

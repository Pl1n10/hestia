"""Feature-requests module - REST surface (thin adapter over service.py)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import Principal
from app.deps import current_principal, get_db

from . import service
from .schemas import FeatureRequestIn, FeatureRequestOut, FeatureRequestUpdate

router = APIRouter()


@router.get("/requests", response_model=list[FeatureRequestOut])
def list_requests(
    status: str | None = None,
    open_only: bool = False,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    return service.list_requests(db, p.household_id, status=status, open_only=open_only)


@router.post(
    "/requests", response_model=FeatureRequestOut, status_code=status.HTTP_201_CREATED
)
def create_request(
    payload: FeatureRequestIn,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    return service.create_request(
        db,
        p.household_id,
        title=payload.title,
        detail=payload.detail,
        priority=payload.normalised_priority(),
        # Attribute to whoever the caller says asked, else to the caller itself.
        requested_by=payload.requested_by or p.display_name,
    )


@router.get("/requests/{request_id}", response_model=FeatureRequestOut)
def get_request(
    request_id: int,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    req = service.get_request(db, p.household_id, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Feature request not found")
    return req


@router.patch("/requests/{request_id}", response_model=FeatureRequestOut)
def update_request(
    request_id: int,
    payload: FeatureRequestUpdate,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    req = service.update_request(
        db, p.household_id, request_id, **payload.model_dump(exclude_unset=True)
    )
    if req is None:
        raise HTTPException(status_code=404, detail="Feature request not found")
    return req


@router.delete("/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_request(
    request_id: int,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    if not service.delete_request(db, p.household_id, request_id):
        raise HTTPException(status_code=404, detail="Feature request not found")

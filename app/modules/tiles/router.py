"""Tiles module - REST surface (thin adapter over service.py)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import Principal
from app.deps import current_principal, get_db

from . import service
from .schemas import TileIn, TileOut, TileUpdate

router = APIRouter()


@router.get("/tiles", response_model=list[TileOut])
def list_tiles(
    active_only: bool = True,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    return service.list_tiles(db, p.household_id, active_only=active_only)


@router.post("/tiles", response_model=TileOut, status_code=status.HTTP_201_CREATED)
def create_tile(
    payload: TileIn,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    return service.create_tile(
        db,
        p.household_id,
        title=payload.title,
        body=payload.body,
        color=payload.color,
        size=payload.size,
        refresh_interval_min=payload.refresh_interval_min,
        next_check_at=payload.next_check_at,
    )


@router.get("/tiles/{tile_id}", response_model=TileOut)
def get_tile(
    tile_id: int,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    tile = service.get_tile(db, p.household_id, tile_id)
    if tile is None:
        raise HTTPException(status_code=404, detail="Tile not found")
    return tile


@router.patch("/tiles/{tile_id}", response_model=TileOut)
def update_tile(
    tile_id: int,
    payload: TileUpdate,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    tile = service.update_tile(
        db, p.household_id, tile_id, **payload.model_dump(exclude_unset=True)
    )
    if tile is None:
        raise HTTPException(status_code=404, detail="Tile not found")
    return tile


@router.delete("/tiles/{tile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tile(
    tile_id: int,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    if not service.delete_tile(db, p.household_id, tile_id):
        raise HTTPException(status_code=404, detail="Tile not found")

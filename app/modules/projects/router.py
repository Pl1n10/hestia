"""Projects module - REST surface (thin adapter over service.py)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import Principal
from app.deps import current_principal, get_db

from . import service
from .schemas import ProjectIn, ProjectOut, ProjectUpdate

router = APIRouter()


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(
    status: str | None = None,
    active_only: bool = False,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    return service.list_projects(db, p.household_id, status=status, active_only=active_only)


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectIn,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    return service.create_project(
        db,
        p.household_id,
        name=payload.name,
        description=payload.description,
        status=payload.normalised_status(),
        repo_url=payload.repo_url,
        last_activity=payload.last_activity,
        last_activity_at=payload.last_activity_at,
    )


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    proj = service.get_project(db, p.household_id, project_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    proj = service.update_project(
        db, p.household_id, project_id, **payload.model_dump(exclude_unset=True)
    )
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    p: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
):
    if not service.delete_project(db, p.household_id, project_id):
        raise HTTPException(status_code=404, detail="Project not found")

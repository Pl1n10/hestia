"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import Principal, resolve_principal
from app.db import get_session


def get_db() -> Iterator[Session]:
    yield from get_session()


def current_principal(request: Request, db: Session = Depends(get_db)) -> Principal:
    principal = resolve_principal(dict(request.headers), db)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal

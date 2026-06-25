"""Shared test fixtures.

The env is configured *before* any app import so the settings singleton picks
up a throwaway SQLite file and a known module set. Each test runs against fresh
tables (drop + create) for isolation, since the service layer commits eagerly.
"""

from __future__ import annotations

import os
import tempfile

import pytest

# --- configure the app for testing BEFORE it is imported anywhere ---------- #
_DB_FD, _DB_PATH = tempfile.mkstemp(prefix="hestia_test_", suffix=".db")
os.close(_DB_FD)
os.environ["HESTIA_DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ["HESTIA_ENABLED_MODULES"] = "dogs,subscriptions,feature_requests,projects"
os.environ["HESTIA_AUTH_MODE"] = "dev"
os.environ["HESTIA_AGENT_TOKEN"] = "test-master-token"
os.environ["HESTIA_DEFAULT_HOUSEHOLD_ID"] = "1"

AGENT_TOKEN = "test-master-token"
HOUSEHOLD_ID = 1


@pytest.fixture(autouse=True)
def fresh_tables():
    """Recreate all tables before each test."""
    import app.core_models  # noqa: F401  (register core tables)
    from app.db import Base, engine
    from app.modules import load_enabled

    load_enabled()  # register module tables on the shared metadata
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def db():
    from app.db import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def household(db):
    """A persisted household + owner (some flows want the rows to exist)."""
    from app.core_models import Household, User

    hh = Household(id=HOUSEHOLD_ID, name="Casa Test")
    db.add(hh)
    db.flush()
    db.add(User(household_id=hh.id, name="Roberto", email="roberto@casa.local", role="owner"))
    db.commit()
    return hh


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def agent_headers():
    return {"Authorization": f"Bearer {AGENT_TOKEN}"}

"""SQLAlchemy 2.0 setup: engine, declarative Base, session factory, init."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.settings import settings

_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _record):  # pragma: no cover - driver glue
    """WAL for concurrent reads while the agent writes; enforce foreign keys."""
    if not _is_sqlite:
        return
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


SessionLocal = sessionmaker(
    bind=engine, autoflush=False, expire_on_commit=False, class_=Session
)


class Base(DeclarativeBase):
    """Single declarative base shared by core + every module."""


def init_db() -> None:
    """Import all model-bearing packages, then create tables.

    Importing ``app.core_models`` and ``app.modules`` is what registers ORM
    classes on ``Base.metadata``. Only *enabled* modules are imported, so
    disabled modules never create tables.
    """
    import app.core_models  # noqa: F401  (registers core tables)
    from app.modules import load_enabled

    load_enabled()  # imports enabled module packages -> registers their models
    Base.metadata.create_all(bind=engine)


def get_session() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

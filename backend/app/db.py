"""Database engine + session management.

SQLite by default (zero infra); the same SQLModel schema runs on PostgreSQL in production. Foreign
keys are enforced on SQLite via a PRAGMA so referential-integrity tests behave like Postgres.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

_settings = get_settings()


def _ensure_sqlite_dir(url: str) -> None:
    """Make sure the parent dir for a file-based SQLite DB exists."""
    prefix = "sqlite:///"
    if url.startswith(prefix):
        db_path = url[len(prefix):]
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(_settings.database_url)

_connect_args = {"check_same_thread": False} if _settings.is_sqlite else {}
engine: Engine = create_engine(
    _settings.database_url,
    echo=os.getenv("VRA_SQL_ECHO") == "1",
    connect_args=_connect_args,
)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record):  # noqa: ANN001
    """Enforce FK constraints on SQLite (off by default)."""
    if _settings.is_sqlite:
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


def init_db() -> None:
    """Create all tables. Import models for side-effect registration first."""
    import app.domain.models  # noqa: F401  (registers tables on SQLModel.metadata)

    SQLModel.metadata.create_all(engine)


def drop_all() -> None:
    import app.domain.models  # noqa: F401

    SQLModel.metadata.drop_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: a request-scoped session."""
    with Session(engine) as session:
        yield session

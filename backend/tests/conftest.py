"""Shared pytest fixtures: an isolated in-memory DB seeded with the Northstar scenario."""

from __future__ import annotations

import pytest
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.domain import models  # noqa: F401  (register tables)
from app.seed import seed_all


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _fk(dbapi_connection, _record):  # noqa: ANN001
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine):
    with Session(engine) as s:
        seed_all(s)
        try:
            from app.rag.corpus import seed_documents

            seed_documents(s)
        except Exception:
            pass  # corpus optional for non-RAG tests
        yield s

"""Reliability tests (Phase 12): transactional-outbox relay, dead-lettering, deep health, correlation IDs."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import get_session
from app.domain.models import OutboxEvent
from app.main import app
from app.workflow.audit import MAX_OUTBOX_ATTEMPTS, drain_outbox, outbox_stats, publish_outbox


@pytest.fixture()
def client(session: Session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_drain_outbox_publishes_then_is_idempotent(session):
    publish_outbox(session, topic="recovery.decision", payload={"a": 1}, correlation_id="cor-1")
    publish_outbox(session, topic="agent.event", payload={"b": 2}, correlation_id="cor-1")
    assert outbox_stats(session)["pending"] == 2

    published = drain_outbox(session)
    assert published == 2
    rows = session.exec(select(OutboxEvent)).all()
    assert all(r.status == "published" and r.published_at is not None for r in rows)

    # Nothing left to publish — the relay is idempotent.
    assert drain_outbox(session) == 0
    assert outbox_stats(session) == {"pending": 0, "published": 2, "failed": 0}


def test_drain_outbox_dead_letters_after_max_attempts(session):
    publish_outbox(session, topic="recovery.decision", payload={}, correlation_id="cor-x")

    def failing_sink(_t, _p, _c):
        raise RuntimeError("broker down")

    for _ in range(MAX_OUTBOX_ATTEMPTS):
        drain_outbox(session, sink=failing_sink)

    evt = session.exec(select(OutboxEvent)).first()
    assert evt.status == "failed"
    assert evt.attempts >= MAX_OUTBOX_ATTEMPTS
    assert "broker down" in evt.last_error


def test_health_reports_db_and_outbox(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["db"] is True
    assert "outbox" in body and isinstance(body["outbox"], dict)


def test_correlation_id_is_propagated_and_generated(client):
    echoed = client.get("/health", headers={"X-Correlation-Id": "trace-abc"})
    assert echoed.headers.get("X-Correlation-Id") == "trace-abc"

    generated = client.get("/health")
    assert generated.headers.get("X-Correlation-Id", "").startswith("req-")

"""Procedure applicability: a future-dated revision must not be retrieved until it is effective.
(Closes the gap where effective_date was stored but never enforced — a doc effective tomorrow returned
today.) Approval + supersession + effective-date are all hard gates applied BEFORE similarity ranking."""

from __future__ import annotations

from datetime import timedelta

from sqlmodel import select

from app.domain.base import utcnow
from app.domain.enums import DocApprovalStatus
from app.domain.models import DocumentChunk
from app.rag.retrieval import search


def test_future_dated_procedure_not_retrieved_until_effective(session):
    chunk = next((c for c in session.exec(select(DocumentChunk)).all()
                  if c.approval_status == DocApprovalStatus.APPROVED and not c.superseded_by), None)
    assert chunk is not None, "seeded corpus should contain an approved chunk"
    h, q = chunk.content_hash, chunk.content[:60]

    # authoritative today
    assert any(c.content_hash == h for c in search(session, q, approved_only=True, k=50))

    # make it effective tomorrow → must drop out of today's retrieval
    chunk.effective_date = utcnow() + timedelta(days=1)
    session.add(chunk)
    session.commit()
    assert not any(c.content_hash == h for c in search(session, q, approved_only=True, k=50))

    # …but it IS authoritative when evaluated as-of after its effective date
    later = search(session, q, approved_only=True, k=50, as_of=utcnow() + timedelta(days=2))
    assert any(c.content_hash == h for c in later)

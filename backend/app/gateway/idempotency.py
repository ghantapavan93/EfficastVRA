"""Idempotency ledger for write actions — once-only effects keyed by an idempotency key."""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session

from app.config import get_settings
from app.domain.models import IdempotencyRecord

_settings = get_settings()


def lookup(session: Session, key: str) -> Optional[IdempotencyRecord]:
    return session.get(IdempotencyRecord, key)


def remember(session: Session, key: str, *, scope: str, result_ref: str, detail: dict) -> IdempotencyRecord:
    rec = IdempotencyRecord(
        id=key, tenant_id=_settings.tenant_id, scope=scope, result_ref=result_ref, detail=detail
    )
    session.add(rec)
    session.flush()
    return rec

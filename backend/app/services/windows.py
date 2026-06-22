"""Verification-window helpers."""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from app.config import get_settings
from app.domain.base import utcnow
from app.domain.models import RecoveryContract, RecoveryWindow

_settings = get_settings()


def get_active_window(session: Session, contract: RecoveryContract) -> Optional[RecoveryWindow]:
    return session.exec(
        select(RecoveryWindow)
        .where(RecoveryWindow.contract_id == contract.id)
        .where(RecoveryWindow.status.in_(["open", "monitoring"]))  # type: ignore[attr-defined]
        .order_by(RecoveryWindow.sequence.desc())
    ).first()


def open_window(
    session: Session,
    *,
    incident_id: str,
    contract: RecoveryContract,
    sequence: int,
    required_stable_cycles: int,
    baseline: dict,
) -> RecoveryWindow:
    win = RecoveryWindow(
        tenant_id=_settings.tenant_id,
        incident_id=incident_id,
        contract_id=contract.id,
        sequence=sequence,
        required_stable_cycles=required_stable_cycles,
        status="open",
        baseline=baseline,
        opened_at=utcnow(),
    )
    session.add(win)
    session.flush()
    return win

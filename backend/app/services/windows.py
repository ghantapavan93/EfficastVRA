"""Verification-window helpers."""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from app.config import get_settings
from app.domain.base import utcnow
from app.domain.models import RecoveryContract, RecoveryWindow

_settings = get_settings()

# The plant's *normal* operating context — the reference the Comparable-Conditions Gate compares a
# verification window against. Synthetic PROTOTYPE_ASSUMPTION; in a real deployment this comes from the MES.
DEFAULT_OPERATING_CONTEXT: dict = {
    "product": "PKG-STD-12",
    "speed_pct": 95.0,
    "load": "nominal",
    "material_lot": "LOT-7741",
    "machine_mode": "AUTO",
    "shift": "A",
    "ambient_c": 24.0,
    "sensor_health": "ok",
}


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
    baseline_context: Optional[dict] = None,
    observed_context: Optional[dict] = None,
) -> RecoveryWindow:
    win = RecoveryWindow(
        tenant_id=_settings.tenant_id,
        incident_id=incident_id,
        contract_id=contract.id,
        sequence=sequence,
        required_stable_cycles=required_stable_cycles,
        status="open",
        baseline=baseline,
        baseline_context=baseline_context if baseline_context is not None else dict(DEFAULT_OPERATING_CONTEXT),
        observed_context=observed_context if observed_context is not None else dict(DEFAULT_OPERATING_CONTEXT),
        opened_at=utcnow(),
    )
    session.add(win)
    session.flush()
    return win

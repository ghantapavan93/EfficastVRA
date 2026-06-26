"""Telemetry source abstraction — the real-data seam.

The cycle engine consumes one sample per cycle from a ``TelemetrySource``. In synthetic mode that is
``ScenarioPhysics``; when real readings have been ingested for a machine (via ``POST /api/telemetry``,
or a future Efficast Edge stream), ``IngestedTelemetrySource`` serves them and the *same* deterministic
evaluator verifies recovery on real data. Nothing else in the system changes.
"""

from __future__ import annotations

import abc
from typing import Optional

from sqlmodel import Session, select

from app.adapters.synthetic import ScenarioPhysics
from app.domain.base import utcnow
from app.domain.models import TelemetrySample

# Synthetic samples are generated in-process, so they're effectively "just now" — a small, honest
# constant rather than a claim of real-sensor freshness.
_SYNTHETIC_FRESHNESS_S = 2
_SYNTHETIC_LABEL = "SyntheticEfficastPort"


class TelemetrySource(abc.ABC):
    @abc.abstractmethod
    def next_sample(self, *, machine_id: str, window_seq: int, cycle_index: int, baseline: dict) -> dict:
        """Return one cycle's reading: vibration/temperature/cycle_time/scrap_pct/fault_code (+extras)."""
        ...

    def provenance(self) -> tuple[str, int]:
        """``(source label, freshness seconds)`` for the most recently served sample.

        Honest provenance: synthetic data is labelled as such; ingested data carries its *real* source
        and *real* age. The cycle engine stamps these onto the observation instead of the old hardcoded
        ``("SyntheticEfficastPort", 2)`` — which lied on ingested data (the product's own
        "can we trust the evidence?" thesis applied to its data layer)."""
        return (_SYNTHETIC_LABEL, _SYNTHETIC_FRESHNESS_S)


class SyntheticTelemetrySource(TelemetrySource):
    """Deterministic synthetic plant (the demo default)."""

    def __init__(self, physics: ScenarioPhysics | None = None):
        self.physics = physics or ScenarioPhysics()

    def next_sample(self, *, machine_id: str, window_seq: int, cycle_index: int, baseline: dict) -> dict:
        return self.physics.synthesize_cycle(window_seq, cycle_index, baseline)


class IngestedTelemetrySource(TelemetrySource):
    """Serves real readings ingested for a machine, FIFO, marking each consumed exactly once."""

    def __init__(self, session: Session):
        self.session = session
        self._last: Optional[TelemetrySample] = None

    def has_data(self, machine_id: str) -> bool:
        return self.session.exec(
            select(TelemetrySample).where(TelemetrySample.machine_id == machine_id)
            .where(TelemetrySample.consumed == False)  # noqa: E712
        ).first() is not None

    def next_sample(self, *, machine_id: str, window_seq: int, cycle_index: int, baseline: dict) -> dict:
        row = self.session.exec(
            select(TelemetrySample).where(TelemetrySample.machine_id == machine_id)
            .where(TelemetrySample.consumed == False)  # noqa: E712
            .order_by(TelemetrySample.seq)  # type: ignore[arg-type]
        ).first()
        if row is None:
            raise NoTelemetryAvailable(machine_id)
        row.consumed = True
        self.session.add(row)
        self.session.flush()
        self._last = row
        return {
            "vibration": row.vibration, "temperature": row.temperature, "cycle_time": row.cycle_time,
            "scrap_pct": row.scrap_pct, "fault_code": row.fault_code, **(row.extra or {}),
        }

    def provenance(self) -> tuple[str, int]:
        if self._last is None:
            return ("ingested", 0)
        label = self._last.source or "ingested"
        if self._last.received_at is None:
            return (label, 0)
        return (label, max(int((utcnow() - self._last.received_at).total_seconds()), 0))


class NoTelemetryAvailable(RuntimeError):
    pass


def resolve_source(session: Session, port, machine_id: str) -> TelemetrySource:
    """Prefer ingested real telemetry when present for the machine; otherwise synthetic."""
    ingested = IngestedTelemetrySource(session)
    if ingested.has_data(machine_id):
        return ingested
    return SyntheticTelemetrySource(getattr(port, "physics", None))

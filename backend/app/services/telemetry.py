"""Telemetry source abstraction — the real-data seam.

The cycle engine consumes one sample per cycle from a ``TelemetrySource``. In synthetic mode that is
``ScenarioPhysics``; when real readings have been ingested for a machine (via ``POST /api/telemetry``,
or a future Efficast Edge stream), ``IngestedTelemetrySource`` serves them and the *same* deterministic
evaluator verifies recovery on real data. Nothing else in the system changes.
"""

from __future__ import annotations

import abc

from sqlmodel import Session, select

from app.adapters.synthetic import ScenarioPhysics
from app.domain.models import TelemetrySample


class TelemetrySource(abc.ABC):
    @abc.abstractmethod
    def next_sample(self, *, machine_id: str, window_seq: int, cycle_index: int, baseline: dict) -> dict:
        """Return one cycle's reading: vibration/temperature/cycle_time/scrap_pct/fault_code (+extras)."""
        ...


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
        return {
            "vibration": row.vibration, "temperature": row.temperature, "cycle_time": row.cycle_time,
            "scrap_pct": row.scrap_pct, "fault_code": row.fault_code, **(row.extra or {}),
        }


class NoTelemetryAvailable(RuntimeError):
    pass


def resolve_source(session: Session, port, machine_id: str) -> TelemetrySource:
    """Prefer ingested real telemetry when present for the machine; otherwise synthetic."""
    ingested = IngestedTelemetrySource(session)
    if ingested.has_data(machine_id):
        return ingested
    return SyntheticTelemetrySource(getattr(port, "physics", None))

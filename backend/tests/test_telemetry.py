"""Real-data telemetry seam tests (Phase 10).

Proves the same deterministic evaluator runs on real ingested readings, not just the synthetic plant:
ingested samples are consumed FIFO by the verification window and become the recorded observations.
"""

from __future__ import annotations

from sqlmodel import select

from app.adapters.synthetic import SyntheticEfficastPort
from app.domain.base import utcnow
from app.domain.models import RecoveryObservation, TelemetrySample
from app.seed.northstar import IDS
from app.services.telemetry import (
    IngestedTelemetrySource,
    SyntheticTelemetrySource,
    resolve_source,
)
from app.services.windows import get_active_window
from tests.helpers import to_monitoring


def _ingest(session, machine_id, readings):
    for i, r in enumerate(readings, start=1):
        session.add(TelemetrySample(tenant_id=IDS["tenant"], machine_id=machine_id, seq=i,
                                    received_at=utcnow(), **r))
    session.flush()


def test_resolve_source_prefers_ingested_when_present(session):
    port = SyntheticEfficastPort(session)
    assert isinstance(resolve_source(session, port, IDS["machine"]), SyntheticTelemetrySource)
    _ingest(session, IDS["machine"], [{"vibration": 3.5, "cycle_time": 12.3, "scrap_pct": 1.5}])
    assert isinstance(resolve_source(session, port, IDS["machine"]), IngestedTelemetrySource)


def test_ingested_telemetry_drives_the_verification_window(session):
    svc, inc, c1 = to_monitoring(session)
    readings = [
        {"vibration": 3.50, "temperature": 70.0, "cycle_time": 12.30, "scrap_pct": 1.5, "fault_code": None},
        {"vibration": 3.48, "temperature": 69.0, "cycle_time": 12.29, "scrap_pct": 1.5, "fault_code": None},
        {"vibration": 3.46, "temperature": 68.0, "cycle_time": 12.28, "scrap_pct": 1.4, "fault_code": None},
    ]
    _ingest(session, inc.machine_id, readings)

    result = svc.advance(inc, 3)
    assert result["outcome"] == "monitoring"

    window = get_active_window(session, c1)
    obs = session.exec(
        select(RecoveryObservation).where(RecoveryObservation.window_id == window.id)
        .order_by(RecoveryObservation.cycle_index)  # type: ignore[arg-type]
    ).all()
    assert len(obs) == 3
    # The recorded observations are the REAL ingested values, not synthetic ScenarioPhysics output.
    assert [round(o.vibration, 2) for o in obs] == [3.50, 3.48, 3.46]
    assert obs[0].temperature == 70.0 and obs[2].scrap_pct == 1.4

    # All ingested samples were consumed exactly once.
    remaining = session.exec(
        select(TelemetrySample).where(TelemetrySample.machine_id == inc.machine_id)
        .where(TelemetrySample.consumed == False)  # noqa: E712
    ).all()
    assert remaining == []

"""The last mile: an uploaded mission's telemetry, replayed through the *deterministic evaluator*.

The sample export has F27 recurring at cycle 17. The evaluator — not the reconstruction heuristic — must
independently reject closure and reopen the mission. This is the product's thesis proven on uploaded data
by the authoritative layer.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.api.intake_routes import _sample_csv
from app.domain.enums import WorkflowState
from app.domain.models import Incident, RecoveryContract, TelemetrySample
from app.services.intake_mission import create_mission_from_upload
from app.services.uploaded_verification import run_uploaded_verification


def _mission(session: Session) -> Incident:
    out = create_mission_from_upload(session, "northstar.csv", _sample_csv())
    return session.get(Incident, out["incident_id"])


def test_uploaded_telemetry_is_rejected_by_the_evaluator(session: Session):
    inc = _mission(session)
    res = run_uploaded_verification(session, inc)

    assert res["ran"] is True
    assert res["verdict_by"] == "deterministic-evaluator"
    assert res["outcome"] == "reopened"            # the engine rejected closure
    assert res["relapse_cycle"] == 17              # F27 recurred exactly where the upload shows it
    assert res["telemetry_rows"] == 30
    # the mission landed at the honest next human gate — not auto-closed
    assert inc.state == WorkflowState.CONTINGENCY_AWAITING_APPROVAL


def test_verification_creates_a_real_contract_testing_the_fault(session: Session):
    inc = _mission(session)
    run_uploaded_verification(session, inc)
    contract = session.get(RecoveryContract, inc.current_contract_id)
    assert contract is not None  # persist_contract refuses a contract that can't detect the F27 relapse


def test_leftover_uploaded_samples_are_reclaimed(session: Session):
    inc = _mission(session)
    run_uploaded_verification(session, inc)
    leftover = session.exec(
        select(TelemetrySample).where(TelemetrySample.machine_id == inc.machine_id)
        .where(TelemetrySample.consumed == False)  # noqa: E712
    ).all()
    mine = [s for s in leftover if (s.extra or {}).get("upload_incident_id") == inc.id]
    assert mine == []  # nothing of this mission's lingers on the shared machine


def test_verification_is_idempotent_once_a_contract_exists(session: Session):
    inc = _mission(session)
    run_uploaded_verification(session, inc)
    again = run_uploaded_verification(session, inc)
    assert again["ran"] is False
    assert "already" in again["reason"].lower()


def test_unsupported_fault_blocks_honestly(session: Session):
    csv = ("machine_code,event_time,vibration_rms,temp_c,cycle_no,fault\n"
           "L4-CONV,2026-01-01T08:01:00,3.0,60,1,E99\n")
    out = create_mission_from_upload(session, "other.csv", csv)
    inc = session.get(Incident, out["incident_id"])
    res = run_uploaded_verification(session, inc)
    assert res["ran"] is False
    assert "machine profile" in res["reason"].lower()

"""A1 — the deterministic evaluator is genuinely machine-agnostic.

Before this, `is_stable_observation` + the scalar map hardcoded the four conveyor metric keys, so a
press/pump contract's conditions resolved to None→BLOCKED and never gated the streak: the profile
catalog could be *built* but not *verified*. These tests drive an **injection press** (IMX-90, fault
E12, signals `melt_temperature`/`injection_pressure` carried in obs.raw) through the SAME evaluator and
cycle engine — proving it verifies a press recovery, breaks the streak on an out-of-spec press signal,
and catches a press relapse. No conveyor literals involved.
"""

from __future__ import annotations

import pytest
from sqlmodel import Session, select

from app.config import get_settings
from app.domain.base import utcnow
from app.domain.enums import (
    ApprovalStatus,
    ConditionKind,
    ConditionStatus,
    EvidenceStatus,
    InterventionStatus,
    Role,
    Severity,
    WorkflowState,
)
from app.domain.models import (
    ApprovalDecision,
    ApprovalRequirement,
    EvidenceItem,
    EvidenceRequirement,
    Incident,
    Intervention,
    Machine,
    RecoveryCondition,
    RecoveryObservation,
    TelemetrySample,
)
from app.services import cycle_engine
from app.services.evaluator import evaluate, signal_value
from app.services.machine_profiles import INJECTION_PRESS, build_contract_from_profile
from app.services.windows import open_window
from app.workflow.contract_builder import persist_contract

_S = get_settings()
MACHINE_ID = "MCH-PRESS-1"


def _press_setup(session: Session):
    """A press incident + an active contract built from the INJECTION_PRESS profile, window open."""
    # Tiered flushes: these models use string FKs without ORM relationships, so insert order is not
    # auto-derived (mirrors the seed's pattern) — the parent must exist before the child.
    session.add(Machine(id=MACHINE_ID, tenant_id=_S.tenant_id, plant_id=_S.plant_id, code="IMX-90-01",
                        name="Injection Press 1", machine_model="IMX-90", baseline=INJECTION_PRESS.baseline))
    session.flush()
    inc = Incident(tenant_id=_S.tenant_id, plant_id=_S.plant_id, machine_id=MACHINE_ID,
                   correlation_id="COR-PRESS", dedupe_key="press-1", title="Press E12 recovery",
                   severity=Severity.S2, state=WorkflowState.MONITORING_RECOVERY, fault_code="E12")
    session.add(inc)
    session.flush()
    itv = Intervention(tenant_id=_S.tenant_id, plant_id=_S.plant_id, machine_id=MACHINE_ID,
                       incident_id=inc.id, sequence=1, kind="barrel_heater_replacement",
                       title="Barrel heater band replacement", status=InterventionStatus.COMPLETED)
    session.add(itv)
    session.flush()
    spec = build_contract_from_profile(INJECTION_PRESS, incident_id=inc.id, intervention_id=itv.id,
                                       contract_no="RC-PRESS-1")
    contract = persist_contract(session, inc, spec)
    contract.status = "active"
    session.add(contract)
    open_window(session, incident_id=inc.id, contract=contract, sequence=1,
                required_stable_cycles=INJECTION_PRESS.required_stable_cycles, baseline=INJECTION_PRESS.baseline)
    session.flush()
    return inc, contract


def _ingest(session: Session, seq: int, *, melt=230.0, pressure=1150.0, cycle_time=38.0,
            scrap=1.0, fault=None):
    """Queue one press telemetry sample; press-specific signals ride in `extra` → obs.raw."""
    session.add(TelemetrySample(
        tenant_id=_S.tenant_id, machine_id=MACHINE_ID, seq=seq, cycle_time=cycle_time, scrap_pct=scrap,
        fault_code=fault, source="efficast-edge", received_at=utcnow(),
        extra={"melt_temperature": melt, "injection_pressure": pressure},
    ))
    session.flush()


def _advance(session: Session, contract, n: int):
    for _ in range(n):
        cycle_engine.advance_cycle(session, None, contract)


def _release_quality(session: Session, inc, contract):
    req = session.exec(select(EvidenceRequirement).where(EvidenceRequirement.contract_id == contract.id)
                       .where(EvidenceRequirement.key == "first_piece_quality")).first()
    session.add(EvidenceItem(
        tenant_id=_S.tenant_id, plant_id=_S.plant_id, requirement_id=req.id, contract_id=contract.id,
        incident_id=inc.id, kind=req.kind, submitted_by="q.idris", submitted_role=Role.QUALITY_ENGINEER,
        value_text="pass", source_kind="human", evidence_timestamp=utcnow(), received_at=utcnow(),
        freshness_s=0, valid=True, status=EvidenceStatus.VALIDATED,
    ))
    appr = session.exec(select(ApprovalRequirement).where(ApprovalRequirement.contract_id == contract.id)
                        .where(ApprovalRequirement.key == "quality_release")).first()
    appr.status = ApprovalStatus.APPROVED
    session.add(appr)
    session.add(ApprovalDecision(
        tenant_id=_S.tenant_id, requirement_id=appr.id, contract_id=contract.id, incident_id=inc.id,
        decided_by="q.idris", decided_role=Role.QUALITY_ENGINEER, decision="approve",
        idempotency_key=f"appr-{appr.id}",
    ))
    session.flush()


# ── pure unit: key resolution from columns and obs.raw ────────────────────────
def test_signal_value_resolves_columns_and_raw():
    obs = RecoveryObservation(tenant_id="t", incident_id="i", contract_id="c", window_id="w",
                              cycle_index=1, at=utcnow(), cycle_time=38.0, scrap_pct=1.0,
                              raw={"melt_temperature": 230.0, "injection_pressure": 1150.0})
    assert signal_value(obs, "cycle_time") == 38.0
    assert signal_value(obs, "scrap") == 1.0           # key→column mapping
    assert signal_value(obs, "melt_temperature") == 230.0   # from obs.raw
    assert signal_value(obs, "injection_pressure") == 1150.0
    assert signal_value(obs, "not_a_signal") is None


# ── the headline proof: a second machine verifies through the same evaluator ───
def test_press_recovery_verifies_through_the_same_evaluator(session: Session):
    inc, contract = _press_setup(session)
    n = INJECTION_PRESS.required_stable_cycles
    for seq in range(1, n + 1):
        _ingest(session, seq)
    _advance(session, contract, n)

    result = evaluate(session, contract)
    assert result.stable_streak == n, "press signals must count toward the stable streak"
    by_key = {c["key"]: c["status"] for c in result.conditions}
    # The press-specific machine conditions (resolved from obs.raw) are genuinely PASSED.
    assert by_key["melt_temperature"] == ConditionStatus.PASSED.value
    assert by_key["injection_pressure"] == ConditionStatus.PASSED.value
    # All telemetry conditions pass; only the human quality gate remains (first-piece evidence absent).
    assert result.verdict == "monitoring"
    assert by_key["first_piece"] == ConditionStatus.BLOCKED.value

    _release_quality(session, inc, contract)
    assert evaluate(session, contract).verdict == "verified"


def test_press_out_of_spec_signal_breaks_the_streak(session: Session):
    inc, contract = _press_setup(session)
    for seq in range(1, 6):
        _ingest(session, seq)
    _advance(session, contract, 5)
    assert evaluate(session, contract).stable_streak == 5
    # An over-pressure cycle (1300 > 1200 bar LTE) must reset the streak — proof the press signal gates.
    _ingest(session, 6, pressure=1300.0)
    _advance(session, contract, 1)
    assert evaluate(session, contract).stable_streak == 0


def test_press_relapse_is_caught(session: Session):
    inc, contract = _press_setup(session)
    for seq in range(1, 5):
        _ingest(session, seq)
    _advance(session, contract, 4)
    _ingest(session, 5, fault="E12")          # the originating fault recurs
    _advance(session, contract, 1)
    result = evaluate(session, contract)
    assert result.verdict == "violated"
    assert "fault_e12" in result.violated_keys

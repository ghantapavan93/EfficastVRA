"""Safety / gateway / idempotency / audit tests (covers required tests 2,3,4,11,13,15,16,17,18,20)."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.adapters.synthetic import SyntheticEfficastPort
from app.auth import Principal
from app.domain.enums import ActionClass, AuditEventType, KnowledgeStatus, Role, WorkflowState
from app.domain.models import (
    ActionProposal,
    AuditEvent,
    Incident,
    KnowledgeCandidate,
    ToolExecution,
)
from app.gateway import execute as gateway_execute
from app.gateway.actions import PROHIBITED_ACTIONS
from app.gateway.gateway import GatewayError
from app.reasoning.base import ReasoningProvider
from app.seed.northstar import IDS
from app.tools import REGISTRY
from app.workflow.demo import run_scenario
from helpers import principal, to_monitoring, to_window2_stable


# ── Test 2: duplicate incident event creates one incident ─────────────────────
def test_duplicate_incident_dedupe(session: Session):
    inc = session.get(Incident, IDS["incident"])
    dup = Incident(tenant_id=inc.tenant_id, plant_id=inc.plant_id, machine_id=inc.machine_id,
                   correlation_id="dup", dedupe_key=inc.dedupe_key, title="dup")
    session.add(dup)
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


# ── Test 3: duplicate action request is idempotent ────────────────────────────
def test_duplicate_action_idempotent(session: Session):
    svc, inc, c1 = to_monitoring(session)  # draft already requested evidence with idem key
    port = SyntheticEfficastPort(session)
    agent = principal(session, "s.vega")
    out = gateway_execute(session, tool_name="request_missing_evidence",
                          raw_args={"contract_id": c1.id}, principal=agent,
                          correlation_id=inc.correlation_id, incident_id=inc.id,
                          idempotency_key=f"req-evi-{c1.id}", port=port)
    assert out.source == "idempotent-replay"  # second use of the key replays, no new effect


# ── H1: an unexpected tool error resolves the proposal to "failed", never stuck "proposed" ────
def test_unexpected_tool_error_marks_proposal_failed(session: Session, monkeypatch):
    svc, inc, c1 = to_monitoring(session)
    sup = principal(session, "s.vega")
    spec = REGISTRY["request_missing_evidence"]

    def boom(_ctx):
        raise ValueError("kaboom")

    monkeypatch.setattr(spec, "handler", boom)
    with pytest.raises(GatewayError) as ei:
        gateway_execute(session, tool_name="request_missing_evidence", raw_args={"contract_id": c1.id},
                        principal=sup, correlation_id=inc.correlation_id, incident_id=inc.id,
                        port=SyntheticEfficastPort(session), idempotency_key="boom-1")
    assert ei.value.status_code == 500 and ei.value.stage == "execute"
    props = session.exec(select(ActionProposal).where(ActionProposal.idempotency_key == "boom-1")).all()
    assert props and all(p.status == "failed" for p in props)  # resolved, not stuck "proposed"


# ── N1: an approval decision must be explicit (never silently coerced to REJECT) ──────────────
def test_approval_decision_must_be_explicit():
    import pydantic

    from app.tools.schemas import RecordApprovalInput

    RecordApprovalInput(requirement_id="r", decision="approve")  # valid
    RecordApprovalInput(requirement_id="r", decision="reject")   # valid
    for bad in ("approved", "Approve", "yes", "ok", ""):
        with pytest.raises(pydantic.ValidationError):
            RecordApprovalInput(requirement_id="r", decision=bad)  # loud, not a silent rejection


# ── Test 4 + 11: role authorization on approvals ──────────────────────────────
def test_unauthorized_role_cannot_approve(session: Session):
    svc, inc, c1 = to_monitoring(session)
    from helpers import appr_id

    review = appr_id(session, c1.id, "contract_review")  # requires supervisor
    tech = principal(session, "a.lang")
    with pytest.raises(GatewayError):
        gateway_execute(session, tool_name="record_human_approval",
                        raw_args={"requirement_id": review, "decision": "approve"}, principal=tech,
                        correlation_id=inc.correlation_id, incident_id=inc.id,
                        port=SyntheticEfficastPort(session))


def test_quality_release_requires_quality_engineer(session: Session):
    svc, inc, c2 = to_window2_stable(session, cycles=30)
    from helpers import appr_id

    qr = appr_id(session, c2.id, "quality_release")
    sup = principal(session, "s.vega")  # supervisor must NOT be able to release quality
    with pytest.raises(GatewayError):
        gateway_execute(session, tool_name="record_human_approval",
                        raw_args={"requirement_id": qr, "decision": "approve"}, principal=sup,
                        correlation_id=inc.correlation_id, incident_id=inc.id,
                        port=SyntheticEfficastPort(session))
    # 30 stable cycles but no quality release => not verified, still monitoring.
    result = svc.current_evaluation(inc)
    assert result.verdict != "verified"
    assert inc.state == WorkflowState.MONITORING_RECOVERY


# ── Test 13: model failure preserves workflow state ───────────────────────────
class _BoomReasoning(ReasoningProvider):
    id = "BoomReasoning"

    def extract_recovery_requirements(self, **_):
        raise RuntimeError("model unavailable")

    def identify_missing_evidence(self, **_):
        return []

    def compare_historical_interventions(self, **_):
        return {}

    def detect_document_conflicts(self, **_):
        return {}

    def explain_recovery_failure(self, **_):
        return {}

    def generate_handoff_summary(self, **_):
        return {}


def test_model_failure_preserves_state(session: Session):
    from app.workflow.recovery_service import RecoveryService

    inc = session.get(Incident, IDS["incident"])
    svc = RecoveryService(session, reasoning=_BoomReasoning())
    with pytest.raises(RuntimeError):
        svc.draft_contract(inc)
    session.rollback()
    inc = session.get(Incident, IDS["incident"])
    assert inc.state == WorkflowState.INTERVENTION_RECORDED  # unchanged
    assert inc.current_contract_id is None


# ── Allowlist invariant: every runnable tool is in a known-safe class (not a name denylist) ───
def test_every_registered_tool_is_in_a_safe_action_class():
    """Inverts the safety check from a denylist to an allowlist: a newly-added dangerous tool fails this
    even if its name isn't on any blocklist. Every tool the gateway can run must be in a safe class, and
    every *write* tool must be reversible-automatic or human-approval-gated (never misclassified read-only)."""
    safe = {ActionClass.READ_ONLY, ActionClass.REVERSIBLE_AUTOMATIC, ActionClass.APPROVAL_REQUIRED}
    write_safe = {ActionClass.REVERSIBLE_AUTOMATIC, ActionClass.APPROVAL_REQUIRED}
    for name, spec in REGISTRY.items():
        assert spec.action_class in safe, f"{name}: unsafe action_class {spec.action_class}"
        assert spec.action_class != ActionClass.PROHIBITED
        if spec.is_write:
            assert spec.action_class in write_safe, f"{name}: write tool must be gated, got {spec.action_class}"


# ── Test 15: no machine-control tool / route / action exists ──────────────────
def test_no_machine_control_exists(session: Session):
    # No registered tool is a prohibited action.
    assert not (set(REGISTRY) & PROHIBITED_ACTIONS)
    # The gateway denies any prohibited action name outright.
    sup = principal(session, "s.vega")
    inc = session.get(Incident, IDS["incident"])
    for name in ["machine_start", "machine_stop", "plc_modification", "automatic_quality_release"]:
        with pytest.raises(GatewayError) as ei:
            gateway_execute(session, tool_name=name, raw_args={}, principal=sup,
                            correlation_id=inc.correlation_id, incident_id=inc.id)
        assert ei.value.stage == "risk_class"
    # No HTTP route exposes machine control.
    from app.main import app

    banned = ("machine/start", "machine/stop", "machine/restart", "/plc", "setpoint",
              "interlock", "lockout", "/loto", "quality/auto")
    for route in app.routes:
        path = getattr(route, "path", "").lower()
        assert not any(b in path for b in banned)


# ── Test 18: cross-plant evidence cannot be retrieved ─────────────────────────
def test_cross_plant_denied(session: Session):
    inc = session.get(Incident, IDS["incident"])
    other = Principal(user_id="x", username="x.other", role=Role.SUPERVISOR,
                      plant_id="PLANT-OTHER", tenant_id="northstar")
    with pytest.raises(GatewayError) as ei:
        gateway_execute(session, tool_name="get_machine_recovery_metrics",
                        raw_args={"machine_id": IDS["machine"]}, principal=other,
                        correlation_id="x", incident_id=None, port=SyntheticEfficastPort(session))
    assert ei.value.stage == "plant_scope"


# ── Tests 16 + 17 + 20: audit completeness after the full scenario ────────────
def test_audit_completeness_and_knowledge_pending(session: Session):
    run_scenario(session, log=lambda *_a: None)
    inc = session.get(Incident, IDS["incident"])
    assert inc.state == WorkflowState.VERIFIED_RECOVERY

    audits = session.exec(select(AuditEvent).where(AuditEvent.incident_id == inc.id)).all()
    transitions = [a for a in audits if a.type == AuditEventType.STATE_TRANSITION]
    assert len(transitions) >= 10
    assert all(a.prev_state and a.new_state for a in transitions)  # every transition fully recorded

    # INVARIANT (not mere existence): after a clean run no write proposal is stuck in "proposed" — every
    # one resolved to executed/failed — and every executed write has a matching tool-execution row (so it
    # provably went *through* the gateway rather than around it).
    proposals = session.exec(select(ActionProposal)).all()
    execs = session.exec(select(ToolExecution)).all()
    assert proposals and execs
    assert all(p.action_class is not None for p in proposals)
    write_proposals = [p for p in proposals if p.action_class != ActionClass.READ_ONLY]
    assert write_proposals, "the scenario performs writes"
    unresolved = [(p.tool_name, p.status) for p in write_proposals if p.status not in ("executed", "failed")]
    assert not unresolved, f"write proposals left unresolved: {unresolved}"
    exec_proposal_ids = {e.proposal_id for e in execs}
    assert all(p.id in exec_proposal_ids for p in write_proposals if p.status == "executed")
    assert any(a.type == AuditEventType.TOOL_EXECUTED for a in audits)

    kc = session.exec(select(KnowledgeCandidate).where(KnowledgeCandidate.incident_id == inc.id)).first()
    assert kc is not None and kc.status == KnowledgeStatus.PENDING_REVIEW

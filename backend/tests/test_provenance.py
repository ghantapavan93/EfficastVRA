"""Provenance & evidence-trust tests (Phase 26).

Evidence-quality tiering, the closure-provenance record (which also exercises the proposed-vs-executed
reconciliation), and the H8 audit-sequence uniqueness constraint. All read-only / advisory.
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.domain.enums import EvidenceKind, EvidenceStatus, Role, WorkflowState
from app.domain.models import AuditEvent, EvidenceItem, EvidenceRequirement, Incident
from app.seed.northstar import IDS
from app.services.evidence_quality import classify, summarize
from app.services.provenance import closure_provenance
from app.workflow.audit import verify_audit_chain
from app.workflow.demo import run_scenario


def _item(**kw) -> EvidenceItem:
    base = dict(kind=EvidenceKind.NUMERIC_MEASUREMENT, valid=True)
    base.update(kw)
    return EvidenceItem(**base)


def test_evidence_quality_ranks_by_provenance_then_discounts():
    # A direct instrument reading outranks a measured human reading > observation > document.
    sensor = classify(_item(source_kind="sensor", value_num=3.1))
    human_num = classify(_item(source_kind="human", value_num=3.6, unit="mm/s"))
    human_obs = classify(_item(source_kind="human", value_text="completed", kind=EvidenceKind.COMPLETION))
    doc = classify(_item(source_kind="document", value_text="proc rev C"))
    assert sensor["tier"] == "direct_sensor" and sensor["trust"] == 1.0
    assert human_num["tier"] == "instrumented_measurement" and human_num["trust"] == 0.85
    assert human_obs["tier"] == "human_observation" and human_obs["trust"] == 0.6
    assert doc["tier"] == "document_reference" and doc["trust"] == 0.5
    assert sensor["rank"] > human_num["rank"] > human_obs["rank"] > doc["rank"]

    # Pending (submitted, awaiting validation) is DISCOUNTED, not zeroed — a healthy in-progress incident
    # must not read as untrustworthy. Rejected/conflicting collapse to zero.
    pending = classify(_item(source_kind="sensor", value_num=3.1, valid=False))  # default status SUBMITTED
    assert pending["trust"] == 0.5 and "pending" in pending["flags"]
    rejected = classify(_item(source_kind="sensor", value_num=3.1, valid=False, status=EvidenceStatus.REJECTED))
    assert rejected["trust"] == 0.0
    conflict = classify(_item(source_kind="sensor", value_num=3.1, conflict_reason="contradicts QC"))
    assert conflict["trust"] == 0.0 and "conflict" in conflict["flags"]

    req = EvidenceRequirement(kind=EvidenceKind.NUMERIC_MEASUREMENT, key="k",
                              assigned_role=Role.TECHNICIAN, freshness_max_s=60)
    stale = classify(_item(source_kind="sensor", value_num=3.1, freshness_s=600), req)
    assert "stale" in stale["flags"] and stale["trust"] == 0.5  # 1.0 halved


def test_summarize_surfaces_the_weakest_link():
    s = summarize([
        classify(_item(source_kind="sensor", value_num=1.0)),
        classify(_item(source_kind="human", value_text="ok", kind=EvidenceKind.COMPLETION)),
    ])
    assert s["count"] == 2 and s["min_trust"] == 0.6 and s["weakest"]["trust"] == 0.6


def test_closure_provenance_after_verified_run(session: Session):
    run_scenario(session, log=lambda *_a: None)
    inc = session.get(Incident, IDS["incident"])
    assert inc.state == WorkflowState.VERIFIED_RECOVERY

    prov = closure_provenance(session, inc)
    assert prov["available"] and prov["closed"] is True
    assert prov["conditions"] and any(c["status"] in ("PASSED", "PASSING") for c in prov["conditions"])
    assert prov["evidence_summary"]["count"] > 0 and prov["evidence_summary"]["mean_trust"] > 0
    assert prov["approvals"], "a verified closure has human approvals (incl. quality release)"
    assert len(prov["interventions"]) >= 2  # alignment (failed) + bearing replacement
    # Reconciliation: every proposed action reconciles to an execution; nothing orphaned (validates H1/H7).
    assert prov["reconciliation"]["ok"] is True
    assert prov["reconciliation"]["unreconciled"] == [] and prov["reconciliation"]["orphan_executions"] == []
    # Audit chain intact, and the overall record is trustworthy.
    assert prov["audit"]["ok"] is True and prov["trustworthy"] is True
    assert "VERIFIED" in prov["summary"]


def test_closure_provenance_unavailable_before_contract(session: Session):
    inc = session.get(Incident, IDS["incident"])  # raw seed: no contract yet
    assert closure_provenance(session, inc)["available"] is False


# ── H8: the per-correlation audit sequence is unique at the DB layer ──────────
def test_audit_sequence_is_unique_per_correlation(session: Session):
    run_scenario(session, log=lambda *_a: None)
    existing = session.exec(select(AuditEvent)).first()
    assert existing is not None
    dup = AuditEvent(
        tenant_id=existing.tenant_id, plant_id=existing.plant_id,
        correlation_id=existing.correlation_id, seq=existing.seq,  # collides on (correlation_id, seq)
        type=existing.type, actor="x", summary="dup",
    )
    session.add(dup)
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_audit_chain_detects_deletion(session: Session):
    run_scenario(session, log=lambda *_a: None)
    cid = session.get(Incident, IDS["incident"]).correlation_id
    assert verify_audit_chain(session, cid)["ok"] is True

    events = session.exec(
        select(AuditEvent).where(AuditEvent.correlation_id == cid).order_by(AuditEvent.seq)  # type: ignore[arg-type]
    ).all()
    assert len(events) > 3
    session.delete(events[len(events) // 2])  # remove a middle entry
    session.flush()
    broken = verify_audit_chain(session, cid)
    assert broken["ok"] is False and broken["broken_at_seq"] is not None


def test_audit_chain_detects_reorder(session: Session):
    run_scenario(session, log=lambda *_a: None)
    cid = session.get(Incident, IDS["incident"]).correlation_id
    events = session.exec(
        select(AuditEvent).where(AuditEvent.correlation_id == cid).order_by(AuditEvent.seq)  # type: ignore[arg-type]
    ).all()
    # Move a middle entry to the end (a reorder) → ordering + prev_hash linkage no longer recompute.
    mid = events[len(events) // 2]
    mid.seq = events[-1].seq + 100
    session.add(mid)
    session.flush()
    assert verify_audit_chain(session, cid)["ok"] is False

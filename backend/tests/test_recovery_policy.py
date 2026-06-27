"""The comparable-conditions recovery CEILING (rule ccr-1.0) as a system-wide invariant.

Proves: NOT_COMPARABLE/UNKNOWN can never be VERIFIED (even at raw 0.99); PARTIALLY reduces + exposes
confounders; COMPARABLE preserves normal; a relapse (FAILED) and missing hard gates (quality/freshness)
are never overridden by a confidence or comparability score; and no surface (signature, disposition,
certificate, finalize/knowledge-candidate) represents VERIFIED when the effective policy is INSUFFICIENT.
"""

from __future__ import annotations

from sqlmodel import select

from app.domain.enums import WorkflowState
from app.domain.models import Incident, KnowledgeCandidate, RecoveryWindow
from app.seed.northstar import IDS
from app.services.certificate import build_certificate
from app.services.disposition import assess_disposition
from app.services.recovery_policy import (
    ELIGIBLE,
    FAILED,
    INSUFFICIENT,
    RULE_VERSION,
    derive_effective_recovery_confidence,
)
from app.services.recovery_signature import score_signature
from app.workflow.demo import run_scenario
from tests.helpers import to_quality_released, to_window2_stable


def _diverge(session, contract_id: str) -> RecoveryWindow:
    """Make the latest window's verification context not comparable to normal (changed product/speed/load)."""
    win = session.exec(
        select(RecoveryWindow).where(RecoveryWindow.contract_id == contract_id)
        .order_by(RecoveryWindow.sequence.desc())
    ).first()
    win.observed_context = {**win.observed_context, "product": "PKG-XL-20", "speed_pct": 47.5, "load": "high"}
    session.add(win)
    session.commit()
    return win


# ── 1–4 + dominance: the canonical policy function (pure) ─────────────────────────────────────────────
def test_raw_099_plus_not_comparable_is_insufficient():
    r = derive_effective_recovery_confidence(0.99, "NOT_COMPARABLE", 0.2, ELIGIBLE)
    assert r.policy_result == "INSUFFICIENT_EVIDENCE" and r.policy_result != "VERIFIED"
    assert r.causal_language_allowed is False and r.rule_version == RULE_VERSION


def test_raw_099_plus_unknown_is_insufficient():
    r = derive_effective_recovery_confidence(0.99, "UNKNOWN", 0.5, ELIGIBLE)  # default-deny
    assert r.policy_result == "INSUFFICIENT_EVIDENCE"


def test_partially_comparable_reduces_and_exposes_confounders():
    r = derive_effective_recovery_confidence(0.90, "PARTIALLY_COMPARABLE", 0.6, ELIGIBLE,
                                             confounders=["Ambient temperature"])
    assert r.policy_result == "VERIFIED" and r.confidence_tier == "REDUCED"
    assert r.effective_confidence < 0.90
    assert "Ambient temperature" in r.confounding_dimensions
    assert r.capped_rung == "consistent_with_intervention"  # strong causal claim withheld


def test_comparable_preserves_normal_evaluation():
    r = derive_effective_recovery_confidence(0.90, "COMPARABLE", 1.0, ELIGIBLE)
    assert r.policy_result == "VERIFIED" and r.confidence_tier == "NORMAL"
    assert r.effective_confidence == 0.90 and r.capped_rung == "strongly_consistent"


def test_failed_relapse_dominates_even_when_not_comparable():
    r = derive_effective_recovery_confidence(0.99, "NOT_COMPARABLE", 0.2, FAILED)
    assert r.policy_result == "FAILED"  # comparability must not hide a directly observed relapse


def test_hard_gate_insufficient_not_rescued_by_good_comparability():
    r = derive_effective_recovery_confidence(0.99, "COMPARABLE", 1.0, INSUFFICIENT)
    assert r.policy_result == "INSUFFICIENT_EVIDENCE"  # a missing/stale hard gate is never overridden


# ── 5: relapse stays FAILED end-to-end ────────────────────────────────────────────────────────────────
def test_cycle17_relapse_remains_failed(session):
    from tests.helpers import to_monitoring
    svc, inc, _c1 = to_monitoring(session)
    svc.advance(inc, 16)
    r = svc.advance(inc, 1)  # cycle 17: F27 recurs
    # the relapse forces a reopen — never a (false) closure — regardless of comparability (the policy-level
    # FAILED-dominates invariant is covered by test_failed_relapse_dominates_even_when_not_comparable)
    assert r["outcome"] == "reopened"
    assert inc.reopened_count >= 1
    assert inc.state == WorkflowState.CONTINGENCY_AWAITING_APPROVAL


# ── 6 + 7: hard gates block verification (comparability cannot rescue them) ────────────────────────────
def test_missing_quality_approval_still_blocks_verification(session):
    _svc, inc, _c2 = to_window2_stable(session, cycles=30)  # 30 stable, COMPARABLE, but NO quality release
    d = assess_disposition(session, inc)
    assert d["disposition"] == "INSUFFICIENT_EVIDENCE" and d["can_close"] is False
    assert d["comparability"]["classification"] == "COMPARABLE"  # good comparability does not rescue it


def test_stale_or_missing_evidence_hard_gate_dominates():
    # the freshness/evidence MECHANISM is covered by test_freshness_at_closure; here we assert the policy
    # never lets comparability rescue an unmet hard gate (time-of-use staleness ⇒ evidence_status INSUFFICIENT).
    assert derive_effective_recovery_confidence(0.99, "COMPARABLE", 1.0, INSUFFICIENT).policy_result == "INSUFFICIENT_EVIDENCE"


# ── 8: no surface shows VERIFIED when the effective policy is INSUFFICIENT ─────────────────────────────
def test_disposition_never_verified_when_not_comparable(session):
    svc, inc, c2 = to_quality_released(session, cycles=30)            # verified-ELIGIBLE under COMPARABLE
    base = assess_disposition(session, inc)
    assert base["disposition"] == "VERIFIED" and base["can_close"] is True
    _diverge(session, c2.id)
    after = assess_disposition(session, inc)
    assert after["disposition"] == "INSUFFICIENT_EVIDENCE" and after["can_close"] is False
    assert after["verdict"] == "verified"  # the evaluator's hard gate still passed — the ceiling withholds VERIFIED
    assert after["policy_provenance"]["rule_version"] == RULE_VERSION


def test_certificate_not_certified_when_not_comparable(session):
    run_scenario(session, log=lambda *a: None)                        # closed + COMPARABLE → certified
    inc = session.get(Incident, IDS["incident"])
    assert build_certificate(session, inc)["status"] == "certified"
    _diverge(session, inc.current_contract_id)
    cert = build_certificate(session, inc)
    assert cert["status"] != "certified" and cert["verdict"] != "VERIFIED_RECOVERY"


def test_signature_rung_capped_when_not_comparable(session):
    svc, inc, c2 = to_quality_released(session, cycles=30)
    _diverge(session, c2.id)
    sig = score_signature(session, c2)
    assert sig.conditions_matched == "NOT_COMPARABLE"
    assert sig.rung == "insufficient_evidence"   # capped down from a strong raw rung
    assert sig.confounding_dimensions            # the confounders are exposed


# ── 9: knowledge-candidate creation requires VERIFIED under acceptable comparability ──────────────────
def test_knowledge_candidate_created_when_comparable(session):
    svc, inc, _c2 = to_quality_released(session, cycles=30)
    svc.finalize(inc)
    session.commit()
    assert inc.state == WorkflowState.VERIFIED_RECOVERY
    assert session.exec(select(KnowledgeCandidate).where(KnowledgeCandidate.incident_id == inc.id)).first() is not None


def test_knowledge_candidate_blocked_when_not_comparable(session):
    svc, inc, c2 = to_quality_released(session, cycles=30)
    _diverge(session, c2.id)
    svc.finalize(inc)  # comparable-conditions ceiling blocks closure
    session.commit()
    assert inc.state == WorkflowState.INSUFFICIENT_EVIDENCE
    assert session.exec(select(KnowledgeCandidate).where(KnowledgeCandidate.incident_id == inc.id)).first() is None

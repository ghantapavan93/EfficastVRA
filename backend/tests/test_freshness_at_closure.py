"""C2 — evidence freshness is re-checked at *closure*, not only at submission.

The submission-time gate (``test_stale_evidence_is_invalid``) rejects evidence that is already stale
when it arrives. This covers the complementary time-of-check/time-of-use gap: evidence that was fresh
when submitted but has since aged past its freshness budget must not silently close a contract.
"""

from __future__ import annotations

from datetime import timedelta

from sqlmodel import Session, select

from app.domain.base import utcnow
from app.domain.enums import ConditionStatus
from app.domain.models import EvidenceRequirement
from app.services.evaluator import evaluate
from app.services.evidence import is_fresh_at, requirement_satisfied
from tests.helpers import appr_id, principal, req_id, to_window2_stable


def _quality_requirement(session: Session, contract_id: str) -> EvidenceRequirement:
    return session.exec(
        select(EvidenceRequirement)
        .where(EvidenceRequirement.contract_id == contract_id)
        .where(EvidenceRequirement.key == "first_piece_quality")
    ).first()


def _release_quality(session: Session, svc, inc, contract_id: str) -> None:
    """Submit a fresh, valid first-piece result + the quality-engineer release approval."""
    qual = principal(session, "q.idris")
    svc.submit_evidence(inc, qual, requirement_id=req_id(session, contract_id, "first_piece_quality"),
                        value_text="pass")
    svc.record_approval(inc, qual, requirement_id=appr_id(session, contract_id, "quality_release"),
                        reason="first-piece passed; lots dispositioned")


def test_is_fresh_at_uses_the_budget_at_time_of_use(session: Session):
    """The freshness budget is re-applied against the moment of use, not the submission instant."""
    from app.services.evidence import latest_valid_item

    svc, inc, c2 = to_window2_stable(session, cycles=30)
    _release_quality(session, svc, inc, c2.id)
    req = _quality_requirement(session, c2.id)
    it = latest_valid_item(session, req.id)
    assert it is not None and req.freshness_max_s
    base = it.evidence_timestamp or it.received_at
    assert is_fresh_at(it, req, base + timedelta(seconds=req.freshness_max_s - 1)) is True
    assert is_fresh_at(it, req, base + timedelta(seconds=req.freshness_max_s + 1)) is False


def test_quality_evidence_must_be_fresh_at_closure(session: Session):
    svc, inc, c2 = to_window2_stable(session, cycles=30)
    _release_quality(session, svc, inc, c2.id)
    req = _quality_requirement(session, c2.id)
    assert req is not None and req.freshness_max_s

    now = utcnow()
    # Fresh now → the contract verifies.
    assert evaluate(session, c2, as_of=now).verdict == "verified"
    assert requirement_satisfied(session, req, as_of=now) is True

    # The *same* evidence, used to close after its freshness budget has elapsed, no longer counts.
    stale = now + timedelta(seconds=req.freshness_max_s + 60)
    assert requirement_satisfied(session, req, as_of=stale) is False
    result = evaluate(session, c2, as_of=stale)
    assert result.verdict != "verified"
    first_piece = next(c for c in result.conditions if c["key"] == "first_piece")
    assert first_piece["status"] == ConditionStatus.BLOCKED.value


def test_freshness_recheck_is_opt_in(session: Session):
    """Backward compatibility: with no ``as_of`` the once-validated item still satisfies (the monitoring
    and reasoning paths that don't re-check are unchanged)."""
    svc, inc, c2 = to_window2_stable(session, cycles=30)
    _release_quality(session, svc, inc, c2.id)
    req = _quality_requirement(session, c2.id)
    assert requirement_satisfied(session, req) is True

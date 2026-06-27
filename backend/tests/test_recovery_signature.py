"""Phase 36a — the Expected Recovery Signature (advisory intervention-consistency).

Proves the headline of the Causal Recovery Assurance direction: the SAME headline metrics in the two
hero windows produce OPPOSITE signature verdicts — the alignment (coupling) window is only
RECOVERY_OBSERVED (fault recurs + precursor rises), while the bearing window is STRONGLY_CONSISTENT
(capped conditions-unverified). The signature is derived from the contract's own conditions (machine-
agnostic), and the scorer is read-only/advisory. See docs/CAUSAL_RECOVERY_RESEARCH.md.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.domain.models import RecoveryCondition, RecoveryContract
from app.services.recovery_signature import (
    CONSISTENT_WITH_INTERVENTION,
    INSUFFICIENT_EVIDENCE,
    PRECURSOR_KEY,
    RECOVERY_OBSERVED,
    STRONGLY_CONSISTENT,
    expected_signature,
    score_signature,
)
from tests.helpers import to_reopened, to_window2_stable


def _conditions(session: Session, contract_id: str):
    return session.exec(
        select(RecoveryCondition).where(RecoveryCondition.contract_id == contract_id)
    ).all()


def test_signature_is_derived_from_contract_conditions(session: Session):
    _svc, inc, c2 = to_window2_stable(session, cycles=2)
    sig = expected_signature(_conditions(session, c2.id))
    keys = {s["signal"] for s in sig}
    # one entry per non-quality, non-stable-cycle condition + the derived precursor
    assert "vibration_rms" in keys and "cycle_time" in keys and PRECURSOR_KEY in keys
    assert "first_piece" not in keys and "stable_cycles" not in keys
    # the fault-absence signal carries the incident's OWN fault, not a hardcoded "F27"
    fault_sig = next(s for s in sig if s["direction"] == "absent")
    assert fault_sig["fault_code"] == inc.fault_code
    # directions are derived from the operators
    assert next(s for s in sig if s["signal"] == "vibration_rms")["direction"] == "down"


def test_bearing_window_is_strongly_consistent(session: Session):
    _svc, _inc, c2 = to_window2_stable(session, cycles=30)
    res = score_signature(session, c2)
    assert res.rung == STRONGLY_CONSISTENT
    assert res.alignment > 0.9
    # the top rung must always disclose the unverified-conditions confound
    assert res.conditions_matched == "UNKNOWN"
    assert any("conditions-unverified" in c for c in res.caveats)


def test_alignment_window_is_not_consistent(session: Session):
    # advance to the cycle-17 F27 relapse → reopen; V1's window failed and carries the relapse + rising precursor
    _svc, inc = to_reopened(session)
    v1 = session.exec(
        select(RecoveryContract)
        .where(RecoveryContract.incident_id == inc.id)
        .where(RecoveryContract.version == 1)
    ).first()
    res = score_signature(session, v1)
    assert res.rung != STRONGLY_CONSISTENT
    assert res.rung in (RECOVERY_OBSERVED, CONSISTENT_WITH_INTERVENTION, INSUFFICIENT_EVIDENCE)
    assert res.alignment < 0.6
    # the discriminating signals flag the false recovery
    assert any("fault recurred" in c for c in res.caveats)


def test_two_hero_windows_score_oppositely(session: Session):
    # the whole point: identical headline metrics, opposite signature verdicts.
    # to_window2_stable runs the full hero arc (relapse@17 → reopen → contingency → 30 stable cycles),
    # leaving V1 (coupling, failed) and c2 (bearing, recovered) both queryable.
    _svc, inc, c2 = to_window2_stable(session, cycles=30)
    v1 = session.exec(
        select(RecoveryContract).where(RecoveryContract.incident_id == inc.id)
        .where(RecoveryContract.version == 1)
    ).first()
    a1 = score_signature(session, v1).alignment
    a2 = score_signature(session, c2).alignment
    assert a1 < a2, f"alignment window ({a1}) should score below bearing window ({a2})"


def test_scoring_is_read_only(session: Session):
    _svc, inc, c2 = to_window2_stable(session, cycles=5)
    before = inc.state
    score_signature(session, c2)
    assert inc.state == before  # advisory layer must not mutate incident state


def test_signature_view_serializes_for_the_api(session: Session):
    from app.api.serializers import signature_view

    _svc, inc, _c2 = to_window2_stable(session, cycles=30)
    view = signature_view(session, inc)
    assert view["available"] is True
    assert view["rung"] == STRONGLY_CONSISTENT
    assert isinstance(view["signals"], list) and view["signals"]
    assert view["conditions_matched"] == "UNKNOWN"

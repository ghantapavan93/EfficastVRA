"""OEE-Restoration Verification — recomputes Availability × Performance × Quality over the verification
window vs the machine baseline. Advisory/read-only; the deterministic evaluator still owns closure.
"""

from __future__ import annotations

from sqlmodel import Session

from app.domain.models import Incident
from app.seed.northstar import IDS
from app.services.oee_restoration import assess_oee_restoration
from tests.helpers import to_window2_stable


def test_oee_restoration_available_after_monitoring(session: Session):
    _svc, inc, _c2 = to_window2_stable(session, cycles=30)
    out = assess_oee_restoration(session, inc)

    assert out["available"] is True
    assert out["recovered_oee"]["oee"] is not None
    assert 0.0 <= out["recovered_oee"]["oee"] <= 1.0
    assert out["baseline_oee"]["oee"] is not None
    # OEE is decomposed into exactly the three Efficast factors.
    assert {f["key"] for f in out["factors"]} == {"availability", "performance", "quality"}
    assert all(f["recovered"] is not None for f in out["factors"])
    assert len(out["trajectory"]) > 0
    assert isinstance(out["restored"], bool)
    assert out["headline"]


def test_oee_restoration_reads_only(session: Session):
    _svc, inc, _c2 = to_window2_stable(session, cycles=30)
    before = inc.state
    assess_oee_restoration(session, inc)
    assert inc.state == before  # a verification lens never changes state


def test_oee_restoration_unavailable_without_cycles(session: Session):
    inc = session.get(Incident, IDS["incident"])  # fresh incident, no verification window yet
    out = assess_oee_restoration(session, inc)
    assert out["available"] is False

"""Phase 35a honesty fixes (see docs/ARCHITECTURE_AUDIT.md):

- B1 — an absent credential is supervisor ONLY in demo mode; otherwise 401 (no anonymous elevation).
- B3 — telemetry provenance is the sample's real source + age, not a hardcoded ("Synthetic…", 2).
- A3 — timeline/outcome fault labels derive from the incident's fault, not the literal "F27".
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app.api.serializers import outcome_view, timeline_view
from app.auth import get_principal
from app.config import get_settings
from app.domain.base import utcnow
from app.domain.models import Incident, TelemetrySample
from app.seed.northstar import IDS
from app.services.telemetry import IngestedTelemetrySource, resolve_source
from tests.helpers import to_window2_stable


# ── B1: anonymous ≠ supervisor outside demo mode ──────────────────────────────
def test_absent_credential_is_unauthenticated_outside_demo_mode(session: Session, monkeypatch):
    monkeypatch.setenv("VRA_DEMO_MODE", "0")
    assert get_settings().demo_mode is False
    with pytest.raises(HTTPException) as e:
        get_principal(x_vra_user=None, session=session)
    assert e.value.status_code == 401
    # An explicit identity still authenticates (role still comes from the User row).
    assert get_principal(x_vra_user="a.lang", session=session).username == "a.lang"


def test_absent_credential_defaults_to_supervisor_in_demo_mode(session: Session, monkeypatch):
    monkeypatch.setenv("VRA_DEMO_MODE", "1")
    assert get_principal(x_vra_user=None, session=session).username == "s.vega"


# ── B3: honest telemetry provenance ───────────────────────────────────────────
def test_ingested_telemetry_provenance_is_real_source_and_age(session: Session):
    inc = session.get(Incident, IDS["incident"])
    session.add(TelemetrySample(
        tenant_id=inc.tenant_id, machine_id=inc.machine_id, seq=1,
        vibration=3.1, temperature=63.0, cycle_time=12.2, scrap_pct=1.5,
        source="efficast-edge", received_at=utcnow() - timedelta(seconds=120),
    ))
    session.flush()
    src = resolve_source(session, None, inc.machine_id)
    assert isinstance(src, IngestedTelemetrySource)
    src.next_sample(machine_id=inc.machine_id, window_seq=1, cycle_index=1, baseline={})
    label, freshness = src.provenance()
    assert label == "efficast-edge"     # not "SyntheticEfficastPort"
    assert freshness >= 115             # ~120 s, the real age — not the hardcoded 2


def test_synthetic_telemetry_provenance_is_labelled_synthetic(session: Session):
    inc = session.get(Incident, IDS["incident"])
    src = resolve_source(session, None, inc.machine_id)  # no ingested data → synthetic
    assert src.provenance() == ("SyntheticEfficastPort", 2)


# ── A3: machine-agnostic fault labels ─────────────────────────────────────────
def test_timeline_recurrence_flag_tracks_the_incident_fault(session: Session):
    _svc, inc, _c2 = to_window2_stable(session, cycles=3)
    tl = timeline_view(session, inc)
    recur = [c for c in tl["cycles"] if c["is_recurrence"]]
    assert recur, "the window-1 relapse cycle should be flagged a recurrence"
    assert all(c["fault_code"] == inc.fault_code for c in recur)

    # Proof it reads incident.fault_code (not the literal "F27"): retarget the incident's fault and the
    # same observations (still carrying F27) no longer count as a recurrence.
    inc.fault_code = "ZZ-OTHER"
    session.add(inc)
    session.flush()
    assert all(not c["is_recurrence"] for c in timeline_view(session, inc)["cycles"])


def test_outcome_before_after_labels_use_the_incident_fault(session: Session):
    _svc, inc, _c2 = to_window2_stable(session, cycles=3)
    ov = outcome_view(session, inc)
    assert inc.fault_code and inc.fault_code in ov["before"]["fault"]
    assert inc.fault_code in ov["after"]["fault"]

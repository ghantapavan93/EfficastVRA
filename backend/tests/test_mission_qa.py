"""Conversational role-adaptive Mission Q&A — advisory, grounded, never deciding."""

from __future__ import annotations

from sqlmodel import Session

from app.api.intake_routes import _sample_csv
from app.domain.models import Incident
from app.services.intake_mission import create_mission_from_upload
from app.services.mission_qa import answer
from app.services.uploaded_verification import run_uploaded_verification


def _mission(session: Session) -> Incident:
    out = create_mission_from_upload(session, "northstar.csv", _sample_csv())
    return session.get(Incident, out["incident_id"])


def test_meta_question_is_honest_about_authority(session: Session):
    inc = _mission(session)
    res = answer(session, inc, "are you an AI that decides closure?", "supervisor")
    assert res["intent"] == "meta"
    assert "do not decide" in res["answer"].lower()
    assert res["grounded_in"] == "deterministic-evaluator"


def test_close_question_before_contract_is_grounded(session: Session):
    inc = _mission(session)
    res = answer(session, inc, "can we close it now?", "supervisor")
    assert res["intent"] == "close"
    assert "contract" in res["answer"].lower()
    assert res["citations"]  # every answer cites a deterministic surface


def test_relapse_question_after_reopen(session: Session):
    inc = _mission(session)
    run_uploaded_verification(session, inc)
    res = answer(session, inc, "did the fault come back?", "technician")
    assert res["intent"] == "relapse"
    assert "reopen" in res["answer"].lower()
    assert res["role"] == "technician"           # role-adaptive
    assert any(c["surface"] == "Recovery Twin" for c in res["citations"])


def test_blocking_question_returns_the_blocker(session: Session):
    inc = _mission(session)
    run_uploaded_verification(session, inc)
    res = answer(session, inc, "what's blocking this?", "supervisor")
    assert res["intent"] == "blocking"
    assert res["answer"] and res["suggestions"]

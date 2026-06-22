"""Demo controller — only mounted when VRA_DEMO_MODE=1. Drives the *real* backend (reset/seed and a
full auto replay). Individual demo steps in the UI call the real action endpoints in routes.py.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.config import get_settings
from app.db import drop_all, engine, get_session, init_db
from app.domain.models import ApprovalRequirement, EvidenceRequirement, Incident
from app.rag.corpus import seed_documents
from app.seed import IDS, seed_all
from app.workflow.demo import run_scenario

router = APIRouter(prefix="/api/demo", tags=["demo"])
_settings = get_settings()


def _guard() -> None:
    if not _settings.demo_mode:
        raise HTTPException(403, "demo mode disabled")


@router.post("/reset")
def reset() -> dict:
    _guard()
    drop_all()
    init_db()
    with Session(engine) as s:
        seed_all(s)
        n = seed_documents(s)
    return {"ok": True, "ids": IDS, "document_chunks": n}


@router.post("/run")
def run() -> dict:
    _guard()
    with Session(engine) as s:
        summary = run_scenario(s, log=lambda *_a: None)
    return {"ok": True, **summary}


@router.get("/ids")
def ids(session: Session = Depends(get_session)) -> dict:
    """Resolve the live evidence/approval requirement IDs for the active contract so the demo
    controller can target real endpoints."""
    inc = session.get(Incident, IDS["incident"])
    out = {"ids": IDS, "incident_state": inc.state.value if inc else None,
           "contract_id": inc.current_contract_id if inc else None,
           "evidence": {}, "approvals": {}}
    if inc and inc.current_contract_id:
        for r in session.exec(select(EvidenceRequirement)
                              .where(EvidenceRequirement.contract_id == inc.current_contract_id)).all():
            out["evidence"][r.key] = {"id": r.id, "status": r.status.value,
                                      "role": r.assigned_role.value}
        for a in session.exec(select(ApprovalRequirement)
                              .where(ApprovalRequirement.contract_id == inc.current_contract_id)).all():
            out["approvals"][a.key] = {"id": a.id, "status": a.status.value,
                                       "role": a.required_role.value}
    return out

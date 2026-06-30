"""Recovery Mission Intake API — Bring-Your-Own-Plant-Data.

Stateless, read-only analysis of an uploaded plant export: detect schema, propose a contract mapping,
report data readiness, and reconstruct the incident. Nothing is written and no machine is touched here;
this is the front of the mission funnel. Confirmed mappings + a started mission come next.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.db import get_session
from app.domain.models import Incident
from app.services.intake import analyze_upload

router = APIRouter(prefix="/api/intake", tags=["intake"])


class AnalyzeBody(BaseModel):
    filename: str = "upload.csv"
    content: str = Field(..., description="Raw file text — CSV, JSON array, or JSONL.")
    profile_id: Optional[str] = Field(default=None, description="Reuse a saved Mapping Profile instead of proposing.")


@router.get("/profiles")
def profiles(session: Session = Depends(get_session)) -> dict:
    """Saved Plant Data Mapping Profiles — pick one to reuse a confirmed mapping on a similar export."""
    from app.services.intake_mission import list_profiles

    return list_profiles(session)


def _saved(session: Session, profile_id: Optional[str]) -> Optional[list[dict]]:
    if not profile_id:
        return None
    from app.services.intake_mission import get_profile_mappings

    saved = get_profile_mappings(session, profile_id)
    if saved is None:
        raise HTTPException(404, "mapping profile not found")
    return saved


@router.post("/analyze")
def analyze(body: AnalyzeBody, session: Session = Depends(get_session)) -> dict:
    """Analyze an uploaded plant export → mapping + Data Readiness Report + incident reconstruction.
    The AI/heuristic proposes (or a saved profile is reused); the user confirms before a mission is created."""
    return analyze_upload(body.filename, body.content, saved_profile=_saved(session, body.profile_id))


@router.post("/create-mission")
def create_mission(body: AnalyzeBody, session: Session = Depends(get_session)) -> dict:
    """Turn an uploaded export into a live, persisted Recovery Mission: map → reconstruct → persist a
    Mapping Profile → create a real Incident (with the intake analysis attached) → stamp a provenance audit.
    The new mission then flows through the spine + deterministic surfaces (it has no contract/verdict yet)."""
    from app.services.intake_mission import create_mission_from_upload

    out = create_mission_from_upload(session, body.filename, body.content,
                                     saved_profile=_saved(session, body.profile_id))
    if out.get("created"):
        session.commit()
    return out


@router.post("/missions/{incident_id}/run-verification")
def run_verification(incident_id: str, session: Session = Depends(get_session)) -> dict:
    """The last mile: replay an uploaded mission's telemetry through the deterministic evaluator.

    Ingests the uploaded readings, drafts a Recovery Contract via the real orchestrator, satisfies the
    monitoring prerequisites from the uploaded data, and replays the cycles — the *deterministic evaluator*
    renders the verdict (for the messy sample it rejects closure: F27 recurs at cycle 17 → reopened). It
    never fabricates a quality release the upload lacks, and stops at the next human gate."""
    from app.services.uploaded_verification import run_uploaded_verification

    incident = session.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="mission not found")
    out = run_uploaded_verification(session, incident)
    if out.get("ran"):
        session.commit()
    return out


# A deliberately *messy* Northstar export: non-canonical column names, a fault recurrence at cycle 17, and
# NO quality/approval columns — so the demo shows the mapping studio working AND readiness/reconstruction
# honestly blocking verification ("reconstructed, but quality approval is missing").
_SAMPLE = (
    "machine_code,event_time,vibration_rms,temp_c,cycle_no,fault,operator\n"
)
def _sample_csv() -> str:
    rows = [_SAMPLE]
    base_min = 0
    for c in range(1, 31):
        faulted = c == 17
        vib = 7.4 if faulted else round(3.10 + ((c % 5) - 2) * 0.05, 2)
        temp = max(63 - 0.9 * c, 24)
        fault = "F27" if faulted else ""
        # a couple of restart/intervention markers via the fault column kept simple
        ts = f"2026-01-01T08:{base_min + c:02d}:00" if (base_min + c) < 60 else f"2026-01-01T09:{base_min + c - 60:02d}:00"
        rows.append(f"L4-CONV,{ts},{vib},{round(temp,1)},{c},{fault},A.Ortiz\n")
    return "".join(rows)


@router.get("/sample")
def sample() -> dict:
    """A messy Northstar incident export to try the intake flow without your own data."""
    return {"filename": "northstar-line4-export.csv", "content": _sample_csv(),
            "note": "Deliberately messy: non-canonical headers, an F27 recurrence at cycle 17, and no quality/approval columns."}

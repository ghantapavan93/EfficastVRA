"""Recovery Mission Intake API — Bring-Your-Own-Plant-Data.

Stateless, read-only analysis of an uploaded plant export: detect schema, propose a contract mapping,
report data readiness, and reconstruct the incident. Nothing is written and no machine is touched here;
this is the front of the mission funnel. Confirmed mappings + a started mission come next.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.db import get_session
from app.services.intake import analyze_upload

router = APIRouter(prefix="/api/intake", tags=["intake"])


class AnalyzeBody(BaseModel):
    filename: str = "upload.csv"
    content: str = Field(..., description="Raw file text — CSV, JSON array, or JSONL.")


@router.post("/analyze")
def analyze(body: AnalyzeBody) -> dict:
    """Analyze an uploaded plant export → proposed mapping + Data Readiness Report + incident reconstruction.
    The AI/heuristic proposes; the user confirms the mapping before a mission is created."""
    return analyze_upload(body.filename, body.content)


@router.post("/create-mission")
def create_mission(body: AnalyzeBody, session: Session = Depends(get_session)) -> dict:
    """Turn an uploaded export into a live, persisted Recovery Mission: map → reconstruct → persist a
    Mapping Profile → create a real Incident (with the intake analysis attached) → stamp a provenance audit.
    The new mission then flows through the spine + deterministic surfaces (it has no contract/verdict yet)."""
    from app.services.intake_mission import create_mission_from_upload

    out = create_mission_from_upload(session, body.filename, body.content)
    if out.get("created"):
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

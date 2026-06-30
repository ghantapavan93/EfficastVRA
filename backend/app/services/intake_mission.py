"""Intake → a live, persisted Recovery Mission.

Closes the headline loop: an uploaded plant export doesn't just get *analyzed*, it *becomes a mission*. We
map + reconstruct the upload, persist a reusable Mapping Profile, create a real Incident on the plant with
the intake analysis attached (so the mission carries its own origin story), and stamp a provenance audit
event. The mission then flows through the existing spine + deterministic surfaces.

Governed: the model/heuristic proposed the mapping (a human confirms upstream); reconstruction is
deterministic; and a created mission still has NO contract or verdict yet — the deterministic layer owns
those downstream. No machine is touched.
"""

from __future__ import annotations

import hashlib
import uuid

from sqlmodel import Session, select

from app.config import get_settings
from app.domain.base import utcnow
from app.domain.enums import AuditEventType, Role, Severity, WorkflowState
from app.domain.models import Incident, Machine, MappingProfile
from app.services.intake import analyze_upload, build_telemetry_series, parse_content, propose_mapping
from app.workflow.audit import record_audit

_settings = get_settings()


def _first_value(rows: list[dict], col: str | None) -> str | None:
    if not col:
        return None
    for r in rows:
        v = r.get(col)
        if v not in (None, "", "null", "nan", "NaN"):
            return str(v).strip()
    return None


def _first_fault(rows: list[dict], col: str | None) -> str | None:
    if not col:
        return None
    for r in rows:
        v = str(r.get(col, "")).strip()
        if v and v.lower() not in ("none", "ok", "0", "nan", "null", "false"):
            return v
    return None


def create_mission_from_upload(session: Session, filename: str, content: str) -> dict:
    analysis = analyze_upload(filename, content)
    table = parse_content(filename, content)
    mappings = propose_mapping(table)
    idx = {(m.target_event, m.target_field): m.column for m in mappings if m.target_event}

    machine_code = _first_value(table.rows, idx.get(("asset", "source_id")))
    fault = _first_fault(table.rows, idx.get(("machine_event", "event_code")))
    telemetry_series = build_telemetry_series(table, mappings)

    # Resolve the asset: match the uploaded code, else fall back to a seeded machine in the plant.
    machine = (session.exec(select(Machine).where(Machine.code == machine_code)).first()
               if machine_code else None) or session.exec(select(Machine)).first()
    if machine is None:
        return {"created": False, "reason": "No machine is registered to attach the mission to."}

    profile = MappingProfile(
        tenant_id=_settings.tenant_id, plant_id=machine.plant_id,
        name=f"{machine.code} upload mapping", profile_version="1.0", source_filename=filename,
        mappings=[vars(m) for m in mappings],
    )
    session.add(profile)
    session.flush()

    digest = hashlib.sha256((filename + content[:2000]).encode()).hexdigest()[:12]
    incident = Incident(
        tenant_id=_settings.tenant_id, plant_id=machine.plant_id, machine_id=machine.id,
        correlation_id=f"up-{uuid.uuid4().hex[:10]}",
        dedupe_key=f"upload-{digest}-{uuid.uuid4().hex[:6]}",  # unique per upload
        title=f"{machine.name} — {fault or 'uploaded incident'} (from {filename})",
        fault_code=fault, severity=Severity.S2, state=WorkflowState.INTERVENTION_RECORDED,
        opened_at=utcnow(),
        intake={**analysis, "mapping_profile_id": profile.id, "source_filename": filename,
                "detected_machine": machine_code, "detected_fault": fault,
                "telemetry_series": telemetry_series},
    )
    session.add(incident)
    session.flush()

    record_audit(
        session, type=AuditEventType.ALERT_INGESTED, correlation_id=incident.correlation_id,
        actor="intake", role=Role.AGENT, plant_id=machine.plant_id, incident_id=incident.id,
        summary=f"Mission created from uploaded plant data ({filename})",
        detail={"source": "upload", "filename": filename, "rows": analysis["row_count"],
                "mapped_columns": analysis["mapped_count"], "readiness_score": analysis["readiness"]["score"],
                "false_closure_detected": analysis["reconstruction"]["false_closure_detected"],
                "mapping_profile_id": profile.id},
    )
    session.flush()

    return {
        "created": True,
        "incident_id": incident.id,
        "machine": machine.code,
        "fault": fault,
        "readiness_score": analysis["readiness"]["score"],
        "readiness_verdict": analysis["readiness"]["verdict"],
        "false_closure_detected": analysis["reconstruction"]["false_closure_detected"],
        "mapping_profile_id": profile.id,
        "mapped_columns": analysis["mapped_count"],
        "row_count": analysis["row_count"],
        "telemetry_rows": len(telemetry_series),
    }

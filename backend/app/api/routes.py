"""Read views + gateway-mediated actions. All mutations go through the gateway or the orchestrator
(which itself routes side effects through the gateway)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.adapters.synthetic import SyntheticEfficastPort
from app.auth import Principal, get_principal
from app.config import get_settings
from app.db import get_session
from app.domain.models import ApprovalRequirement, EvidenceRequirement, Incident, RecoveryContract
from app.gateway import execute as gateway_execute
from app.api import serializers as S
from app.reasoning import get_reasoning_provider
from app.workflow.recovery_service import RecoveryService

router = APIRouter(prefix="/api", tags=["recovery"])
_settings = get_settings()


def _incident(session: Session, incident_id: str) -> Incident:
    inc = session.get(Incident, incident_id)
    if inc is None:
        raise HTTPException(404, f"incident {incident_id} not found")
    return inc


def _svc(session: Session) -> RecoveryService:
    return RecoveryService(session, port=SyntheticEfficastPort(session), reasoning=get_reasoning_provider())


# ── identity ─────────────────────────────────────────────────────────────────
@router.get("/me")
def me(principal: Principal = Depends(get_principal)) -> dict:
    return {"user_id": principal.user_id, "username": principal.username, "role": principal.role.value,
            "plant_id": principal.plant_id, "tenant_id": principal.tenant_id,
            "environment": _settings.environment, "demo_mode": _settings.demo_mode}


# ── reads ────────────────────────────────────────────────────────────────────
@router.get("/missions")
def missions(session: Session = Depends(get_session)) -> dict:
    incidents = session.exec(select(Incident).where(Incident.historical == False)).all()  # noqa: E712
    rows = [S.mission_summary(session, i) for i in incidents]
    session.commit()
    rows.sort(key=lambda r: (not r["is_active"], r["state"]))
    return {"missions": rows, "environment": _settings.environment}


@router.get("/missions/{incident_id}")
def mission(incident_id: str, session: Session = Depends(get_session)) -> dict:
    inc = _incident(session, incident_id)
    out = S.mission_detail(session, inc)
    session.commit()
    return out


@router.get("/incidents/{incident_id}/contract")
def incident_contract(incident_id: str, session: Session = Depends(get_session)) -> dict:
    inc = _incident(session, incident_id)
    if inc.current_contract_id is None:
        raise HTTPException(404, "no contract yet")
    contract = session.get(RecoveryContract, inc.current_contract_id)
    out = S.contract_view(session, contract)
    session.commit()
    return out


@router.get("/contracts/{contract_id}")
def contract(contract_id: str, session: Session = Depends(get_session)) -> dict:
    c = session.get(RecoveryContract, contract_id)
    if c is None:
        raise HTTPException(404, "contract not found")
    out = S.contract_view(session, c)
    session.commit()
    return out


@router.get("/incidents/{incident_id}/contract-versions")
def contract_versions(incident_id: str, session: Session = Depends(get_session)) -> dict:
    inc = _incident(session, incident_id)
    contracts = session.exec(
        select(RecoveryContract).where(RecoveryContract.incident_id == inc.id).order_by(RecoveryContract.version)  # type: ignore[arg-type]
    ).all()
    out = [S.contract_view(session, c) for c in contracts]
    session.commit()
    return {"versions": out}


@router.get("/incidents/{incident_id}/evidence")
def evidence(incident_id: str, session: Session = Depends(get_session)) -> dict:
    inc = _incident(session, incident_id)
    out = S.evidence_view(session, inc)
    session.commit()
    return out


@router.get("/incidents/{incident_id}/timeline")
def timeline(incident_id: str, session: Session = Depends(get_session)) -> dict:
    inc = _incident(session, incident_id)
    return S.timeline_view(session, inc)


@router.get("/incidents/{incident_id}/outcome")
def outcome(incident_id: str, session: Session = Depends(get_session)) -> dict:
    inc = _incident(session, incident_id)
    out = S.outcome_view(session, inc)
    session.commit()
    return out


@router.get("/incidents/{incident_id}/audit")
def audit(incident_id: str, session: Session = Depends(get_session)) -> dict:
    inc = _incident(session, incident_id)
    return {"events": S.audit_view(session, inc)}


@router.get("/incidents/{incident_id}/reasoning")
def reasoning(incident_id: str, session: Session = Depends(get_session)) -> dict:
    inc = _incident(session, incident_id)
    return S.reasoning_view(session, inc)


# ── front of the loop: MAIA alerts + agent diagnosis ──────────────────────────
@router.get("/alerts")
def alerts(session: Session = Depends(get_session)) -> dict:
    return {"alerts": S.open_alerts_view(session), "environment": _settings.environment}


@router.get("/machine-profiles")
def machine_profiles() -> dict:
    """The machine-agnostic contract catalog (supported equipment classes)."""
    return S.machine_profiles_view()


@router.get("/integration")
def integration(session: Session = Depends(get_session)) -> dict:
    """ISA-95 hierarchy, Unified-Namespace topics, and the connector catalog."""
    return S.integration_view(session)


@router.get("/incidents/{incident_id}/diagnosis")
def diagnosis(incident_id: str, session: Session = Depends(get_session)) -> dict:
    inc = _incident(session, incident_id)
    return S.diagnosis_view(session, inc)


@router.post("/alerts/{alert_id}/triage")
def triage_alert(alert_id: str, session: Session = Depends(get_session),
                 principal: Principal = Depends(get_principal)) -> dict:
    from app.adapters.efficast_port import MaiaAlertDTO
    from app.domain.models import MaiaAlert

    row = session.get(MaiaAlert, alert_id)
    if row is None:
        raise HTTPException(404, f"alert {alert_id} not found")
    dto = MaiaAlertDTO(
        id=row.id, source=row.source, kind=row.kind, machine_id=row.machine_id, order_id=row.order_id,
        fault_code=row.fault_code,
        severity=row.severity.value if hasattr(row.severity, "value") else str(row.severity),
        message=row.message, signals=row.signals or {}, detected_at=row.detected_at, status=row.status,
    )
    inc = _svc(session).triage_from_alert(dto)
    session.commit()
    return {"ok": True, "incident_id": inc.id, "state": inc.state.value,
            "diagnosis": S.diagnosis_view(session, inc)}


@router.post("/incidents/{incident_id}/diagnosis/accept")
def accept_diagnosis(incident_id: str, session: Session = Depends(get_session),
                     principal: Principal = Depends(get_principal)) -> dict:
    inc = _incident(session, incident_id)
    _svc(session).accept_diagnosis(inc, principal)
    session.commit()
    return {"ok": True, "state": inc.state.value}


# ── generic gateway tool call (every action passes the gateway) ───────────────
class ToolCall(BaseModel):
    args: dict = {}
    incident_id: Optional[str] = None
    idempotency_key: Optional[str] = None


@router.post("/tools/{tool_name}")
def call_tool(tool_name: str, body: ToolCall, session: Session = Depends(get_session),
              principal: Principal = Depends(get_principal)) -> dict:
    inc = session.get(Incident, body.incident_id) if body.incident_id else None
    correlation = inc.correlation_id if inc else "adhoc"
    out = gateway_execute(session, tool_name=tool_name, raw_args=body.args, principal=principal,
                          correlation_id=correlation, incident_id=body.incident_id,
                          idempotency_key=body.idempotency_key, port=SyntheticEfficastPort(session),
                          reasoning=get_reasoning_provider())
    session.commit()
    return out.model_dump(mode="json")


# ── orchestrated human/agent actions ─────────────────────────────────────────
class AdvanceBody(BaseModel):
    n: int = 1


class EvidenceBody(BaseModel):
    value_num: Optional[float] = None
    value_text: str = ""
    unit: str = ""
    source: str = ""


class ApprovalBody(BaseModel):
    decision: str = "approve"
    reason: str = ""


class TelemetryReading(BaseModel):
    vibration: Optional[float] = None
    temperature: Optional[float] = None
    cycle_time: Optional[float] = None
    scrap_pct: Optional[float] = None
    fault_code: Optional[str] = None
    extra: dict = {}


class TelemetryBody(BaseModel):
    readings: list[TelemetryReading]


@router.post("/telemetry/{machine_id}")
def ingest_telemetry(machine_id: str, body: TelemetryBody, session: Session = Depends(get_session),
                     principal: Principal = Depends(get_principal)) -> dict:
    """Ingest real telemetry readings for a machine. They are consumed FIFO by the next verification
    window instead of synthetic samples — the same evaluator then verifies recovery on real data.
    This is the seam a real Efficast Edge / historian stream would feed (see docs/REAL_DATA_INTEGRATION.md)."""
    from app.domain.base import utcnow
    from app.domain.models import Machine, TelemetrySample
    from sqlalchemy import func as _func

    machine = session.get(Machine, machine_id)
    if machine is None:
        raise HTTPException(404, f"machine {machine_id} not found")
    start = int(session.exec(
        select(_func.max(TelemetrySample.seq)).where(TelemetrySample.machine_id == machine_id)
    ).one() or 0)
    for i, r in enumerate(body.readings, start=1):
        session.add(TelemetrySample(
            tenant_id=machine.tenant_id, machine_id=machine_id, seq=start + i,
            vibration=r.vibration, temperature=r.temperature, cycle_time=r.cycle_time,
            scrap_pct=r.scrap_pct, fault_code=r.fault_code, extra=r.extra, source="ingested",
            received_at=utcnow(),
        ))
    session.commit()
    return {"ok": True, "machine_id": machine_id, "ingested": len(body.readings),
            "next_seq": start + len(body.readings)}


@router.post("/incidents/{incident_id}/contract/draft")
def draft(incident_id: str, session: Session = Depends(get_session),
          principal: Principal = Depends(get_principal)) -> dict:
    inc = _incident(session, incident_id)
    c = _svc(session).draft_contract(inc)
    session.commit()
    return {"ok": True, "contract_id": c.id, "state": inc.state.value}


@router.post("/incidents/{incident_id}/contract/review")
def review(incident_id: str, session: Session = Depends(get_session),
           principal: Principal = Depends(get_principal)) -> dict:
    inc = _incident(session, incident_id)
    _svc(session).review_contract(inc, principal)
    session.commit()
    return {"ok": True, "state": inc.state.value}


@router.post("/evidence/{requirement_id}/submit")
def submit_evidence(requirement_id: str, body: EvidenceBody, session: Session = Depends(get_session),
                    principal: Principal = Depends(get_principal)) -> dict:
    req = session.get(EvidenceRequirement, requirement_id)
    if req is None:
        raise HTTPException(404, "evidence requirement not found")
    inc = _incident(session, req.incident_id)
    out = _svc(session).submit_evidence(inc, principal, requirement_id=requirement_id,
                                        value_num=body.value_num, value_text=body.value_text,
                                        unit=body.unit, source=body.source)
    session.commit()
    return out.model_dump(mode="json")


@router.post("/approvals/{requirement_id}/decide")
def decide(requirement_id: str, body: ApprovalBody, session: Session = Depends(get_session),
           principal: Principal = Depends(get_principal)) -> dict:
    req = session.get(ApprovalRequirement, requirement_id)
    if req is None:
        raise HTTPException(404, "approval requirement not found")
    inc = _incident(session, req.incident_id)
    out = _svc(session).record_approval(inc, principal, requirement_id=requirement_id,
                                        decision=body.decision, reason=body.reason)
    session.commit()
    return out.model_dump(mode="json")


@router.post("/incidents/{incident_id}/monitoring/start")
def start_monitoring(incident_id: str, session: Session = Depends(get_session),
                     principal: Principal = Depends(get_principal)) -> dict:
    inc = _incident(session, incident_id)
    _svc(session).start_monitoring(inc)
    session.commit()
    return {"ok": True, "state": inc.state.value}


@router.post("/incidents/{incident_id}/advance")
def advance(incident_id: str, body: AdvanceBody, session: Session = Depends(get_session),
            principal: Principal = Depends(get_principal)) -> dict:
    inc = _incident(session, incident_id)
    out = _svc(session).advance(inc, body.n)
    session.commit()
    return out


@router.post("/incidents/{incident_id}/contingency/approve")
def approve_contingency(incident_id: str, session: Session = Depends(get_session),
                        principal: Principal = Depends(get_principal)) -> dict:
    inc = _incident(session, incident_id)
    _svc(session).approve_contingency(inc, principal)
    session.commit()
    return {"ok": True, "state": inc.state.value}


@router.post("/incidents/{incident_id}/contingency/complete")
def complete_contingency(incident_id: str, session: Session = Depends(get_session),
                         principal: Principal = Depends(get_principal)) -> dict:
    inc = _incident(session, incident_id)
    _svc(session).complete_contingency(inc)
    session.commit()
    return {"ok": True, "state": inc.state.value}

"""The Agent Action Gateway pipeline.

    reasoning output → schema → identity → plant scope → role → risk class → policy →
    human-approval → idempotency → circuit-breaker → audit → execute → result validation → transition

Every operational side effect flows through :func:`execute`. Denials and executions are audited. A tool
failure marks its proposal ``failed`` and records a ``TOOL_EXECUTED`` (error) audit row — the failed
attempt is kept as evidence, by design. It never advances workflow state: ``execute`` itself never calls
``transition`` (the orchestrator transitions only *after* a successful ``execute`` returns), so a raised
failure means no state change happens.
"""

from __future__ import annotations

from typing import Optional

from pydantic import ValidationError
from sqlmodel import Session

from app.auth import Principal
from app.config import get_settings
from app.domain.base import utcnow
from app.domain.enums import ActionClass, AuditEventType, ToolStatus
from app.domain.models import (
    ActionProposal,
    ApprovalRequirement,
    EvidenceRequirement,
    Incident,
    Machine,
    ProductionOrder,
    RecoveryContract,
    ToolExecution,
)
from app.gateway import circuit, idempotency
from app.gateway.actions import PROHIBITED_ACTIONS, ToolContext, ToolError
from app.tools import REGISTRY
from app.tools.schemas import ToolOutput
from app.workflow.audit import record_audit

_settings = get_settings()


class GatewayError(Exception):
    def __init__(self, message: str, *, status_code: int = 400, code: str = "error", stage: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.stage = stage


def _resolve_target_plant(session: Session, inp, incident_id: Optional[str]) -> Optional[str]:
    if incident_id:
        inc = session.get(Incident, incident_id)
        if inc:
            return inc.plant_id
    for attr, model, plant_attr in [
        ("machine_id", Machine, "plant_id"),
        ("order_id", ProductionOrder, "plant_id"),
        ("contract_id", RecoveryContract, "plant_id"),
    ]:
        val = getattr(inp, attr, None)
        if val:
            row = session.get(model, val)
            if row:
                return getattr(row, plant_attr)
    for attr, model in [("requirement_id", EvidenceRequirement), ("requirement_id", ApprovalRequirement)]:
        val = getattr(inp, attr, None)
        if val:
            row = session.get(model, val)
            if row:
                inc = session.get(Incident, row.incident_id)
                return inc.plant_id if inc else None
    return None


def _deny(session: Session, *, correlation_id: str, principal: Principal, tool_name: str,
          incident_id: Optional[str], stage: str, reason: str, status_code: int = 403) -> None:
    record_audit(session, type=AuditEventType.ACTION_DENIED, correlation_id=correlation_id,
                 actor=principal.username if principal else "unknown",
                 role=principal.role if principal else None, summary=f"DENIED [{stage}] {tool_name}: {reason}",
                 incident_id=incident_id, detail={"tool": tool_name, "stage": stage, "reason": reason})
    session.flush()
    raise GatewayError(reason, status_code=status_code, code="denied", stage=stage)


def execute(
    session: Session,
    *,
    tool_name: str,
    raw_args: dict,
    principal: Principal,
    correlation_id: str,
    incident_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    port=None,
    reasoning=None,
) -> ToolOutput:
    # ── risk class: hard-prohibited names never run, even if no such tool exists ──
    if tool_name in PROHIBITED_ACTIONS:
        _deny(session, correlation_id=correlation_id, principal=principal, tool_name=tool_name,
              incident_id=incident_id, stage="risk_class",
              reason="prohibited action class (physical/safety control is never permitted)")

    spec = REGISTRY.get(tool_name)
    if spec is None:
        raise GatewayError(f"unknown tool '{tool_name}'", status_code=404, code="unknown_tool")
    if spec.action_class == ActionClass.PROHIBITED:
        _deny(session, correlation_id=correlation_id, principal=principal, tool_name=tool_name,
              incident_id=incident_id, stage="risk_class", reason="tool is PROHIBITED")

    # ── 1. schema validation ──────────────────────────────────────────────────
    try:
        inp = spec.input_model.model_validate(raw_args)
    except ValidationError as e:
        raise GatewayError(f"invalid arguments: {e.errors()}", status_code=422, code="schema",
                           stage="schema") from e

    proposal = ActionProposal(
        tenant_id=_settings.tenant_id, plant_id=principal.plant_id if principal else _settings.plant_id,
        incident_id=incident_id, correlation_id=correlation_id,
        proposed_by=principal.username if principal else "unknown", tool_name=tool_name,
        action_class=spec.action_class, args=raw_args, idempotency_key=idempotency_key or "",
        status="proposed", risk_reason=spec.summary,
    )
    session.add(proposal)
    session.flush()
    record_audit(session, type=AuditEventType.ACTION_PROPOSED, correlation_id=correlation_id,
                 actor=proposal.proposed_by, role=principal.role if principal else None,
                 summary=f"Proposed {tool_name} [{spec.action_class.value}]", incident_id=incident_id,
                 detail={"tool": tool_name, "class": spec.action_class.value})

    # ── 2. identity ───────────────────────────────────────────────────────────
    if principal is None:
        _deny(session, correlation_id=correlation_id, principal=principal, tool_name=tool_name,
              incident_id=incident_id, stage="identity", reason="no authenticated principal",
              status_code=401)

    # ── 3. plant scope ────────────────────────────────────────────────────────
    target_plant = _resolve_target_plant(session, inp, incident_id)
    if target_plant and target_plant != principal.plant_id:
        _deny(session, correlation_id=correlation_id, principal=principal, tool_name=tool_name,
              incident_id=incident_id, stage="plant_scope",
              reason=f"principal plant {principal.plant_id} may not act on {target_plant}")

    # ── 4. role authorization ─────────────────────────────────────────────────
    if principal.role not in spec.allowed_roles:
        _deny(session, correlation_id=correlation_id, principal=principal, tool_name=tool_name,
              incident_id=incident_id, stage="role",
              reason=f"role {principal.role.value} not permitted for {tool_name}")

    # ── 5. risk classification (record) ───────────────────────────────────────
    record_audit(session, type=AuditEventType.ACTION_CLASSIFIED, correlation_id=correlation_id,
                 actor=proposal.proposed_by, role=principal.role,
                 summary=f"Classified {tool_name} as {spec.action_class.value}", incident_id=incident_id)

    # ── 6. policy validation ──────────────────────────────────────────────────
    ctx = ToolContext(session=session, port=port, reasoning=reasoning, principal=principal,
                      correlation_id=correlation_id, incident_id=incident_id, input=inp,
                      idempotency_key=idempotency_key)
    if spec.policy is not None:
        ok, reason = spec.policy(ctx)
        if not ok:
            _deny(session, correlation_id=correlation_id, principal=principal, tool_name=tool_name,
                  incident_id=incident_id, stage="policy", reason=reason, status_code=409)

    # ── 7. human-approval validation ──────────────────────────────────────────
    if (spec.requires_human or spec.action_class == ActionClass.APPROVAL_REQUIRED) and not principal.is_human:
        _deny(session, correlation_id=correlation_id, principal=principal, tool_name=tool_name,
              incident_id=incident_id, stage="human_approval",
              reason="this action requires a human principal")

    # ── 8. idempotency (writes) ───────────────────────────────────────────────
    if spec.is_write and idempotency_key:
        prior = idempotency.lookup(session, idempotency_key)
        if prior is not None:
            return ToolOutput(ok=True, data=prior.detail, source="idempotent-replay", ref=prior.result_ref)

    # ── 9. circuit breaker ────────────────────────────────────────────────────
    allowed, cb_reason = circuit.allow(session, tool_name)
    if not allowed:
        _deny(session, correlation_id=correlation_id, principal=principal, tool_name=tool_name,
              incident_id=incident_id, stage="circuit_breaker", reason=cb_reason, status_code=503)

    # ── 10/11. execute ────────────────────────────────────────────────────────
    texec = ToolExecution(
        tenant_id=_settings.tenant_id, proposal_id=proposal.id, incident_id=incident_id,
        correlation_id=correlation_id, tool_name=tool_name, actor=principal.username,
        role=principal.role, input_data=raw_args, started_at=utcnow(),
    )
    try:
        with session.begin_nested():  # savepoint: a handler's partial writes roll back atomically on failure
            out: ToolOutput = spec.handler(ctx)
    except ToolError as e:
        circuit.on_failure(session, tool_name)
        texec.status = ToolStatus.ERROR
        texec.error_type = e.code
        texec.finished_at = utcnow()
        session.add(texec)
        proposal.status = "failed"
        session.add(proposal)
        record_audit(session, type=AuditEventType.TOOL_EXECUTED, correlation_id=correlation_id,
                     actor=principal.username, role=principal.role,
                     summary=f"{tool_name} failed: {e}", incident_id=incident_id,
                     detail={"error": str(e), "code": e.code})
        session.flush()
        raise GatewayError(str(e), status_code=409 if e.code in ("role_mismatch", "role_denied") else 400,
                           code=e.code, stage="execute") from e
    except Exception as e:  # unexpected — record the failed attempt, resolve the proposal, do not transition
        circuit.on_failure(session, tool_name)
        texec.status = ToolStatus.ERROR
        texec.error_type = type(e).__name__
        texec.finished_at = utcnow()
        session.add(texec)
        proposal.status = "failed"      # never leave a write proposal stuck in "proposed"
        session.add(proposal)
        record_audit(session, type=AuditEventType.TOOL_EXECUTED, correlation_id=correlation_id,
                     actor=principal.username, role=principal.role,
                     summary=f"{tool_name} errored: {type(e).__name__}", incident_id=incident_id,
                     detail={"error": str(e), "code": "internal"})
        session.flush()
        raise GatewayError(f"tool execution error: {e}", status_code=500, code="internal",
                           stage="execute") from e

    # ── 12. result validation ─────────────────────────────────────────────────
    out = spec.output_model.model_validate(out.model_dump())
    circuit.on_success(session, tool_name)

    # ── 13. persist execution + idempotency ───────────────────────────────────
    texec.status = ToolStatus.SUCCESS if out.ok else ToolStatus.ERROR
    texec.output_data = out.model_dump(mode="json")
    texec.data_source = out.source
    texec.data_timestamp = out.data_timestamp
    texec.freshness_s = out.freshness_s
    texec.idempotency_key = idempotency_key
    texec.finished_at = utcnow()
    texec.duration_ms = int((texec.finished_at - texec.started_at).total_seconds() * 1000)
    session.add(texec)

    if spec.is_write and idempotency_key:
        idempotency.remember(session, idempotency_key, scope=tool_name,
                             result_ref=out.ref or "", detail=out.data)

    proposal.status = "executed"
    session.add(proposal)
    record_audit(session, type=AuditEventType.TOOL_EXECUTED, correlation_id=correlation_id,
                 actor=principal.username, role=principal.role,
                 summary=f"Executed {tool_name} ({texec.status.value})", incident_id=incident_id,
                 detail={"tool": tool_name, "ref": out.ref, "source": out.source})
    session.flush()
    return out

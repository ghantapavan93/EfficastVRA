"""Tool handlers + the registry. Handlers assume the gateway already authorised the call; they do the
work, enforce data-level invariants (e.g. evidence role match), and record semantic audit events.
"""

from __future__ import annotations

from datetime import timedelta

from sqlmodel import select

from app.domain.base import utcnow
from app.domain.enums import (
    ApprovalStatus,
    AuditEventType,
    ConditionStatus,
    EvidenceStatus,
    KnowledgeStatus,
    LotDisposition,
    Role,
    WorkflowState,
)
from app.domain.models import (
    ApprovalDecision,
    ApprovalRequirement,
    Component,
    EvidenceItem,
    EvidenceRequirement,
    Incident,
    Intervention,
    KnowledgeCandidate,
    Machine,
    MaterialLot,
    RecoveryContract,
    RecoveryObservation,
)
from app.gateway.actions import (
    ALL_ROLES,
    READ_ROLES,
    ToolContext,
    ToolError,
    ToolSpec,
)
from app.domain.enums import ActionClass
from app.services import metrics, quality
from app.services.evaluator import evaluate
from app.services.evidence import validate_item
from app.tools.schemas import (
    IncidentInput,
    InterventionInput,
    KnowledgeInput,
    MachineInput,
    OrderInput,
    PublishDecisionInput,
    QualityInput,
    RecordApprovalInput,
    ReopenInput,
    RequestEvidenceInput,
    SearchRequirementsInput,
    SubmitEvidenceInput,
    ToolOutput,
)
from app.workflow.audit import publish_outbox, record_audit

TECH_ROLES = frozenset({Role.TECHNICIAN, Role.SUPERVISOR, Role.PLANT_ADMIN})
APPROVER_ROLES = frozenset({Role.SUPERVISOR, Role.QUALITY_ENGINEER, Role.PLANT_ADMIN})


# ── READ tools ───────────────────────────────────────────────────────────────
def _h_get_intervention(ctx: ToolContext) -> ToolOutput:
    itv = ctx.session.get(Intervention, ctx.input.intervention_id)
    if itv is None:
        raise ToolError(f"intervention {ctx.input.intervention_id} not found", code="not_found")
    return ToolOutput(data={
        "id": itv.id, "kind": itv.kind, "title": itv.title, "status": itv.status.value,
        "sequence": itv.sequence, "hypothesis": itv.hypothesis,
        "completed_at": itv.completed_at.isoformat() if itv.completed_at else None,
        "measurements": itv.measurements,
    }, source="evidence-system", data_timestamp=itv.completed_at)


def _h_machine_metrics(ctx: ToolContext) -> ToolOutput:
    data = metrics.machine_recovery_metrics(ctx.port, ctx.input.machine_id)
    return ToolOutput(data=data, source=data["source"], freshness_s=data["freshness_s"])


def _h_production_metrics(ctx: ToolContext) -> ToolOutput:
    data = metrics.production_recovery_metrics(ctx.session, ctx.port, ctx.input.order_id)
    return ToolOutput(data=data, source=data["source"])


def _h_quality_status(ctx: ToolContext) -> ToolOutput:
    data = quality.quality_status(ctx.port, machine_id=ctx.input.machine_id, order_id=ctx.input.order_id)
    return ToolOutput(data=data, source=data["source"])


def _h_active_order(ctx: ToolContext) -> ToolOutput:
    po = ctx.port.get_active_production_order(ctx.input.machine_id)
    if po is None:
        return ToolOutput(ok=False, data={}, source="SyntheticEfficastPort")
    return ToolOutput(data=po.model_dump(mode="json"), source=po.source)


def _h_affected_lots(ctx: ToolContext) -> ToolOutput:
    lots = ctx.port.get_affected_lots(ctx.input.order_id)
    return ToolOutput(data={"lots": [lot.model_dump(mode="json") for lot in lots]},
                      source="SyntheticEfficastPort")


def _h_worker_evidence(ctx: ToolContext) -> ToolOutput:
    ev = ctx.port.get_worker_evidence(ctx.input.incident_id)
    return ToolOutput(data={"evidence": [e.model_dump(mode="json") for e in ev]},
                      source="SyntheticEfficastPort")


def _h_search_requirements(ctx: ToolContext) -> ToolOutput:
    from app.rag import search

    results = search(ctx.session, ctx.input.query, machine_model=ctx.input.machine_model,
                     component=ctx.input.component, plant_scope=ctx.principal.plant_id)
    return ToolOutput(data={"results": [r.__dict__ for r in results]}, source="rag")


def _h_search_historical(ctx: ToolContext) -> ToolOutput:
    incident = ctx.session.get(Incident, ctx.input.incident_id)
    if incident is None:
        raise ToolError("incident not found", code="not_found")
    data = ctx.reasoning.compare_historical_interventions(session=ctx.session, incident=incident)
    return ToolOutput(data=data, source="reasoning+rag")


# ── WRITE tools ──────────────────────────────────────────────────────────────
def _h_request_evidence(ctx: ToolContext) -> ToolOutput:
    inp: RequestEvidenceInput = ctx.input
    reqs = ctx.session.exec(
        select(EvidenceRequirement).where(EvidenceRequirement.contract_id == inp.contract_id)
    ).all()
    requested = []
    for r in reqs:
        if inp.requirement_keys and r.key not in inp.requirement_keys:
            continue
        if r.status == EvidenceStatus.MISSING:
            r.status = EvidenceStatus.REQUESTED
            r.due_at = utcnow() + timedelta(hours=2)
            ctx.session.add(r)
            requested.append(r.key)
    record_audit(ctx.session, type=AuditEventType.EVIDENCE_REQUESTED, correlation_id=ctx.correlation_id,
                 actor=ctx.principal.username, role=ctx.principal.role,
                 summary=f"Requested {len(requested)} evidence item(s): {', '.join(requested)}",
                 incident_id=ctx.incident_id, contract_id=inp.contract_id,
                 detail={"requested": requested})
    ctx.session.flush()
    return ToolOutput(data={"requested": requested}, source="workflow", ref=inp.contract_id)


def _h_submit_evidence(ctx: ToolContext) -> ToolOutput:
    inp: SubmitEvidenceInput = ctx.input
    req = ctx.session.get(EvidenceRequirement, inp.requirement_id)
    if req is None:
        raise ToolError("evidence requirement not found", code="not_found")
    if ctx.principal.role != req.assigned_role:
        raise ToolError(
            f"evidence requires role {req.assigned_role.value}, not {ctx.principal.role.value}",
            code="role_mismatch",
        )
    item = EvidenceItem(
        tenant_id=ctx.principal.tenant_id, plant_id=ctx.principal.plant_id,
        requirement_id=req.id, contract_id=req.contract_id, incident_id=req.incident_id,
        kind=req.kind, submitted_by=ctx.principal.username, submitted_role=ctx.principal.role,
        value_num=inp.value_num, value_text=inp.value_text, unit=inp.unit,
        source=inp.source or ctx.principal.username, source_kind="human",
        evidence_timestamp=inp.evidence_timestamp or utcnow(), received_at=utcnow(),
        file_ref=inp.file_ref,
    )
    validate_item(item, req)
    ctx.session.add(item)
    req.status = item.status
    ctx.session.add(req)
    record_audit(ctx.session, type=AuditEventType.EVIDENCE_SUBMITTED, correlation_id=ctx.correlation_id,
                 actor=ctx.principal.username, role=ctx.principal.role,
                 summary=f"Evidence '{req.key}' submitted ({item.status.value}, {item.freshness_s}s old)",
                 incident_id=req.incident_id, contract_id=req.contract_id,
                 detail={"requirement": req.key, "valid": item.valid, "status": item.status.value,
                         "freshness_s": item.freshness_s, "conflict": item.conflict_reason})
    ctx.session.flush()
    return ToolOutput(ok=item.valid, data={"status": item.status.value, "valid": item.valid,
                                           "freshness_s": item.freshness_s,
                                           "conflict_reason": item.conflict_reason},
                      source="human", ref=item.id, freshness_s=item.freshness_s)


def _h_record_approval(ctx: ToolContext) -> ToolOutput:
    inp: RecordApprovalInput = ctx.input
    req = ctx.session.get(ApprovalRequirement, inp.requirement_id)
    if req is None:
        raise ToolError("approval requirement not found", code="not_found")
    if ctx.principal.role != req.required_role:
        raise ToolError(
            f"approval requires role {req.required_role.value}, not {ctx.principal.role.value}",
            code="role_denied",
        )
    decision = ApprovalDecision(
        tenant_id=ctx.principal.tenant_id, requirement_id=req.id, contract_id=req.contract_id,
        incident_id=req.incident_id, decided_by=ctx.principal.username, decided_role=ctx.principal.role,
        decision=inp.decision, reason=inp.reason, policy_ref=req.policy_ref,
        idempotency_key=ctx.idempotency_key or f"approval-{req.id}",
    )
    ctx.session.add(decision)
    req.status = ApprovalStatus.APPROVED if inp.decision == "approve" else ApprovalStatus.REJECTED
    ctx.session.add(req)
    record_audit(ctx.session, type=AuditEventType.APPROVAL_RECORDED, correlation_id=ctx.correlation_id,
                 actor=ctx.principal.username, role=ctx.principal.role,
                 summary=f"Approval '{req.key}' {req.status.value} by {ctx.principal.role.value}",
                 incident_id=req.incident_id, contract_id=req.contract_id,
                 detail={"approval": req.key, "decision": inp.decision, "reason": inp.reason,
                         "grants": req.grants, "denies": req.denies})
    ctx.session.flush()
    return ToolOutput(data={"approval": req.key, "status": req.status.value}, source="human", ref=decision.id)


def _h_publish_decision(ctx: ToolContext) -> ToolOutput:
    inp: PublishDecisionInput = ctx.input
    result = ctx.port.publish_recovery_decision(
        incident_id=inp.incident_id,
        decision={"type": inp.decision_type, "summary": inp.summary},
        correlation_id=ctx.correlation_id,
    )
    record_audit(ctx.session, type=AuditEventType.DECISION_PUBLISHED, correlation_id=ctx.correlation_id,
                 actor=ctx.principal.username, role=ctx.principal.role,
                 summary=f"Published recovery decision: {inp.decision_type}",
                 incident_id=inp.incident_id, detail={"decision_type": inp.decision_type, "ref": result.ref})
    ctx.session.flush()
    return ToolOutput(data={"published": inp.decision_type}, source="EfficastPort", ref=result.ref)


def _policy_reopen(ctx: ToolContext) -> tuple[bool, str]:
    incident = ctx.session.get(Incident, ctx.input.incident_id)
    if incident is None or incident.current_contract_id is None:
        return False, "no active contract"
    contract = ctx.session.get(RecoveryContract, incident.current_contract_id)
    result = evaluate(ctx.session, contract)
    if result.verdict != "violated":
        return False, "recovery is not in a violated state; reopening not permitted"
    return True, "violation confirmed"


def _h_reopen_incident(ctx: ToolContext) -> ToolOutput:
    from app.workflow.reopening import reopen_with_contingency

    incident = ctx.session.get(Incident, ctx.input.incident_id)
    contract = ctx.session.get(RecoveryContract, incident.current_contract_id)
    result = evaluate(ctx.session, contract)
    v2 = reopen_with_contingency(ctx.session, ctx.port, incident, contract,
                                 violated_keys=result.violated_keys,
                                 actor=ctx.principal.username, role=ctx.principal.role)
    return ToolOutput(data={"new_contract": v2.id, "violated": result.violated_keys},
                      source="workflow", ref=v2.id)


def derive_knowledge_candidate(session, incident: Incident) -> dict:
    """Derive a knowledge candidate's content from the incident's *own* facts (M-C).

    The lesson is built from the fault, the machine's model, which intervention failed vs. held, the
    replaced component, the relapse cycle (read from the first faulted observation), and the verified
    window — so it generalises to any machine/fault rather than being hardcoded to the Northstar
    F27 / CDX-220 / BR-6205 case. Returns the content-bearing ``KnowledgeCandidate`` fields.
    """
    interventions = session.exec(
        select(Intervention).where(Intervention.incident_id == incident.id)
        .order_by(Intervention.sequence)  # type: ignore[arg-type]
    ).all()

    # The contract whose verification passed binds the intervention that *held*; an earlier
    # (lower-sequence) intervention is the one that did not.
    contract = (session.get(RecoveryContract, incident.current_contract_id)
                if incident.current_contract_id else None)
    success = (session.get(Intervention, contract.intervention_id)
               if (contract and contract.intervention_id) else None)
    if success is None and interventions:
        success = interventions[-1]
    failed = next((i for i in interventions if success and i.sequence < success.sequence), None)

    machine = session.get(Machine, incident.machine_id)
    model = (machine.machine_model if machine else "") or ""
    component = (session.get(Component, success.component_id)
                 if (success and success.component_id) else None)

    fault = incident.fault_code or "the fault"
    required_stable = (int((contract.verification_window or {}).get("required_stable_cycles", 30))
                       if contract else 30)

    # Relapse cycle — read from the first observation that carried a fault, not assumed.
    observations = session.exec(
        select(RecoveryObservation).where(RecoveryObservation.incident_id == incident.id)
        .order_by(RecoveryObservation.cycle_index)  # type: ignore[arg-type]
    ).all()
    faulted = next((o for o in observations if o.fault_code), None)
    recurrence_cycle = faulted.cycle_index if faulted else None

    def _action(itv, default: str) -> str:
        if itv is None:
            return default
        return (itv.kind or "").replace("_", " ").strip() or (itv.title or default)

    failed_action = _action(failed, "the initial intervention")
    success_action = _action(success, "a follow-up intervention")
    root_cause = (component.kind if component else "") or "the affected component"
    remedy_noun = (component.name if component else "") or root_cause
    part_suffix = f" ({component.part_number})" if (component and component.part_number) else ""
    where = f"On {model} machines, " if model else ""

    if failed is not None:
        title = f"{fault} recurrence after {failed_action} → {success_action}"
        window_phrase = (f"within ~{recurrence_cycle} cycles " if recurrence_cycle is not None else "")
        lesson = (f"{where}{fault} recurrence {window_phrase}after a {failed_action} indicates "
                  f"{root_cause} degradation; replace the {remedy_noun}{part_suffix} and verify over "
                  f"{required_stable} stable cycles.")
    else:
        title = f"{fault} recovered by {success_action}"
        lesson = (f"{where}{fault} was recovered by {success_action}{part_suffix}; verify over "
                  f"{required_stable} stable cycles before closing the work order.")
    if not where:  # sentence now starts with the fault code — capitalise it
        lesson = lesson[:1].upper() + lesson[1:]

    conditions: dict = {"fault": incident.fault_code, "required_stable_cycles": required_stable}
    if recurrence_cycle is not None:
        conditions["recurrence_cycle"] = recurrence_cycle

    return {
        "title": title,
        "lesson": lesson,
        "component": (component.kind if component else "") or "",
        "applicable_models": [model] if model else [],
        "conditions": conditions,
        "supporting_evidence": [i.id for i in interventions],
        "failed_intervention": failed.id if failed else "",
        "successful_intervention": success.id if success else "",
    }


def _h_create_knowledge(ctx: ToolContext) -> ToolOutput:
    incident = ctx.session.get(Incident, ctx.input.incident_id)
    if incident is None:
        raise ToolError("incident not found", code="not_found")
    kc = KnowledgeCandidate(
        tenant_id=incident.tenant_id, plant_id=incident.plant_id, incident_id=incident.id,
        status=KnowledgeStatus.PENDING_REVIEW, reviewer_role=Role.QUALITY_ENGINEER,
        review_due=utcnow() + timedelta(days=30),
        **derive_knowledge_candidate(ctx.session, incident),
    )
    ctx.session.add(kc)
    record_audit(ctx.session, type=AuditEventType.KNOWLEDGE_CANDIDATE_CREATED,
                 correlation_id=ctx.correlation_id, actor=ctx.principal.username, role=ctx.principal.role,
                 summary="Knowledge candidate created — PENDING expert review (not approved guidance).",
                 incident_id=incident.id, detail={"status": kc.status.value})
    ctx.session.flush()
    return ToolOutput(data={"status": kc.status.value, "title": kc.title}, source="workflow", ref=kc.id)


# ── Registry ─────────────────────────────────────────────────────────────────
def _spec(name, action_class, roles, in_model, is_write, handler, summary, *, policy=None,
          requires_human=False) -> ToolSpec:
    return ToolSpec(name=name, action_class=action_class, allowed_roles=roles, input_model=in_model,
                    output_model=ToolOutput, is_write=is_write, handler=handler, summary=summary,
                    policy=policy, requires_human=requires_human)


_R = ActionClass.READ_ONLY
_A = ActionClass.REVERSIBLE_AUTOMATIC
_P = ActionClass.APPROVAL_REQUIRED

REGISTRY: dict[str, ToolSpec] = {
    "get_intervention_record": _spec("get_intervention_record", _R, READ_ROLES, InterventionInput, False, _h_get_intervention, "Read a recorded intervention."),
    "get_machine_recovery_metrics": _spec("get_machine_recovery_metrics", _R, READ_ROLES, MachineInput, False, _h_machine_metrics, "Machine metrics vs baseline."),
    "get_production_recovery_metrics": _spec("get_production_recovery_metrics", _R, READ_ROLES, OrderInput, False, _h_production_metrics, "Production metrics for an order."),
    "get_quality_status": _spec("get_quality_status", _R, READ_ROLES, QualityInput, False, _h_quality_status, "Quality hold status."),
    "get_active_production_order": _spec("get_active_production_order", _R, READ_ROLES, MachineInput, False, _h_active_order, "Active production order for a machine."),
    "get_affected_lots": _spec("get_affected_lots", _R, READ_ROLES, OrderInput, False, _h_affected_lots, "Lots affected by an order."),
    "get_worker_evidence": _spec("get_worker_evidence", _R, READ_ROLES, IncidentInput, False, _h_worker_evidence, "Human-submitted worker evidence."),
    "search_recovery_requirements": _spec("search_recovery_requirements", _R, READ_ROLES, SearchRequirementsInput, False, _h_search_requirements, "Filtered retrieval over manuals/policy."),
    "search_historical_interventions": _spec("search_historical_interventions", _R, READ_ROLES, IncidentInput, False, _h_search_historical, "Compare past interventions."),
    "request_missing_evidence": _spec("request_missing_evidence", _A, ALL_ROLES | {Role.AGENT}, RequestEvidenceInput, True, _h_request_evidence, "Create evidence requests."),
    "submit_evidence": _spec("submit_evidence", _A, TECH_ROLES | {Role.QUALITY_ENGINEER}, SubmitEvidenceInput, True, _h_submit_evidence, "Submit a measurement / result.", requires_human=True),
    "record_human_approval": _spec("record_human_approval", _P, APPROVER_ROLES, RecordApprovalInput, True, _h_record_approval, "Record a human approval/rejection.", requires_human=True),
    "publish_recovery_decision": _spec("publish_recovery_decision", _A, ALL_ROLES | {Role.AGENT}, PublishDecisionInput, True, _h_publish_decision, "Publish a recovery decision event."),
    "reopen_incident": _spec("reopen_incident", _A, ALL_ROLES | {Role.AGENT}, ReopenInput, True, _h_reopen_incident, "Reopen + activate contingency (only when violated).", policy=_policy_reopen),
    "create_knowledge_candidate": _spec("create_knowledge_candidate", _A, ALL_ROLES | {Role.AGENT}, KnowledgeInput, True, _h_create_knowledge, "Create a PENDING-review knowledge candidate."),
}


def get_tool(name: str) -> ToolSpec | None:
    return REGISTRY.get(name)

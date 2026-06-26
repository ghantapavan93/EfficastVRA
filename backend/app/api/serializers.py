"""ORM → JSON view builders for the frontend. The frontend consumes backend truth only."""

from __future__ import annotations

from sqlmodel import Session, select

from app.domain.base import utcnow
from app.domain.enums import WorkflowState
from app.domain.models import (
    ApprovalDecision,
    ApprovalRequirement,
    AuditEvent,
    EvidenceItem,
    EvidenceRequirement,
    Incident,
    Intervention,
    KnowledgeCandidate,
    Machine,
    MaterialLot,
    ProductionOrder,
    RecoveryCondition,
    RecoveryContract,
    RecoveryObservation,
)
from app.seed.northstar import BASELINE, DEGRADED
from app.services.evaluator import evaluate
from app.services.evidence import missing_required

# Mission-rail stage + UX metadata per workflow state.
_STATE_META: dict[str, dict] = {
    WorkflowState.ALERT_TRIAGED.value: {"group": "requires_decision", "stage": "diagnosis", "next": "Agent triaging MAIA alert", "owner": "agent"},
    WorkflowState.INTERVENTION_PROPOSED.value: {"group": "requires_decision", "stage": "diagnosis", "next": "Accept diagnosis to record intervention", "owner": "supervisor"},
    WorkflowState.INTERVENTION_RECORDED.value: {"group": "requires_decision", "stage": "intervention", "next": "Draft recovery contract", "owner": "agent"},
    WorkflowState.RECOVERY_CONTRACT_DRAFTED.value: {"group": "requires_decision", "stage": "contract", "next": "Review recovery contract", "owner": "supervisor"},
    WorkflowState.RECOVERY_CONTRACT_REVIEWED.value: {"group": "awaiting_evidence", "stage": "contract", "next": "Submit required evidence", "owner": "technician"},
    WorkflowState.AWAITING_REQUIRED_EVIDENCE.value: {"group": "awaiting_evidence", "stage": "evidence", "next": "Submit required evidence", "owner": "technician"},
    WorkflowState.READY_FOR_MONITORING.value: {"group": "requires_decision", "stage": "monitoring", "next": "Start recovery monitoring", "owner": "agent"},
    WorkflowState.MONITORING_RECOVERY.value: {"group": "monitoring", "stage": "monitoring", "next": "Monitoring recovery cycles", "owner": "agent"},
    WorkflowState.RECOVERY_CONDITION_PENDING.value: {"group": "monitoring", "stage": "monitoring", "next": "Awaiting condition results", "owner": "agent"},
    WorkflowState.RECOVERY_CONDITION_FAILED.value: {"group": "reopened", "stage": "monitoring", "next": "Recovery condition failed", "owner": "agent"},
    WorkflowState.INSUFFICIENT_EVIDENCE.value: {"group": "awaiting_evidence", "stage": "evidence", "next": "Provide fresh evidence", "owner": "technician"},
    WorkflowState.RECOVERY_FAILED.value: {"group": "reopened", "stage": "monitoring", "next": "Reopen incident", "owner": "agent"},
    WorkflowState.INCIDENT_REOPENED.value: {"group": "reopened", "stage": "verification", "next": "Approve contingency", "owner": "supervisor"},
    WorkflowState.CONTINGENCY_AWAITING_APPROVAL.value: {"group": "requires_decision", "stage": "verification", "next": "Approve bearing contingency", "owner": "supervisor"},
    WorkflowState.CONTINGENCY_IN_PROGRESS.value: {"group": "monitoring", "stage": "verification", "next": "Complete contingency work", "owner": "technician"},
    WorkflowState.VERIFIED_RECOVERY.value: {"group": "verified", "stage": "outcome", "next": "Recovery verified", "owner": "—"},
    WorkflowState.ESCALATED.value: {"group": "escalated", "stage": "outcome", "next": "Escalated to supervision", "owner": "supervisor"},
    WorkflowState.CANCELLED.value: {"group": "escalated", "stage": "outcome", "next": "Cancelled", "owner": "—"},
}

_RAIL = ["diagnosis", "intervention", "contract", "evidence", "approval", "monitoring", "verification", "outcome"]


def _iso(dt):
    return dt.isoformat() if dt else None


def state_meta(state: WorkflowState) -> dict:
    return _STATE_META.get(state.value, {"group": "monitoring", "stage": "monitoring", "next": "", "owner": "agent"})


def _machine(session: Session, machine_id: str) -> Machine | None:
    return session.get(Machine, machine_id)


def mission_summary(session: Session, incident: Incident) -> dict:
    meta = state_meta(incident.state)
    contract = session.get(RecoveryContract, incident.current_contract_id) if incident.current_contract_id else None
    missing = len(missing_required(session, contract.id, "monitoring")) if contract else 0
    machine = _machine(session, incident.machine_id)
    order = session.get(ProductionOrder, incident.order_id) if incident.order_id else None
    progress = _recovery_progress(incident, contract, session)
    return {
        "id": incident.id,
        "title": incident.title,
        "objective": contract.objective if contract else "Define and verify recovery.",
        "machine": {"id": machine.id, "code": machine.code, "name": machine.name} if machine else None,
        "order": {"id": order.id, "product": order.product, "qty_remaining": order.qty_remaining} if order else None,
        "state": incident.state.value,
        "state_group": meta["group"],
        "stage": meta["stage"],
        "severity": incident.severity.value,
        "next_action": meta["next"],
        "owner": meta["owner"],
        "missing_evidence": missing,
        "reopened_count": incident.reopened_count,
        "fault_code": incident.fault_code,
        "origin_alert_id": incident.origin_alert_id,
        "contract_no": contract.contract_no if contract else None,
        "contract_version": contract.version if contract else None,
        "recovery_progress": progress,
        "opened_at": _iso(incident.opened_at),
        "updated_at": _iso(incident.updated_at),
        "is_active": incident.state not in (WorkflowState.VERIFIED_RECOVERY, WorkflowState.CANCELLED),
    }


def _recovery_progress(incident: Incident, contract, session: Session) -> int:
    """A 0–100 *progress* heuristic for list/header display — NOT a calibrated probability. It ramps with
    stable cycles (and the agent's display confidence). The statistically grounded figure (zero-failure
    demonstration + SPRT) lives in the Recovery Confidence tab / reliability assessment."""
    from app.agent.trace import latest_confidence

    c = latest_confidence(session, incident.id)
    if c is not None:
        return int(round(c * 100))
    if incident.state == WorkflowState.VERIFIED_RECOVERY:
        return 100
    if incident.state in (WorkflowState.RECOVERY_FAILED, WorkflowState.INCIDENT_REOPENED,
                          WorkflowState.CONTINGENCY_AWAITING_APPROVAL, WorkflowState.RECOVERY_CONDITION_FAILED):
        return 20
    if contract is None:
        return 40
    result = evaluate(session, contract)
    if result.required_stable_cycles:
        return int(40 + 55 * min(result.stable_streak / result.required_stable_cycles, 1.0))
    return 50


# Plain-language brief for operators/technicians — no jargon, says what happened + what to do now.
_WORKER_BRIEF: dict[str, dict] = {
    "ALERT_TRIAGED": {"headline": "The agent is sizing up a new alert",
                      "what_happened": "MAIA flagged a repeating fault and the agent is diagnosing it.",
                      "what_to_do_now": "Nothing yet — a proposed fix is coming.", "who": "Agent"},
    "INTERVENTION_PROPOSED": {"headline": "A fix has been proposed — your OK is needed",
                              "what_happened": "The agent diagnosed the fault and proposed an intervention.",
                              "what_to_do_now": "Review the diagnosis and accept it if it looks right.",
                              "who": "Supervisor"},
    "INTERVENTION_RECORDED": {"headline": "Fix recorded — building the recovery checklist",
                              "what_happened": "The intervention is logged; the agent is drafting what 'recovered' must look like.",
                              "what_to_do_now": "Nothing yet.", "who": "Agent"},
    "RECOVERY_CONTRACT_DRAFTED": {"headline": "Recovery checklist ready for review",
                                  "what_happened": "The agent wrote the conditions that prove recovery.",
                                  "what_to_do_now": "Review and approve the recovery contract.", "who": "Supervisor"},
    "RECOVERY_CONTRACT_REVIEWED": {"headline": "Measurements needed before monitoring",
                                   "what_happened": "The contract is approved.",
                                   "what_to_do_now": "Submit the post-fix measurement and completion sign-off.",
                                   "who": "Technician"},
    "AWAITING_REQUIRED_EVIDENCE": {"headline": "Waiting on a measurement",
                                   "what_happened": "Monitoring can't start until the required evidence is in.",
                                   "what_to_do_now": "Submit the post-fix measurement.", "who": "Technician"},
    "READY_FOR_MONITORING": {"headline": "Ready to watch the recovery",
                             "what_happened": "Evidence and approval are in.",
                             "what_to_do_now": "Nothing — monitoring starts automatically.", "who": "Agent"},
    "MONITORING_RECOVERY": {"headline": "Watching the machine actually recover",
                            "what_happened": "The agent is checking each cycle against the contract.",
                            "what_to_do_now": "Nothing — it needs a full run of stable cycles before closing.",
                            "who": "Agent"},
    "INCIDENT_REOPENED": {"headline": "The first fix did NOT hold — fault came back",
                          "what_happened": "Early cycles looked fine, then the fault recurred. The agent reopened the incident.",
                          "what_to_do_now": "Approve the contingency (bearing replacement).", "who": "Supervisor"},
    "CONTINGENCY_AWAITING_APPROVAL": {"headline": "Second fix proposed — your OK is needed",
                                      "what_happened": "The agent recommends the bearing-replacement contingency.",
                                      "what_to_do_now": "Approve to reserve the part and assign a technician.",
                                      "who": "Supervisor"},
    "CONTINGENCY_IN_PROGRESS": {"headline": "Bearing replacement underway",
                                "what_happened": "The contingency is approved and in progress.",
                                "what_to_do_now": "Complete the work and submit the measurement.", "who": "Technician"},
    "VERIFIED_RECOVERY": {"headline": "Recovery confirmed",
                          "what_happened": "All conditions passed for the full window and quality released.",
                          "what_to_do_now": "Done — the verified recovery is logged.", "who": "—"},
    "ESCALATED": {"headline": "Escalated to plant supervision",
                  "what_happened": "Recovery could not be verified within policy.",
                  "what_to_do_now": "Plant supervision will take it from here.", "who": "Supervisor"},
}


def _worker_brief(incident: Incident, session: Session) -> dict:
    base = _WORKER_BRIEF.get(incident.state.value, {
        "headline": "Recovery in progress", "what_happened": "", "what_to_do_now": "", "who": "Agent"})
    # Quality-release nuance: technically recovered but a quality engineer must still release.
    if incident.state == WorkflowState.MONITORING_RECOVERY and incident.current_contract_id:
        contract = session.get(RecoveryContract, incident.current_contract_id)
        if contract is not None:
            result = evaluate(session, contract)
            if result.awaiting_quality:
                return {"headline": "Recovered — waiting on quality release",
                        "what_happened": "Every machine and production condition passed.",
                        "what_to_do_now": "Quality engineer: review the first-piece and release the hold.",
                        "who": "Quality engineer"}
    return base


def mission_detail(session: Session, incident: Incident) -> dict:
    summary = mission_summary(session, incident)
    interventions = session.exec(
        select(Intervention).where(Intervention.incident_id == incident.id).order_by(Intervention.sequence)  # type: ignore[arg-type]
    ).all()
    rail = _progress_rail(incident)
    summary.update({
        "interventions": [{
            "id": i.id, "sequence": i.sequence, "kind": i.kind, "title": i.title,
            "status": i.status.value, "hypothesis": i.hypothesis,
            "completed_at": _iso(i.completed_at),
        } for i in interventions],
        "progress_rail": rail,
        "worker_brief": _worker_brief(incident, session),
        "agent_responsibility": "Define recovery, gather evidence, observe the real trajectory, and decide closure. Never controls the machine.",
        "human_responsibility": "Perform physical work, submit measurements, and grant approvals.",
        "environment": "synthetic-demo",
    })
    return summary


def _progress_rail(incident: Incident) -> list[dict]:
    meta = state_meta(incident.state)
    active = meta["stage"]
    reopened = incident.reopened_count > 0
    order = _RAIL
    active_idx = order.index(active) if active in order else 0
    rail = []
    for i, stage in enumerate(order):
        if incident.state == WorkflowState.VERIFIED_RECOVERY:
            status = "complete"
        elif i < active_idx:
            status = "complete"
        elif i == active_idx:
            status = "active"
        else:
            status = "upcoming"
        if reopened and stage in ("monitoring", "verification") and incident.state != WorkflowState.VERIFIED_RECOVERY:
            if stage == "monitoring" and active != "monitoring":
                status = "reopened"
        rail.append({"stage": stage, "status": status})
    return rail


def condition_views(session: Session, contract: RecoveryContract) -> dict:
    result = evaluate(session, contract)
    conds = session.exec(select(RecoveryCondition).where(RecoveryCondition.contract_id == contract.id)).all()
    groups = {"machine": [], "production": [], "quality": []}
    for c in conds:
        groups[c.kind.value.lower()].append({
            "key": c.key, "label": c.label, "op": c.op.value, "threshold": c.threshold,
            "unit": c.unit, "baseline": c.baseline, "current_value": c.current_value,
            "status": c.status.value, "sensor_tag": c.sensor_tag, "fault_code": c.fault_code,
            "deadline_kind": c.deadline_kind, "deadline_value": c.deadline_value,
            "policy_ref": c.policy_ref, "rationale": (c.detail or {}).get("rationale", ""),
        })
    return {"groups": groups, "evaluation": result.__dict__}


def contract_view(session: Session, contract: RecoveryContract) -> dict:
    cv = condition_views(session, contract)
    ev_reqs = session.exec(select(EvidenceRequirement).where(EvidenceRequirement.contract_id == contract.id)).all()
    ap_reqs = session.exec(select(ApprovalRequirement).where(ApprovalRequirement.contract_id == contract.id)).all()
    return {
        "id": contract.id, "contract_no": contract.contract_no, "version": contract.version,
        "status": contract.status, "objective": contract.objective, "drafted_by": contract.drafted_by,
        "policy_version": contract.policy_version, "workflow_version": contract.workflow_version,
        "incident_id": contract.incident_id, "superseded_by": contract.superseded_by,
        "conditions": cv["groups"], "evaluation": cv["evaluation"],
        "verification_window": contract.verification_window,
        "closure_policy": contract.closure_policy, "reopening_policy": contract.reopening_policy,
        "escalation_policy": contract.escalation_policy,
        "evidence_requirements": [_ev_req(session, r) for r in ev_reqs],
        "approval_requirements": [_ap_req(session, r) for r in ap_reqs],
    }


def _ev_req(session: Session, r: EvidenceRequirement) -> dict:
    items = session.exec(
        select(EvidenceItem).where(EvidenceItem.requirement_id == r.id).order_by(EvidenceItem.received_at.desc())  # type: ignore[attr-defined]
    ).all()
    latest = items[0] if items else None
    return {
        "id": r.id, "key": r.key, "label": r.label, "kind": r.kind.value,
        "assigned_role": r.assigned_role.value, "reason_required": r.reason_required,
        "required_before": r.required_before, "freshness_max_s": r.freshness_max_s,
        "status": r.status.value, "blocks_conditions": r.blocks_conditions,
        "due_at": _iso(r.due_at),
        "submitted": None if latest is None else {
            "id": latest.id, "value_num": latest.value_num, "value_text": latest.value_text,
            "unit": latest.unit, "source": latest.source, "submitted_by": latest.submitted_by,
            "submitted_role": latest.submitted_role.value, "valid": latest.valid,
            "status": latest.status.value, "freshness_s": latest.freshness_s,
            "conflict_reason": latest.conflict_reason, "at": _iso(latest.evidence_timestamp),
        },
    }


def _ap_req(session: Session, r: ApprovalRequirement) -> dict:
    decision = session.exec(
        select(ApprovalDecision).where(ApprovalDecision.requirement_id == r.id)
    ).first()
    return {
        "id": r.id, "key": r.key, "label": r.label, "required_role": r.required_role.value,
        "required_before": r.required_before, "grants": r.grants, "denies": r.denies,
        "status": r.status.value, "policy_ref": r.policy_ref,
        "decision": None if decision is None else {
            "decided_by": decision.decided_by, "decided_role": decision.decided_role.value,
            "decision": decision.decision, "reason": decision.reason, "at": _iso(decision.decided_at),
        },
    }


def evidence_view(session: Session, incident: Incident) -> dict:
    contract = session.get(RecoveryContract, incident.current_contract_id) if incident.current_contract_id else None
    if contract is None:
        return {"groups": {}, "requirements": []}
    reqs = session.exec(select(EvidenceRequirement).where(EvidenceRequirement.contract_id == contract.id)).all()
    reqs_v = [_ev_req(session, r) for r in reqs]
    groups: dict[str, list] = {}
    for rv in reqs_v:
        status = rv["status"]
        groups.setdefault(status, []).append(rv)
    return {"contract_id": contract.id, "groups": groups, "requirements": reqs_v}


def timeline_view(session: Session, incident: Incident) -> dict:
    audits = session.exec(
        select(AuditEvent).where(AuditEvent.incident_id == incident.id).order_by(AuditEvent.seq)  # type: ignore[arg-type]
    ).all()
    obs = session.exec(
        select(RecoveryObservation).where(RecoveryObservation.incident_id == incident.id)
        .order_by(RecoveryObservation.at)  # type: ignore[arg-type]
    ).all()
    events = [{
        "kind": "audit", "seq": a.seq, "type": a.type.value, "summary": a.summary,
        "actor": a.actor, "role": a.role.value if a.role else None, "at": _iso(a.created_at),
        "prev_state": a.prev_state.value if a.prev_state else None,
        "new_state": a.new_state.value if a.new_state else None, "detail": a.detail,
    } for a in audits]
    cycles = [{
        "kind": "cycle", "cycle_index": o.cycle_index, "window": o.window_id, "at": _iso(o.at),
        "vibration": o.vibration, "temperature": o.temperature, "cycle_time": o.cycle_time,
        "scrap_pct": o.scrap_pct, "fault_code": o.fault_code, "source": o.source,
        "freshness_s": o.freshness_s,
        # A recurrence = an observation carrying the incident's *originating* fault, not a literal "F27".
        "is_recurrence": bool(o.fault_code) and o.fault_code == incident.fault_code,
    } for o in obs]
    return {"events": events, "cycles": cycles}


def outcome_view(session: Session, incident: Incident) -> dict:
    contract = session.get(RecoveryContract, incident.current_contract_id) if incident.current_contract_id else None
    interventions = session.exec(
        select(Intervention).where(Intervention.incident_id == incident.id).order_by(Intervention.sequence)  # type: ignore[arg-type]
    ).all()
    lots = session.exec(select(MaterialLot).where(MaterialLot.order_id == incident.order_id)).all() if incident.order_id else []
    kc = session.exec(select(KnowledgeCandidate).where(KnowledgeCandidate.incident_id == incident.id)).first()
    result = evaluate(session, contract) if contract else None
    quality_ok = result.verdict == "verified" if result else False
    return {
        "incident_id": incident.id, "state": incident.state.value,
        "outcome_type": incident.outcome_type.value if incident.outcome_type else None,
        "summary": incident.outcome_summary,
        "before": {"vibration": DEGRADED["vibration"], "temperature": DEGRADED["temperature"],
                   "cycle_time": DEGRADED["cycle_time"], "scrap_pct": DEGRADED["scrap_pct"],
                   "fault": f"{incident.fault_code or 'fault'} recurring"},
        "after": {"vibration": BASELINE["vibration_mm_s"], "temperature": BASELINE["temp_c"],
                  "cycle_time": BASELINE["cycle_time_s"], "scrap_pct": BASELINE["scrap_pct"],
                  "fault": f"{incident.fault_code or 'fault'} absent for "
                           f"{result.required_stable_cycles if result else 30} stable cycles"},
        "stable_cycles": result.stable_streak if result else 0,
        "required_stable_cycles": result.required_stable_cycles if result else 30,
        "reopened_count": incident.reopened_count,
        "interventions": [{"sequence": i.sequence, "kind": i.kind, "title": i.title,
                           "status": i.status.value, "failed": i.sequence == 1 and incident.reopened_count > 0}
                          for i in interventions],
        "lots": [{"id": lot.id, "qty": lot.qty, "disposition": lot.disposition.value} for lot in lots],
        "quality_released": quality_ok,
        "policy_version": contract.policy_version if contract else None,
        "knowledge_candidate": knowledge_view(kc) if kc else None,
        "closed_at": _iso(incident.closed_at),
    }


def knowledge_view(kc: KnowledgeCandidate) -> dict:
    return {
        "id": kc.id, "title": kc.title, "lesson": kc.lesson, "component": kc.component,
        "applicable_models": kc.applicable_models, "conditions": kc.conditions,
        "supporting_evidence": kc.supporting_evidence, "failed_intervention": kc.failed_intervention,
        "successful_intervention": kc.successful_intervention, "status": kc.status.value,
        "reviewer_role": kc.reviewer_role.value, "review_due": _iso(kc.review_due),
        "pending_review": kc.status.value == "PENDING_REVIEW",
        "incident_id": kc.incident_id, "reviewed_by": kc.reviewed_by,
        "reviewed_at": _iso(kc.reviewed_at), "review_reason": kc.review_reason,
    }


def audit_view(session: Session, incident: Incident) -> list[dict]:
    audits = session.exec(
        select(AuditEvent).where(AuditEvent.incident_id == incident.id).order_by(AuditEvent.seq)  # type: ignore[arg-type]
    ).all()
    return [{
        "seq": a.seq, "type": a.type.value, "summary": a.summary, "actor": a.actor,
        "role": a.role.value if a.role else None, "at": _iso(a.created_at),
        "policy_version": a.policy_version, "workflow_version": a.workflow_version,
        "model_version": a.model_version, "prev_state": a.prev_state.value if a.prev_state else None,
        "new_state": a.new_state.value if a.new_state else None, "detail": a.detail,
        "entry_hash": (a.entry_hash or "")[:12], "prev_hash": (a.prev_hash or "")[:12],
    } for a in audits]


def forecast_view(session: Session, incident: Incident) -> dict:
    """Recovery Forecaster — the live prediction of whether this repair will hold (advisory)."""
    import dataclasses

    from app.services.forecaster import forecast as _forecast

    if not incident.current_contract_id:
        return {"available": False, "incident_id": incident.id}
    contract = session.get(RecoveryContract, incident.current_contract_id)
    if contract is None:
        return {"available": False, "incident_id": incident.id}
    return {"incident_id": incident.id, **dataclasses.asdict(_forecast(session, contract))}


def notification_view(n) -> dict:
    return {
        "id": n.id, "incident_id": n.incident_id, "to_role": n.to_role.value,
        "channel": n.channel, "kind": n.kind, "title": n.title, "body": n.body,
        "status": n.status, "action_path": n.action_path, "at": _iso(n.created_at),
    }


_NODE_LABEL = {
    "perceive": "Perceive", "retrieve": "Retrieve", "hypothesize": "Hypothesize",
    "draft": "Draft contract", "self_critique": "Self-critique", "decide": "Decide",
    "observe": "Observe", "reflect": "Reflect",
}


def _alert_dict(a) -> dict:
    return {
        "id": a.id, "source": a.source, "kind": a.kind, "machine_id": a.machine_id,
        "order_id": a.order_id, "fault_code": a.fault_code,
        "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
        "message": a.message, "signals": a.signals or {}, "detected_at": _iso(a.detected_at),
        "status": a.status, "resulted_in_incident": a.resulted_in_incident,
    }


def machine_profiles_view() -> dict:
    """The machine-agnostic Recovery Contract catalog — proves the engine is not conveyor-specific."""
    from app.services.machine_profiles import PROFILES

    return {
        "profiles": [
            {
                "equipment_class": p.equipment_class, "label": p.label, "machine_models": p.machine_models,
                "summary": p.summary, "required_stable_cycles": p.required_stable_cycles,
                "cycle_seconds": p.cycle_seconds, "fault_codes": p.fault_codes,
                "condition_count": len(p.conditions),
                "signals": [
                    {"key": c.key, "label": c.label, "op": c.op.value, "unit": c.unit,
                     "threshold": c.threshold, "kind": c.kind.value}
                    for c in p.conditions
                ],
            }
            for p in PROFILES.values()
        ],
    }


def integration_view(session: Session) -> dict:
    """ISA-95 hierarchy + Unified-Namespace topics + the connector catalog (how real plant data
    sources map onto the system's seams). Documented, not a live connection."""
    from app.domain.models import Machine
    from app.integration import CONNECTORS, ISA95_LEVELS, asset_path, sparkplug_topic, uns_topic
    from app.seed.northstar import IDS

    machine = session.get(Machine, IDS["machine"])
    example: dict = {}
    if machine is not None:
        path = asset_path(session, machine)
        signals = ["vibration", "temperature", "cycle_time", "scrap"]
        example = {
            "machine": machine.code,
            "isa95_path": path.segments(),
            "uns_topics": [uns_topic(session, machine, s) for s in signals],
            "sparkplug_topic": sparkplug_topic(session, machine),
        }
    return {
        "isa95_levels": ISA95_LEVELS,
        "example": example,
        "connectors": [
            {"key": c.key, "label": c.label, "protocol": c.protocol, "direction": c.direction,
             "feeds": c.feeds, "description": c.description, "status": c.status}
            for c in CONNECTORS
        ],
        "note": ("The agent is the reasoning layer above the MES / Unified Namespace. Connectors are "
                 "documented seams, not live connections in this synthetic prototype — and none can "
                 "carry a machine-control command."),
    }


def open_alerts_view(session: Session) -> list[dict]:
    from app.domain.models import MaiaAlert

    alerts = session.exec(
        select(MaiaAlert).where(MaiaAlert.status == "open").order_by(MaiaAlert.detected_at)  # type: ignore[arg-type]
    ).all()
    return [_alert_dict(a) for a in alerts]


def diagnosis_view(session: Session, incident: Incident) -> dict:
    """The agent's triage diagnosis for an incident, drawn from its reasoning trace + the proposed
    intervention. Returns ``available: False`` for incidents that did not originate from an alert."""
    from app.agent.trace import list_traces
    from app.domain.models import Intervention, MaiaAlert

    traces = list_traces(session, incident.id)
    by_node = {}
    for t in traces:
        by_node[t.node] = t  # keep the latest of each node

    propose = by_node.get("propose")
    if propose is None:
        return {"available": False, "incident_id": incident.id,
                "origin_alert_id": incident.origin_alert_id}

    classify = by_node.get("classify")
    hypo = by_node.get("hypothesize")
    retrieve = by_node.get("retrieve")
    itv = session.exec(
        select(Intervention).where(Intervention.incident_id == incident.id)
        .order_by(Intervention.sequence)  # type: ignore[arg-type]
    ).first()
    alert = session.get(MaiaAlert, incident.origin_alert_id) if incident.origin_alert_id else None
    accepted = incident.state not in (WorkflowState.ALERT_TRIAGED, WorkflowState.INTERVENTION_PROPOSED)

    return {
        "available": True,
        "incident_id": incident.id,
        "origin_alert_id": incident.origin_alert_id,
        "alert": _alert_dict(alert) if alert else None,
        "degradation_kind": (classify.outputs or {}).get("degradation_kind") if classify else None,
        "root_causes": (hypo.outputs or {}).get("root_causes", []) if hypo else [],
        "recommended_intervention": (propose.outputs or {}).get("recommended_intervention"),
        "contingency": (propose.outputs or {}).get("contingency"),
        "diagnostic_confidence": (propose.outputs or {}).get("diagnostic_confidence"),
        "citations": retrieve.citations if retrieve else [],
        "perceived": (by_node.get("perceive").outputs if by_node.get("perceive") else {}),
        "proposed_intervention": ({"id": itv.id, "kind": itv.kind, "title": itv.title,
                                   "status": itv.status.value} if itv else None),
        "accepted": accepted,
        "state": incident.state.value,
        "model_version": propose.model_version,
    }


def reasoning_view(session: Session, incident: Incident) -> dict:
    """The agent's bounded reasoning trace — perceive→…→reflect — fully inspectable."""
    from app.agent.trace import latest_confidence, list_traces

    traces = list_traces(session, incident.id)
    steps = [{
        "seq": t.seq, "node": t.node, "node_label": _NODE_LABEL.get(t.node, t.node.title()),
        "title": t.title, "rationale": t.rationale,
        "inputs": t.inputs, "outputs": t.outputs, "citations": t.citations,
        "confidence": t.confidence, "revision": t.revision,
        "contract_id": t.contract_id, "model_version": t.model_version,
        "prompt_version": t.prompt_version, "at": _iso(t.created_at),
    } for t in traces]
    return {
        "incident_id": incident.id,
        "provider": traces[-1].model_version if traces else None,
        "prompt_version": traces[-1].prompt_version if traces else None,
        "confidence": latest_confidence(session, incident.id),
        "step_count": len(steps),
        "steps": steps,
        "note": ("The model proposes and explains; a deterministic evaluator judges recovery and a "
                 "policy gateway authorises every action. Reasoning here never grants permissions."),
    }

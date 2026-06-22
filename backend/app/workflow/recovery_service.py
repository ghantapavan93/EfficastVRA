"""Recovery orchestrator — the durable workflow's high-level operations.

State transitions are the workflow's own responsibility (audited via the state machine). Every
*operational side effect* (request evidence, submit evidence, record approval, reopen, publish,
create knowledge) is routed through the Agent Action Gateway so it is authorised, classified,
idempotent, and audited.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from app.adapters.efficast_port import EfficastPort
from app.adapters.synthetic import SyntheticEfficastPort
from app.auth import Principal, agent_principal
from app.domain.base import utcnow
from app.domain.enums import (
    ApprovalStatus,
    AuditEventType,
    InterventionStatus,
    LotDisposition,
    Role,
    Severity,
    WorkflowState,
)
from app.domain.models import (
    AgentReasoningTrace,
    ApprovalRequirement,
    Component,
    Incident,
    Intervention,
    InventoryPart,
    MaiaAlert,
    MaterialLot,
    RecoveryContract,
    Technician,
)
from app.agent.graph import RecoveryAgentGraph
from app.agent.trace import latest_confidence
from app.gateway import execute as gateway_execute
from app.reasoning import get_reasoning_provider
from app.seed.northstar import IDS
from app.services import cycle_engine
from app.services.evaluator import EvaluationResult, evaluate
from app.services.evidence import missing_required
from app.services.policy import should_reopen
from app.services.windows import open_window
from app.workflow.audit import publish_outbox, record_audit
from app.workflow.contract_builder import persist_contract
from app.workflow.state_machine import transition


class WorkflowError(Exception):
    def __init__(self, message: str, *, code: str = "workflow_error", status_code: int = 409):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class RecoveryService:
    def __init__(self, session: Session, *, port: Optional[EfficastPort] = None, reasoning=None):
        self.session = session
        self.port = port or SyntheticEfficastPort(session)
        self.reasoning = reasoning or get_reasoning_provider()

    # ── helpers ───────────────────────────────────────────────────────────────
    def _agent(self, incident: Incident) -> Principal:
        return agent_principal(incident.plant_id, incident.tenant_id)

    def _contract(self, incident: Incident) -> RecoveryContract:
        c = self.session.get(RecoveryContract, incident.current_contract_id)
        if c is None:
            raise WorkflowError("incident has no active contract")
        return c

    def _current_intervention(self, incident: Incident) -> Intervention:
        itvs = self.session.exec(
            select(Intervention).where(Intervention.incident_id == incident.id)
            .order_by(Intervention.sequence.desc())  # type: ignore[attr-defined]
        ).all()
        if not itvs:
            raise WorkflowError("no intervention to verify")
        return itvs[0]

    def _gw(self, incident, tool, args, principal, *, idem=None):
        return gateway_execute(
            self.session, tool_name=tool, raw_args=args, principal=principal,
            correlation_id=incident.correlation_id, incident_id=incident.id,
            idempotency_key=idem, port=self.port, reasoning=self.reasoning,
        )

    def _graph(self) -> RecoveryAgentGraph:
        return RecoveryAgentGraph(self.session, port=self.port, reasoning=self.reasoning)

    # ── front of the loop: MAIA alert → triage → proposed intervention ──────────
    def triage_from_alert(self, alert) -> Incident:
        """Ingest a MAIA alert, run the agent's triage/diagnosis, and create an incident with a
        *proposed* intervention awaiting human acceptance. Idempotent on the alert id."""
        dedupe = f"alert-{alert.id}"
        existing = self.session.exec(
            select(Incident).where(Incident.dedupe_key == dedupe)
        ).first()
        if existing is not None:
            return existing  # idempotent: one alert → one incident

        from app.domain.models import Machine

        machine = self.session.get(Machine, alert.machine_id)
        try:
            severity = Severity(alert.severity)
        except ValueError:
            severity = Severity.S2
        incident = Incident(
            id=f"INC-{alert.id.split('-')[-1]}",
            tenant_id=machine.tenant_id,
            plant_id=machine.plant_id,
            machine_id=alert.machine_id,
            order_id=alert.order_id,
            correlation_id=f"cor-{alert.id}",
            dedupe_key=dedupe,
            source_event_id=alert.id,
            origin_alert_id=alert.id,
            title=f"{machine.name} fault {alert.fault_code or ''} (MAIA {alert.id})".strip(),
            severity=severity,
            state=WorkflowState.ALERT_TRIAGED,
            fault_code=alert.fault_code,
            opened_at=utcnow(),
        )
        self.session.add(incident)
        self.session.flush()
        record_audit(self.session, type=AuditEventType.ALERT_INGESTED,
                     correlation_id=incident.correlation_id, actor=self.reasoning.id, role=Role.AGENT,
                     summary=f"Ingested MAIA alert {alert.id} → incident {incident.id}",
                     incident_id=incident.id, plant_id=incident.plant_id,
                     detail={"alert_id": alert.id, "kind": alert.kind})

        # Agent triages + proposes (records its reasoning trace).
        diagnosis = self._graph().triage(incident, alert)
        rec = diagnosis["recommended_intervention"]
        proposal = Intervention(
            tenant_id=incident.tenant_id, plant_id=incident.plant_id, incident_id=incident.id,
            machine_id=incident.machine_id, component_id=rec.get("component_id"),
            sequence=1, kind=rec["kind"], title=rec["title"], description=rec["description"],
            hypothesis=rec.get("hypothesis", ""), status=InterventionStatus.PROPOSED,
            proposed_at=utcnow(),
        )
        self.session.add(proposal)
        self.session.flush()
        transition(self.session, incident, WorkflowState.INTERVENTION_PROPOSED,
                   actor=self.reasoning.id, role=Role.AGENT,
                   reason=f"agent proposed: {rec['title']}")
        record_audit(self.session, type=AuditEventType.DIAGNOSIS_PROPOSED,
                     correlation_id=incident.correlation_id, actor=self.reasoning.id, role=Role.AGENT,
                     summary=f"Diagnosis proposed: {rec['title']} (awaiting human acceptance)",
                     incident_id=incident.id, detail={"diagnosis": diagnosis},
                     model_version=self.reasoning.id, prompt_version=self.reasoning.prompt_version)
        self.port.acknowledge_alert(alert.id, incident_id=incident.id)
        self.session.flush()
        return incident

    def accept_diagnosis(self, incident: Incident, principal: Principal) -> None:
        """A human (supervisor) accepts the agent's diagnosis; the proposed intervention is recorded.
        The agent never accepts its own diagnosis — this is the human-in-the-loop gate."""
        if incident.state != WorkflowState.INTERVENTION_PROPOSED:
            raise WorkflowError(f"cannot accept diagnosis from state {incident.state.value}")
        intervention = self._current_intervention(incident)
        tech = self.session.get(Technician, IDS["tech_lang"])
        intervention.technician_id = tech.id if tech else None
        intervention.status = InterventionStatus.COMPLETED
        intervention.completed_at = utcnow()
        self.session.add(intervention)
        transition(self.session, incident, WorkflowState.INTERVENTION_RECORDED,
                   actor=principal.username, role=principal.role,
                   reason="supervisor accepted diagnosis; intervention recorded")
        record_audit(self.session, type=AuditEventType.DIAGNOSIS_ACCEPTED,
                     correlation_id=incident.correlation_id, actor=principal.username, role=principal.role,
                     summary=f"Diagnosis accepted; {intervention.title} recorded",
                     incident_id=incident.id)
        self.session.flush()

    # ── operations ────────────────────────────────────────────────────────────
    def draft_contract(self, incident: Incident) -> RecoveryContract:
        if incident.state != WorkflowState.INTERVENTION_RECORDED:
            raise WorkflowError(f"cannot draft from state {incident.state.value}")
        intervention = self._current_intervention(incident)
        # Run the bounded agent graph: perceive→retrieve→hypothesize→draft→self_critique→decide.
        # It records an inspectable reasoning trace; the deterministic evaluator stays authoritative.
        draft = self._graph().draft(incident, intervention)
        spec = draft.spec
        contract = persist_contract(self.session, incident, spec, drafted_by=self.reasoning.id)
        contract.status = "draft"
        # Backfill the contract id onto the draft-phase traces (recorded before the contract existed).
        for t in self.session.exec(
            select(AgentReasoningTrace)
            .where(AgentReasoningTrace.incident_id == incident.id)
            .where(AgentReasoningTrace.contract_id.is_(None))  # type: ignore[union-attr]
        ).all():
            t.contract_id = contract.id
            self.session.add(t)
        transition(self.session, incident, WorkflowState.RECOVERY_CONTRACT_DRAFTED,
                   actor=self.reasoning.id, role=Role.AGENT,
                   reason=f"contract {contract.contract_no} v{contract.version} drafted")
        record_audit(self.session, type=AuditEventType.CONTRACT_DRAFTED,
                     correlation_id=incident.correlation_id, actor=self.reasoning.id, role=Role.AGENT,
                     summary=f"Drafted recovery contract {contract.contract_no} v{contract.version}",
                     incident_id=incident.id, contract_id=contract.id,
                     model_version=self.reasoning.id, prompt_version=self.reasoning.prompt_version)
        # Agent requests the missing required evidence (through the gateway).
        self._gw(incident, "request_missing_evidence", {"contract_id": contract.id},
                 self._agent(incident), idem=f"req-evi-{contract.id}")
        self.session.flush()
        return contract

    def review_contract(self, incident: Incident, principal: Principal) -> None:
        transition(self.session, incident, WorkflowState.RECOVERY_CONTRACT_REVIEWED,
                   actor=principal.username, role=principal.role, reason="contract reviewed")
        transition(self.session, incident, WorkflowState.AWAITING_REQUIRED_EVIDENCE,
                   actor="system", role=Role.SYSTEM, reason="awaiting required evidence")
        self.session.flush()

    def submit_evidence(self, incident: Incident, principal: Principal, *, requirement_id: str,
                        value_num=None, value_text="", unit="", source="", evidence_timestamp=None,
                        file_ref=None, idem=None):
        return self._gw(incident, "submit_evidence", {
            "requirement_id": requirement_id, "value_num": value_num, "value_text": value_text,
            "unit": unit, "source": source,
            "evidence_timestamp": evidence_timestamp.isoformat() if evidence_timestamp else None,
            "file_ref": file_ref,
        }, principal, idem=idem or f"evi-{requirement_id}-{principal.username}")

    def record_approval(self, incident: Incident, principal: Principal, *, requirement_id: str,
                        decision="approve", reason="", idem=None):
        return self._gw(incident, "record_human_approval", {
            "requirement_id": requirement_id, "decision": decision, "reason": reason,
        }, principal, idem=idem or f"appr-{requirement_id}")

    def start_monitoring(self, incident: Incident) -> None:
        contract = self._contract(incident)
        missing = missing_required(self.session, contract.id, "monitoring")
        if missing:
            raise WorkflowError(
                f"cannot start monitoring: missing evidence {[m.key for m in missing]}",
                code="missing_evidence",
            )
        review = self.session.exec(
            select(ApprovalRequirement).where(ApprovalRequirement.contract_id == contract.id)
            .where(ApprovalRequirement.key == "contract_review")
        ).first()
        if review is not None and review.status != ApprovalStatus.APPROVED:
            raise WorkflowError("cannot start monitoring: recovery contract not approved",
                                code="approval_required")
        from app.domain.models import Machine

        m = self.session.get(Machine, incident.machine_id)
        transition(self.session, incident, WorkflowState.READY_FOR_MONITORING,
                   actor="system", role=Role.SYSTEM, reason="evidence + approval satisfied")
        transition(self.session, incident, WorkflowState.MONITORING_RECOVERY,
                   actor="system", role=Role.SYSTEM, reason="recovery monitoring started")
        contract.status = "active"
        self.session.add(contract)
        open_window(self.session, incident_id=incident.id, contract=contract, sequence=1,
                    required_stable_cycles=30, baseline=m.baseline)
        self.session.flush()

    def advance(self, incident: Incident, n: int = 1) -> dict:
        contract = self._contract(incident)
        if incident.state != WorkflowState.MONITORING_RECOVERY:
            raise WorkflowError(f"cannot advance cycles from state {incident.state.value}")
        graph = self._graph()
        cycles = []
        outcome = "monitoring"
        last_result = None
        last_cycle = None
        for _ in range(n):
            _obs, result = cycle_engine.advance_cycle(self.session, self.port, contract)
            last_result, last_cycle = result, _obs.cycle_index
            cycles.append({"cycle": _obs.cycle_index, "verdict": result.verdict,
                           "stable_streak": result.stable_streak, "fault": _obs.fault_code,
                           "vibration": _obs.vibration, "temperature": _obs.temperature,
                           "cycle_time": _obs.cycle_time})
            if result.verdict == "violated" and should_reopen(contract, result):
                # Agent reflects (reasoning) *before* the gateway reopens (action).
                graph.observe(incident, contract, result, cycle=_obs.cycle_index)
                self._gw(incident, "reopen_incident", {"incident_id": incident.id},
                         self._agent(incident), idem=f"reopen-{incident.id}-{incident.reopened_count}")
                self.session.refresh(incident)
                outcome = "reopened"
                break
            if result.verdict == "verified":
                graph.observe(incident, contract, result, cycle=_obs.cycle_index)
                self.finalize(incident)
                outcome = "verified"
                break
        if outcome == "monitoring" and last_result is not None:
            graph.observe(incident, contract, last_result, cycle=last_cycle)
        self.session.flush()
        return {"outcome": outcome, "cycles": cycles, "state": incident.state.value,
                "confidence": latest_confidence(self.session, incident.id)}

    def approve_contingency(self, incident: Incident, principal: Principal) -> None:
        contract = self._contract(incident)
        req = self.session.exec(
            select(ApprovalRequirement).where(ApprovalRequirement.contract_id == contract.id)
            .where(ApprovalRequirement.key == "release_contingency")
        ).first()
        if req is None:
            raise WorkflowError("no contingency approval requirement")
        self.record_approval(incident, principal, requirement_id=req.id,
                             reason="release bearing-replacement contingency")
        # Apply grants: reserve bearing, assign technician, mark intervention in progress.
        part = self.session.exec(
            select(InventoryPart).where(InventoryPart.part_number == IDS["bearing_part"])
        ).first()
        if part is not None:
            part.reserved += 1
            self.session.add(part)
        contingency = self._current_intervention(incident)
        tech = self.session.get(Technician, IDS["tech_ortiz"])
        contingency.technician_id = tech.id if tech else None
        contingency.status = InterventionStatus.IN_PROGRESS
        self.session.add(contingency)
        transition(self.session, incident, WorkflowState.CONTINGENCY_IN_PROGRESS,
                   actor=principal.username, role=principal.role,
                   reason="contingency approved; bearing reserved; technician assigned")
        self.session.flush()

    def complete_contingency(self, incident: Incident) -> None:
        contract = self._contract(incident)
        missing = missing_required(self.session, contract.id, "monitoring")
        if missing:
            raise WorkflowError(
                f"cannot complete contingency: missing evidence {[m.key for m in missing]}",
                code="missing_evidence",
            )
        contingency = self._current_intervention(incident)
        contingency.status = InterventionStatus.COMPLETED
        contingency.completed_at = utcnow()
        self.session.add(contingency)
        from app.domain.models import Machine

        m = self.session.get(Machine, incident.machine_id)
        # Reset the machine's live readings to baseline-ish before the 2nd window starts.
        m.live = {**m.baseline, "vibration": m.baseline.get("vibration_mm_s"),
                  "temperature": m.baseline.get("temp_c"), "cycle_time": m.baseline.get("cycle_time_s"),
                  "scrap_pct": m.baseline.get("scrap_pct"), "fault_code": None,
                  "at": utcnow().isoformat(), "freshness_s": 2}
        self.session.add(m)
        transition(self.session, incident, WorkflowState.READY_FOR_MONITORING,
                   actor="system", role=Role.SYSTEM, reason="contingency complete; evidence satisfied")
        transition(self.session, incident, WorkflowState.MONITORING_RECOVERY,
                   actor="system", role=Role.SYSTEM, reason="second recovery window started")
        contract.status = "active"
        self.session.add(contract)
        open_window(self.session, incident_id=incident.id, contract=contract, sequence=2,
                    required_stable_cycles=30, baseline=m.baseline)
        self.session.flush()

    def finalize(self, incident: Incident) -> None:
        contract = self._contract(incident)
        result = evaluate(self.session, contract)
        if result.verdict != "verified":
            raise WorkflowError("cannot finalize: recovery not verified")
        # Release held lots (quality already approved as part of 'verified').
        lots = self.session.exec(
            select(MaterialLot).where(MaterialLot.order_id == incident.order_id)
        ).all() if incident.order_id else []
        for lot in lots:
            if lot.disposition == LotDisposition.HOLD:
                lot.disposition = LotDisposition.RELEASED
                self.session.add(lot)
        contract.status = "fulfilled"
        self.session.add(contract)
        transition(self.session, incident, WorkflowState.VERIFIED_RECOVERY,
                   actor="system", role=Role.SYSTEM, reason="all conditions passed; quality released")
        incident.closed_at = utcnow()
        from app.domain.enums import OutcomeType

        incident.outcome_type = OutcomeType.VERIFIED
        incident.outcome_summary = result.summary
        self.session.add(incident)
        record_audit(self.session, type=AuditEventType.RECOVERY_VERIFIED,
                     correlation_id=incident.correlation_id, actor="system", role=Role.SYSTEM,
                     summary="Verified recovery published.", incident_id=incident.id,
                     contract_id=contract.id, detail={"stable_cycles": result.stable_streak})
        self._gw(incident, "publish_recovery_decision",
                 {"incident_id": incident.id, "decision_type": "verified_recovery",
                  "summary": result.summary}, self._agent(incident),
                 idem=f"publish-verified-{incident.id}")
        self._gw(incident, "create_knowledge_candidate", {"incident_id": incident.id},
                 self._agent(incident), idem=f"knowledge-{incident.id}")
        self.session.flush()

    def current_evaluation(self, incident: Incident) -> EvaluationResult:
        return evaluate(self.session, self._contract(incident))

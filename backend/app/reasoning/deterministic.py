"""DeterministicReasoningProvider — carries the entire demo with no API key.

Every method is grounded in the database + the deterministic contract templates + filtered retrieval.
It explains and structures; it never decides recovery and never grants permissions.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.domain.contract import RecoveryContractSpec
from app.domain.models import EvidenceRequirement, Incident, Intervention, RecoveryContract
from app.rag import detect_conflicts, search
from app.reasoning.base import Diagnosis, ReasoningProvider
from app.seed.northstar import IDS
from app.services.contract_templates import build_v1_spec, build_v2_spec
from app.services.evaluator import EvaluationResult
from app.services.evidence import requirement_satisfied


class DeterministicReasoningProvider(ReasoningProvider):
    id = "DeterministicReasoningProvider"
    prompt_version = "deterministic-1"

    # 1. Extract recovery requirements (draft the contract spec) ────────────────
    def extract_recovery_requirements(
        self, *, incident: Incident, intervention: Intervention, retrieved: list[dict]
    ) -> RecoveryContractSpec:
        contract_no = IDS["contract_no"]
        if intervention.sequence >= 2 or intervention.kind == "bearing_replacement":
            return build_v2_spec(incident.id, intervention.id, contract_no)
        return build_v1_spec(incident.id, intervention.id, contract_no)

    # 2. Identify missing evidence ──────────────────────────────────────────────
    def identify_missing_evidence(self, *, session: Session, contract: RecoveryContract) -> list[dict]:
        reqs = session.exec(
            select(EvidenceRequirement).where(EvidenceRequirement.contract_id == contract.id)
        ).all()
        missing: list[dict] = []
        for r in reqs:
            if not requirement_satisfied(session, r):
                missing.append({
                    "key": r.key, "label": r.label, "kind": r.kind.value,
                    "assigned_role": r.assigned_role.value, "reason": r.reason_required,
                    "required_before": r.required_before, "status": r.status.value,
                    "blocks_conditions": r.blocks_conditions,
                })
        return missing

    # 3. Compare historical interventions ──────────────────────────────────────
    def compare_historical_interventions(self, *, session: Session, incident: Incident) -> dict:
        hist = session.exec(
            select(Incident)
            .where(Incident.historical == True)  # noqa: E712
            .where(Incident.fault_code == incident.fault_code)
        ).first()
        citations = search(session, "F27 recurrence after alignment bearing replacement",
                           machine_model="CDX-220", component="bearing", k=2)
        if hist is None:
            return {"match": False, "note": "No comparable historical incident found.", "citations": []}
        return {
            "match": True,
            "historical_incident_id": hist.id,
            "similarity": "Same fault (F27) on a sibling CDX-220 drive after a corrective action.",
            "what_happened": hist.outcome_summary,
            "recommended_contingency": "drive-end bearing replacement (BR-6205)",
            "confidence": "high",
            "citations": [{"document_id": c.document_id, "section": c.section,
                           "excerpt": c.content[:160], "approval_status": c.approval_status}
                          for c in citations],
        }

    # 4. Detect document conflicts ──────────────────────────────────────────────
    def detect_document_conflicts(
        self, *, session: Session, query: str, machine_model: str, component: str
    ) -> dict:
        return detect_conflicts(session, query, machine_model=machine_model, component=component)

    # 4b. Diagnose an alert (advisory) ──────────────────────────────────────────
    def diagnose_alert(
        self, *, incident: Incident, snapshot, signals: dict, retrieved: list[dict], history: dict
    ) -> Diagnosis:
        """Grounded, reproducible diagnosis of a drivetrain alert — the deterministic baseline the
        hosted (Claude) provider falls back to. Identical content to the historical demo behaviour."""
        days = signals.get("motor_replaced_days_ago", 9)
        root_causes = [{
            "cause": f"Coupling misalignment introduced during the motor replacement {days} days ago",
            "likelihood": "primary",
            "basis": "recent motor swap + rising vibration + F27 recurrence",
        }]
        if history.get("match"):
            root_causes.append({
                "cause": "Drive-end bearing degradation",
                "likelihood": "latent",
                "basis": f"historical {history.get('historical_incident_id')}: alignment did not hold and "
                         "F27 recurred — root cause was the bearing",
            })
        return Diagnosis(
            degradation_kind="mechanical_drivetrain_fault",
            classification_rationale=(
                "Rising vibration with a repeating fault and worsening cycle time/scrap points to the "
                "motor-coupling-bearing drivetrain rather than a process or quality cause."),
            root_causes=root_causes,
            recommended_kind="coupling_alignment",
            recommended_title="Coupling-alignment correction",
            recommended_description=(
                "Correct motor-drive coupling alignment disturbed during the recent motor replacement, "
                "then verify recovery before closing."),
            recommended_hypothesis=(
                "Vibration/F27 caused by coupling misalignment introduced during motor replacement."),
            contingency={"kind": "bearing_replacement",
                         "note": "If F27 recurs in the verification window, replace drive-end bearing BR-6205."},
            summary=(
                "Most likely coupling misalignment from the recent motor replacement; verify a "
                "coupling-alignment correction, watching for the bearing-degradation pattern from "
                f"{history.get('historical_incident_id', 'history')}."),
            diagnostic_confidence=0.7,
            source="deterministic",
        )

    # 5. Explain recovery failure ───────────────────────────────────────────────
    def explain_recovery_failure(
        self, *, contract: RecoveryContract, result: EvaluationResult
    ) -> dict:
        violated = result.violated_keys
        fault = "fault_f27" in violated
        headline = (
            f"Recovery Contract {contract.contract_no} v{contract.version} violated"
            + (" — fault F27 recurred." if fault else ".")
        )
        detail = (
            "The intervention's work order was completed and early cycles looked like recovery, but "
            + ("the originating fault F27 recurred during the verification window. A completed work "
               "order is not proof of recovery." if fault else
               f"these conditions failed: {', '.join(violated)}.")
        )
        return {
            "headline": headline,
            "detail": detail,
            "violated": violated,
            "recommendation": ("Reopen the incident and activate the drive-end bearing-replacement "
                               "contingency (BR-6205), consistent with historical incident INC-1990."),
            "human_message": "Work completed. Recovery not proven. Incident reopened automatically.",
        }

    # 6. Generate handoff summary ───────────────────────────────────────────────
    def generate_handoff_summary(self, *, session: Session, incident: Incident) -> dict:
        contract = (
            session.get(RecoveryContract, incident.current_contract_id)
            if incident.current_contract_id else None
        )
        line = (
            f"Incident {incident.id} on {incident.machine_id} is {incident.state.value}. "
            f"Reopened {incident.reopened_count}x. "
        )
        if contract:
            line += f"Active contract {contract.contract_no} v{contract.version} ({contract.status}). "
        return {
            "summary": line + "Verified-recovery verification in progress; quality release gated on a "
                              "quality engineer.",
            "state": incident.state.value,
            "owner_next": "supervisor" if "APPROVAL" in incident.state.value else "agent",
        }

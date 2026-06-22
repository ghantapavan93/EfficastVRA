"""Reopen-with-contingency: the cycle-17 branch.

When the verification window is violated, this preserves the failed intervention + its evidence,
drives the failure→reopen state transitions, creates the bearing-replacement contingency
intervention, drafts contract V2, and parks the incident at ``CONTINGENCY_AWAITING_APPROVAL`` for a
supervisor. Nothing is deleted — the first intervention remains in history.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session

from app.adapters.efficast_port import EfficastPort
from app.domain.base import utcnow
from app.domain.enums import (
    AuditEventType,
    InterventionStatus,
    Role,
    WorkflowState,
)
from app.domain.models import Incident, Intervention, RecoveryContract
from app.services.contract_templates import build_v2_spec
from app.services.windows import get_active_window
from app.seed.northstar import IDS
from app.workflow.audit import publish_outbox, record_audit
from app.workflow.contract_builder import persist_contract
from app.workflow.state_machine import transition


def reopen_with_contingency(
    session: Session,
    port: EfficastPort,
    incident: Incident,
    failed_contract: RecoveryContract,
    *,
    violated_keys: list[str],
    actor: str = "agent",
    role: Role = Role.AGENT,
) -> RecoveryContract:
    cid = incident.correlation_id

    # 1. Mark V1 contract violated; fail its window.
    failed_contract.status = "violated"
    session.add(failed_contract)
    win = get_active_window(session, failed_contract)
    if win is not None:
        win.status = "failed"
        win.closed_at = utcnow()
        session.add(win)
    record_audit(
        session, type=AuditEventType.CONTRACT_VIOLATED, correlation_id=cid, actor=actor, role=role,
        summary=f"Recovery contract {failed_contract.contract_no} v{failed_contract.version} violated: "
                f"{', '.join(violated_keys)}.",
        incident_id=incident.id, contract_id=failed_contract.id,
        detail={"violated_keys": violated_keys, "verdict": "violated"},
    )

    # 2. Failure → reopen state chain (preserves history; automatic, agent-driven).
    if incident.state == WorkflowState.MONITORING_RECOVERY:
        transition(session, incident, WorkflowState.RECOVERY_CONDITION_FAILED, actor=actor, role=role,
                   reason="fault F27 recurred during verification window")
    if incident.state == WorkflowState.RECOVERY_CONDITION_FAILED:
        transition(session, incident, WorkflowState.RECOVERY_FAILED, actor=actor, role=role,
                   reason="work completed but recovery not proven")
    transition(session, incident, WorkflowState.INCIDENT_REOPENED, actor=actor, role=role,
               reason="incident reopened automatically — recovery not verified")
    incident.reopened_count += 1
    session.add(incident)

    # 3. Create the bearing-replacement contingency intervention (sequence 2, proposed).
    contingency = Intervention(
        tenant_id=incident.tenant_id, plant_id=incident.plant_id, incident_id=incident.id,
        machine_id=incident.machine_id, component_id=IDS["bearing"], sequence=2,
        kind="bearing_replacement", title="Drive-end bearing replacement (BR-6205)",
        description="Replace drive-end bearing BR-6205; alignment correction did not hold (F27 recurred).",
        hypothesis="Root cause is drive-end bearing degradation, not coupling misalignment.",
        status=InterventionStatus.PROPOSED, proposed_at=utcnow(),
    )
    session.add(contingency)
    session.flush()

    # 4. Draft contract V2 (bearing) and link supersession.
    spec = build_v2_spec(incident.id, contingency.id, failed_contract.contract_no)
    v2 = persist_contract(session, incident, spec, drafted_by="DeterministicReasoningProvider")
    failed_contract.superseded_by = v2.id
    session.add(failed_contract)

    # 5. Park at CONTINGENCY_AWAITING_APPROVAL (supervisor must approve the contingency).
    transition(session, incident, WorkflowState.CONTINGENCY_AWAITING_APPROVAL, actor=actor, role=role,
               reason="bearing-replacement contingency drafted; awaiting supervisor approval")
    record_audit(
        session, type=AuditEventType.INCIDENT_REOPENED, correlation_id=cid, actor=actor, role=role,
        summary="Incident reopened; bearing-replacement contingency (contract v2) awaiting approval.",
        incident_id=incident.id, contract_id=v2.id,
        detail={"superseded_contract": failed_contract.id, "new_contract": v2.id},
    )
    publish_outbox(session, topic="recovery.reopened",
                   payload={"incident_id": incident.id, "contract": v2.id, "reason": violated_keys},
                   correlation_id=cid)
    session.flush()
    return v2


def reopen_optional(*args, **kwargs) -> Optional[RecoveryContract]:  # convenience alias
    return reopen_with_contingency(*args, **kwargs)

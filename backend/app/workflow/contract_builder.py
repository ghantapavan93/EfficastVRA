"""Persist a structured contract spec into evaluable, queryable rows.

The reasoning layer hands us a :class:`RecoveryContractSpec`; this builder writes the
:class:`RecoveryContract` plus normalised condition / evidence-requirement / approval-requirement
rows, and links the contract to its incident. Deterministic and side-effect-contained.
"""

from __future__ import annotations

from sqlmodel import Session

from app.domain.contract import RecoveryContractSpec
from app.domain.enums import CompareOp
from app.domain.models import (
    ApprovalRequirement,
    EvidenceRequirement,
    Incident,
    RecoveryCondition,
    RecoveryContract,
)


def persist_contract(session: Session, incident: Incident, spec: RecoveryContractSpec,
                     *, drafted_by: str = "DeterministicReasoningProvider") -> RecoveryContract:
    # Deterministic guard against a vacuous contract: an incident with a known fault MUST be verified by a
    # NOT_RECUR condition bound to *that* fault. Otherwise verification would pass while the originating
    # fault is still firing (the false-closure the whole product exists to prevent). The agent drafts the
    # contract, but this gate — not the LLM — refuses a spec that cannot detect the relapse it's verifying.
    if incident.fault_code:
        tests_fault = any(
            c.op == CompareOp.NOT_RECUR and (c.fault_code or "") == incident.fault_code
            for c in spec.all_conditions()
        )
        if not tests_fault:
            raise ValueError(
                f"contract does not test non-recurrence of the originating fault {incident.fault_code!r}; "
                "refusing to persist a contract that cannot detect a relapse"
            )

    contract = RecoveryContract(
        tenant_id=incident.tenant_id,
        plant_id=incident.plant_id,
        incident_id=incident.id,
        intervention_id=spec.intervention_id,
        contract_no=spec.contract_no,
        version=spec.version,
        status="draft",
        policy_version=spec.policy_version,
        workflow_version=spec.workflow_version,
        objective=spec.objective,
        drafted_by=drafted_by,
        verification_window=spec.verification_window.model_dump(),
        closure_policy=spec.closure_policy.model_dump(),
        reopening_policy=spec.reopening_policy.model_dump(),
        escalation_policy=spec.escalation_policy.model_dump(),
        spec=spec.model_dump(mode="json"),
    )
    session.add(contract)
    session.flush()

    cond_by_key: dict[str, RecoveryCondition] = {}
    for c in spec.all_conditions():
        row = RecoveryCondition(
            tenant_id=incident.tenant_id,
            contract_id=contract.id,
            incident_id=incident.id,
            kind=c.kind,
            key=c.key,
            label=c.label,
            op=c.op,
            threshold=c.threshold,
            unit=c.unit,
            baseline=c.baseline,
            sensor_tag=c.sensor_tag,
            fault_code=c.fault_code,
            deadline_kind=c.deadline_kind,
            deadline_value=c.deadline_value,
            window_cycles=c.window_cycles,
            policy_ref=c.policy_ref,
            detail={"rationale": c.rationale},
        )
        session.add(row)
        cond_by_key[c.key] = row
    session.flush()

    for e in spec.evidence_requirements:
        condition_id = None
        for blocked_key in e.blocks_conditions:
            if blocked_key in cond_by_key:
                condition_id = cond_by_key[blocked_key].id
                break
        session.add(EvidenceRequirement(
            tenant_id=incident.tenant_id,
            contract_id=contract.id,
            incident_id=incident.id,
            condition_id=condition_id,
            kind=e.kind,
            key=e.key,
            label=e.label,
            assigned_role=e.assigned_role,
            reason_required=e.reason_required,
            required_before=e.required_before,
            freshness_max_s=e.freshness_max_s,
            blocks_conditions=e.blocks_conditions,
            validity_rule=e.validity_rule,
        ))

    for a in spec.approval_requirements:
        session.add(ApprovalRequirement(
            tenant_id=incident.tenant_id,
            contract_id=contract.id,
            incident_id=incident.id,
            key=a.key,
            label=a.label,
            required_role=a.required_role,
            required_before=a.required_before,
            grants=a.grants,
            denies=a.denies,
            policy_ref=a.policy_ref,
        ))

    incident.current_contract_id = contract.id
    session.add(incident)
    session.flush()
    return contract

"""Deterministic Recovery Contract specs for the Northstar scenario.

These build the structured :class:`RecoveryContractSpec` for V1 (coupling alignment) and V2 (bearing
replacement). The reasoning layer *drafts/explains* a contract; this is the deterministic ground
truth it must agree with. Thresholds here are PROTOTYPE_ASSUMPTIONs chosen for narrative clarity,
not copied from any product or standard (see docs/EFFICAST_EVIDENCE_LEDGER.md).
"""

from __future__ import annotations

from app.config import get_settings
from app.domain.contract import (
    ApprovalReqSpec,
    ClosurePolicySpec,
    ConditionSpec,
    EscalationPolicySpec,
    EvidenceReqSpec,
    RecoveryContractSpec,
    ReopeningPolicySpec,
    VerificationWindowSpec,
)
from app.domain.enums import CompareOp, ConditionKind, EvidenceKind, Role

_settings = get_settings()

# Actions an approval explicitly does NOT authorise — shown verbatim in the approval UI.
PROHIBITED_GRANTS = [
    "machine_start",
    "machine_stop",
    "machine_restart",
    "plc_modification",
    "setpoint_modification",
    "alarm_bypass",
    "interlock_bypass",
    "loto_confirmation",
    "safety_certification",
    "automatic_quality_release",
]

REQUIRED_STABLE_CYCLES = 30
BASELINE = {"vibration_mm_s": 3.1, "temp_c": 63.0, "cycle_time_s": 12.2, "scrap_pct": 1.6}


def _machine_conditions(contract_no: str) -> list[ConditionSpec]:
    return [
        ConditionSpec(
            key="vibration_rms", kind=ConditionKind.MACHINE, label="Vibration RMS",
            op=CompareOp.LTE, threshold=4.0, unit="mm/s", baseline=BASELINE["vibration_mm_s"],
            sensor_tag="VIB-L4-01", deadline_kind="cycles", deadline_value=10,
            policy_ref=f"{contract_no} · C1",
            rationale="Coupling/bearing health: RMS must fall below 4.0 mm/s within 10 cycles.",
        ),
        ConditionSpec(
            key="temperature_trend", kind=ConditionKind.MACHINE, label="Temperature trend",
            op=CompareOp.DECLINING, unit="°C", baseline=BASELINE["temp_c"], sensor_tag="TMP-L4-01",
            deadline_kind="minutes", deadline_value=15, policy_ref=f"{contract_no} · C2",
            rationale="Drive temperature must begin declining within 15 minutes of restart.",
        ),
        ConditionSpec(
            key="fault_f27", kind=ConditionKind.MACHINE, label="Fault F27 non-recurrence",
            op=CompareOp.NOT_RECUR, fault_code="F27", deadline_kind="window",
            policy_ref=f"{contract_no} · C3",
            rationale="The originating fault must not recur during the verification window.",
        ),
        ConditionSpec(
            key="cycle_time", kind=ConditionKind.MACHINE, label="Cycle time vs baseline",
            op=CompareOp.WITHIN_PCT, threshold=0.05, unit="s", baseline=BASELINE["cycle_time_s"],
            sensor_tag="CYC-L4-01", deadline_kind="cycles", deadline_value=10,
            policy_ref=f"{contract_no} · C4",
            rationale="Cycle time must return within 5% of the 12.2 s baseline.",
        ),
    ]


def _production_conditions(contract_no: str) -> list[ConditionSpec]:
    return [
        ConditionSpec(
            key="scrap", kind=ConditionKind.PRODUCTION, label="Scrap rate",
            op=CompareOp.LT, threshold=2.0, unit="%", baseline=BASELINE["scrap_pct"],
            deadline_kind="window", policy_ref=f"{contract_no} · C5",
            rationale="Scrap must return below 2.0%.",
        ),
        ConditionSpec(
            key="stable_cycles", kind=ConditionKind.PRODUCTION, label="Consecutive stable cycles",
            op=CompareOp.COUNT_GTE, threshold=REQUIRED_STABLE_CYCLES, unit="cycles",
            window_cycles=REQUIRED_STABLE_CYCLES, deadline_kind="window",
            policy_ref=f"{contract_no} · C6",
            rationale="30 consecutive stable cycles are required before closure.",
        ),
    ]


def _quality_conditions(contract_no: str) -> list[ConditionSpec]:
    return [
        ConditionSpec(
            key="first_piece", kind=ConditionKind.QUALITY, label="First-piece inspection",
            op=CompareOp.EQ, threshold=1.0, deadline_kind="window",
            policy_ref=f"{contract_no} · C7",
            rationale="First-piece quality inspection must pass before quality release.",
        ),
    ]


def _quality_release_approval(contract_no: str) -> ApprovalReqSpec:
    return ApprovalReqSpec(
        key="quality_release", label="Release quality hold",
        required_role=Role.QUALITY_ENGINEER, required_before="quality_release",
        grants=["release_quality_hold", "disposition_affected_lots"],
        denies=PROHIBITED_GRANTS, policy_ref=f"{contract_no} · A-Q",
    )


def build_v1_spec(incident_id: str, intervention_id: str, contract_no: str) -> RecoveryContractSpec:
    """V1 — verify the coupling-alignment correction."""
    return RecoveryContractSpec(
        contract_no=contract_no, version=1, incident_id=incident_id, intervention_id=intervention_id,
        objective=("Verify that the coupling-alignment correction actually recovered Packaging Line 4 "
                   "conveyor-drive on PO-2841 — not merely that the work order was completed."),
        policy_version=_settings.policy_version, workflow_version=_settings.workflow_version,
        machine_conditions=_machine_conditions(contract_no),
        production_conditions=_production_conditions(contract_no),
        quality_conditions=_quality_conditions(contract_no),
        evidence_requirements=[
            EvidenceReqSpec(
                key="post_alignment_measurement", kind=EvidenceKind.NUMERIC_MEASUREMENT,
                label="Post-alignment vibration measurement", assigned_role=Role.TECHNICIAN,
                reason_required="Confirms the alignment was actually corrected before monitoring.",
                required_before="monitoring", freshness_max_s=7200,
                validity_rule={"type": "numeric", "min": 0.0, "max": 4.5}, blocks_conditions=[],
            ),
            EvidenceReqSpec(
                key="technician_completion", kind=EvidenceKind.COMPLETION,
                label="Technician completion sign-off", assigned_role=Role.TECHNICIAN,
                reason_required="Confirms the physical work is finished and the machine is restartable.",
                required_before="monitoring", freshness_max_s=7200,
                validity_rule={"type": "present"}, blocks_conditions=[],
            ),
            EvidenceReqSpec(
                key="first_piece_quality", kind=EvidenceKind.PHOTO,
                label="First-piece quality inspection result", assigned_role=Role.QUALITY_ENGINEER,
                reason_required="First-piece must pass before any quality release.",
                required_before="quality_release", freshness_max_s=14400,
                validity_rule={"type": "pass_fail", "expect": "pass"}, blocks_conditions=["first_piece"],
            ),
        ],
        approval_requirements=[
            ApprovalReqSpec(
                key="contract_review", label="Approve recovery contract & begin monitoring",
                required_role=Role.SUPERVISOR, required_before="monitoring",
                grants=["begin_recovery_monitoring"], denies=PROHIBITED_GRANTS,
                policy_ref=f"{contract_no} · A1",
            ),
            _quality_release_approval(contract_no),
        ],
        verification_window=VerificationWindowSpec(required_stable_cycles=REQUIRED_STABLE_CYCLES,
                                                   cycle_seconds=12.2),
        closure_policy=ClosurePolicySpec(),
        reopening_policy=ReopeningPolicySpec(),
        escalation_policy=EscalationPolicySpec(),
    )


def build_v2_spec(incident_id: str, intervention_id: str, contract_no: str) -> RecoveryContractSpec:
    """V2 — the bearing-replacement contingency after V1 failed at cycle 17."""
    spec = build_v1_spec(incident_id, intervention_id, contract_no)
    spec.version = 2
    spec.objective = (
        "Verify that drive-end bearing replacement (BR-6205) recovered Packaging Line 4 conveyor-drive "
        "after the coupling-alignment correction failed (F27 recurred at cycle 17 of V1)."
    )
    # Retain all conditions; update evidence to the bearing intervention and add the contingency approval.
    spec.evidence_requirements = [
        EvidenceReqSpec(
            key="bearing_post_measurement", kind=EvidenceKind.NUMERIC_MEASUREMENT,
            label="Post-replacement vibration measurement", assigned_role=Role.TECHNICIAN,
            reason_required="Confirms bearing replacement reduced vibration before monitoring.",
            required_before="monitoring", freshness_max_s=7200,
            validity_rule={"type": "numeric", "min": 0.0, "max": 4.0}, blocks_conditions=[],
        ),
        EvidenceReqSpec(
            key="technician_completion_2", kind=EvidenceKind.COMPLETION,
            label="Bearing replacement completion sign-off", assigned_role=Role.TECHNICIAN,
            reason_required="Confirms the bearing replacement is finished.",
            required_before="monitoring", freshness_max_s=7200,
            validity_rule={"type": "present"}, blocks_conditions=[],
        ),
        EvidenceReqSpec(
            key="first_piece_quality", kind=EvidenceKind.PHOTO,
            label="First-piece quality inspection result", assigned_role=Role.QUALITY_ENGINEER,
            reason_required="First-piece must pass before any quality release.",
            required_before="quality_release", freshness_max_s=14400,
            validity_rule={"type": "pass_fail", "expect": "pass"}, blocks_conditions=["first_piece"],
        ),
    ]
    spec.approval_requirements = [
        ApprovalReqSpec(
            key="release_contingency", label="Release bearing-replacement contingency",
            required_role=Role.SUPERVISOR, required_before="contingency",
            grants=["release_contingency_work_order", "reserve_bearing_BR-6205",
                    "assign_technician", "begin_second_recovery_window"],
            denies=PROHIBITED_GRANTS, policy_ref=f"{contract_no} · A2",
        ),
        _quality_release_approval(contract_no),
    ]
    return spec

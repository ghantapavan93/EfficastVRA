"""Machine-agnostic Recovery Contract catalog.

The Recovery Contract is a *primitive*, not a hardcoded conveyor scenario. A `MachineProfile` is a
**declarative** description of what recovery means for an equipment class — its signals, thresholds,
required evidence, and approvals — and `build_contract_from_profile` instantiates a fully-valid
`RecoveryContractSpec` from it. Adding support for a new machine class is *data*, not code.

This is the same shape the deterministic evaluator already speaks (`CompareOp` over arbitrary metric
keys), so any profile defined here is verified, reopened, and closed by the existing engine without
modification. The Northstar conveyor keeps its hand-tuned template in `contract_templates.py`; it is
also represented here (`CONVEYOR_DRIVE`) so the catalog and the live path provably agree.

Thresholds are PROTOTYPE_ASSUMPTIONs for narrative clarity (see docs/EFFICAST_EVIDENCE_LEDGER.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field

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
from app.services.contract_templates import PROHIBITED_GRANTS

_settings = get_settings()


# ── declarative profile types ────────────────────────────────────────────────
@dataclass
class ProfileCondition:
    key: str
    kind: ConditionKind
    label: str
    op: CompareOp
    unit: str = ""
    threshold: float | None = None
    baseline_key: str | None = None      # resolves against the profile/incident baseline
    sensor_tag: str | None = None
    fault_code: str | None = None
    deadline_kind: str = "window"        # cycles | minutes | window
    deadline_value: float | None = None
    rationale: str = ""


@dataclass
class ProfileEvidence:
    key: str
    kind: EvidenceKind
    label: str
    role: Role
    reason: str
    required_before: str = "monitoring"  # monitoring | quality_release | closure
    freshness_max_s: int = 7200
    validity_rule: dict = field(default_factory=dict)
    blocks_conditions: list[str] = field(default_factory=list)


@dataclass
class MachineProfile:
    equipment_class: str
    label: str
    machine_models: list[str]
    baseline: dict
    conditions: list[ProfileCondition]
    evidence: list[ProfileEvidence]
    required_stable_cycles: int = 30
    cycle_seconds: float = 12.0
    fault_codes: list[str] = field(default_factory=list)
    summary: str = ""


def _stable_cycles_condition(n: int) -> ProfileCondition:
    return ProfileCondition(
        key="stable_cycles", kind=ConditionKind.PRODUCTION, label="Consecutive stable cycles",
        op=CompareOp.COUNT_GTE, threshold=float(n), unit="cycles", deadline_kind="window",
        rationale=f"{n} consecutive stable cycles are required before closure.")


def _first_piece_condition() -> ProfileCondition:
    return ProfileCondition(
        key="first_piece", kind=ConditionKind.QUALITY, label="First-piece inspection",
        op=CompareOp.EQ, threshold=1.0, deadline_kind="window",
        rationale="A first-piece quality inspection must pass before quality release.")


def _standard_evidence(measure_label: str, unit: str, max_value: float) -> list[ProfileEvidence]:
    return [
        ProfileEvidence(
            key="post_intervention_measurement", kind=EvidenceKind.NUMERIC_MEASUREMENT,
            label=measure_label, role=Role.TECHNICIAN,
            reason="Confirms the intervention actually changed the machine before monitoring.",
            required_before="monitoring",
            validity_rule={"type": "numeric", "min": 0.0, "max": max_value}),
        ProfileEvidence(
            key="technician_completion", kind=EvidenceKind.COMPLETION,
            label="Technician completion sign-off", role=Role.TECHNICIAN,
            reason="Confirms the physical work is finished and the machine is restartable.",
            required_before="monitoring", validity_rule={"type": "present"}),
        ProfileEvidence(
            key="first_piece_quality", kind=EvidenceKind.PHOTO,
            label="First-piece quality inspection result", role=Role.QUALITY_ENGINEER,
            reason="First-piece must pass before any quality release.",
            required_before="quality_release", freshness_max_s=14400,
            validity_rule={"type": "pass_fail", "expect": "pass"}, blocks_conditions=["first_piece"]),
    ]


# ── the catalog ───────────────────────────────────────────────────────────────
CONVEYOR_DRIVE = MachineProfile(
    equipment_class="conveyor_drive",
    label="Conveyor-drive assembly",
    machine_models=["CDX-220"],
    baseline={"vibration_mm_s": 3.1, "temp_c": 63.0, "cycle_time_s": 12.2, "scrap_pct": 1.6},
    cycle_seconds=12.2, required_stable_cycles=30, fault_codes=["F27"],
    summary="Motor/coupling/bearing drivetrain on a packaging conveyor.",
    conditions=[
        ProfileCondition("vibration_rms", ConditionKind.MACHINE, "Vibration RMS", CompareOp.LTE,
                         "mm/s", 4.0, "vibration_mm_s", "VIB", deadline_kind="cycles", deadline_value=10,
                         rationale="RMS must fall below 4.0 mm/s within 10 cycles."),
        ProfileCondition("temperature_trend", ConditionKind.MACHINE, "Temperature trend", CompareOp.DECLINING,
                         "°C", None, "temp_c", "TMP", deadline_kind="minutes", deadline_value=15,
                         rationale="Drive temperature must begin declining within 15 minutes."),
        ProfileCondition("fault_f27", ConditionKind.MACHINE, "Fault F27 non-recurrence", CompareOp.NOT_RECUR,
                         fault_code="F27", rationale="The originating fault must not recur in the window."),
        ProfileCondition("cycle_time", ConditionKind.MACHINE, "Cycle time vs baseline", CompareOp.WITHIN_PCT,
                         "s", 0.05, "cycle_time_s", "CYC", deadline_kind="cycles", deadline_value=10,
                         rationale="Cycle time must return within 5% of baseline."),
        ProfileCondition("scrap", ConditionKind.PRODUCTION, "Scrap rate", CompareOp.LT, "%", 2.0,
                         "scrap_pct", rationale="Scrap must return below 2.0%."),
        _stable_cycles_condition(30),
        _first_piece_condition(),
    ],
    evidence=_standard_evidence("Post-intervention vibration measurement", "mm/s", 4.5),
)

INJECTION_PRESS = MachineProfile(
    equipment_class="injection_molding_press",
    label="Injection-molding press",
    machine_models=["IMX-90", "IMX-160"],
    baseline={"melt_temp_c": 230.0, "injection_pressure_bar": 1100.0, "cycle_time_s": 38.0, "scrap_pct": 1.2},
    cycle_seconds=38.0, required_stable_cycles=25, fault_codes=["E12"],
    summary="Thermoplastic injection press: melt temperature, injection pressure, short-shot/flash scrap.",
    conditions=[
        ProfileCondition("melt_temperature", ConditionKind.MACHINE, "Melt temperature vs setpoint",
                         CompareOp.WITHIN_PCT, "°C", 0.03, "melt_temp_c", "MLT", deadline_kind="cycles",
                         deadline_value=8, rationale="Melt temperature must hold within 3% of setpoint."),
        ProfileCondition("injection_pressure", ConditionKind.MACHINE, "Peak injection pressure",
                         CompareOp.LTE, "bar", 1200.0, "injection_pressure_bar", "PRS",
                         deadline_kind="cycles", deadline_value=8,
                         rationale="Peak injection pressure must stay at or below 1200 bar."),
        ProfileCondition("fault_e12", ConditionKind.MACHINE, "Fault E12 non-recurrence", CompareOp.NOT_RECUR,
                         fault_code="E12", rationale="The originating fault must not recur in the window."),
        ProfileCondition("cycle_time", ConditionKind.MACHINE, "Cycle time vs baseline", CompareOp.WITHIN_PCT,
                         "s", 0.05, "cycle_time_s", "CYC", deadline_kind="cycles", deadline_value=8,
                         rationale="Cycle time must return within 5% of baseline."),
        ProfileCondition("scrap", ConditionKind.PRODUCTION, "Short-shot / flash scrap", CompareOp.LT, "%",
                         2.0, "scrap_pct", rationale="Scrap must return below 2.0%."),
        _stable_cycles_condition(25),
        _first_piece_condition(),
    ],
    evidence=_standard_evidence("Post-intervention pressure/melt measurement", "bar", 1200.0),
)

HYDRAULIC_PUMP = MachineProfile(
    equipment_class="hydraulic_pump",
    label="Hydraulic power unit",
    machine_models=["HPU-50"],
    baseline={"vibration_mm_s": 2.4, "oil_temp_c": 55.0, "discharge_pressure_bar": 180.0, "scrap_pct": 0.0},
    cycle_seconds=20.0, required_stable_cycles=20, fault_codes=["P09"],
    summary="Hydraulic power unit: vibration, oil temperature, discharge-pressure stability.",
    conditions=[
        ProfileCondition("vibration_rms", ConditionKind.MACHINE, "Vibration RMS", CompareOp.LTE, "mm/s",
                         3.5, "vibration_mm_s", "VIB", deadline_kind="cycles", deadline_value=8,
                         rationale="Pump vibration must fall below 3.5 mm/s."),
        ProfileCondition("oil_temperature", ConditionKind.MACHINE, "Oil temperature trend", CompareOp.DECLINING,
                         "°C", None, "oil_temp_c", "OIL", deadline_kind="minutes", deadline_value=20,
                         rationale="Oil temperature must begin declining within 20 minutes."),
        ProfileCondition("fault_p09", ConditionKind.MACHINE, "Fault P09 non-recurrence", CompareOp.NOT_RECUR,
                         fault_code="P09", rationale="The originating fault must not recur in the window."),
        ProfileCondition("discharge_pressure", ConditionKind.MACHINE, "Discharge pressure vs baseline",
                         CompareOp.WITHIN_PCT, "bar", 0.04, "discharge_pressure_bar", "DPR",
                         deadline_kind="cycles", deadline_value=8,
                         rationale="Discharge pressure must hold within 4% of baseline."),
        _stable_cycles_condition(20),
        _first_piece_condition(),
    ],
    evidence=_standard_evidence("Post-intervention vibration measurement", "mm/s", 3.8),
)

PROFILES: dict[str, MachineProfile] = {
    p.equipment_class: p for p in (CONVEYOR_DRIVE, INJECTION_PRESS, HYDRAULIC_PUMP)
}


def profile_for_model(machine_model: str) -> MachineProfile | None:
    for p in PROFILES.values():
        if machine_model in p.machine_models:
            return p
    return None


# ── generic builder ───────────────────────────────────────────────────────────
def build_contract_from_profile(
    profile: MachineProfile,
    *,
    incident_id: str,
    intervention_id: str,
    contract_no: str,
    objective: str = "",
    baseline: dict | None = None,
    version: int = 1,
) -> RecoveryContractSpec:
    """Instantiate a fully-valid Recovery Contract for any machine class from its declarative profile."""
    base = {**profile.baseline, **(baseline or {})}

    def cond(i: int, pc: ProfileCondition) -> ConditionSpec:
        return ConditionSpec(
            key=pc.key, kind=pc.kind, label=pc.label, op=pc.op, threshold=pc.threshold, unit=pc.unit,
            baseline=base.get(pc.baseline_key) if pc.baseline_key else None,
            sensor_tag=pc.sensor_tag, fault_code=pc.fault_code, deadline_kind=pc.deadline_kind,
            deadline_value=pc.deadline_value, policy_ref=f"{contract_no} · C{i + 1}", rationale=pc.rationale,
        )

    conds = [cond(i, pc) for i, pc in enumerate(profile.conditions)]
    machine = [c for c in conds if c.kind == ConditionKind.MACHINE]
    production = [c for c in conds if c.kind == ConditionKind.PRODUCTION]
    quality = [c for c in conds if c.kind == ConditionKind.QUALITY]

    evidence = [
        EvidenceReqSpec(
            key=e.key, kind=e.kind, label=e.label, assigned_role=e.role, reason_required=e.reason,
            required_before=e.required_before, freshness_max_s=e.freshness_max_s,
            validity_rule=e.validity_rule, blocks_conditions=e.blocks_conditions,
        )
        for e in profile.evidence
    ]
    approvals = [
        ApprovalReqSpec(
            key="contract_review", label="Approve recovery contract & begin monitoring",
            required_role=Role.SUPERVISOR, required_before="monitoring",
            grants=["begin_recovery_monitoring"], denies=PROHIBITED_GRANTS, policy_ref=f"{contract_no} · A1",
        ),
        ApprovalReqSpec(
            key="quality_release", label="Release quality hold",
            required_role=Role.QUALITY_ENGINEER, required_before="quality_release",
            grants=["release_quality_hold", "disposition_affected_lots"], denies=PROHIBITED_GRANTS,
            policy_ref=f"{contract_no} · A-Q",
        ),
    ]
    return RecoveryContractSpec(
        contract_no=contract_no, version=version, incident_id=incident_id, intervention_id=intervention_id,
        objective=objective or (f"Verify that the intervention actually recovered the {profile.label.lower()} "
                                "— not merely that the work order was completed."),
        policy_version=_settings.policy_version, workflow_version=_settings.workflow_version,
        machine_conditions=machine, production_conditions=production, quality_conditions=quality,
        evidence_requirements=evidence, approval_requirements=approvals,
        verification_window=VerificationWindowSpec(required_stable_cycles=profile.required_stable_cycles,
                                                   cycle_seconds=profile.cycle_seconds),
        closure_policy=ClosurePolicySpec(), reopening_policy=ReopeningPolicySpec(),
        escalation_policy=EscalationPolicySpec(),
    )

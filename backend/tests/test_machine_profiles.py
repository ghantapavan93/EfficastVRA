"""Machine-agnostic catalog tests (Phase 10).

Proves the Recovery Contract is a primitive that works for *any* machine class, not a hardcoded
conveyor scenario: every declarative profile instantiates a fully-valid, deterministically-evaluable
contract, and the conveyor profile agrees with the hand-tuned Northstar template.
"""

from __future__ import annotations

import pytest

from app.domain.enums import CompareOp, ConditionKind, Role
from app.services.contract_templates import build_v1_spec
from app.services.machine_profiles import (
    PROFILES,
    build_contract_from_profile,
    profile_for_model,
)


@pytest.mark.parametrize("equipment_class", list(PROFILES.keys()))
def test_every_profile_builds_a_valid_contract(equipment_class):
    profile = PROFILES[equipment_class]
    spec = build_contract_from_profile(
        profile, incident_id="INC-X", intervention_id="ITV-X", contract_no="RC-TEST",
    )
    conds = spec.all_conditions()

    # A reopening trigger: the originating fault must be a NOT_RECUR condition.
    assert any(c.op == CompareOp.NOT_RECUR for c in conds), f"{equipment_class}: no fault non-recurrence"
    # A full stable-cycle window is required.
    stable = [c for c in conds if c.op == CompareOp.COUNT_GTE]
    assert stable and stable[0].threshold >= profile.required_stable_cycles
    assert spec.verification_window.required_stable_cycles == profile.required_stable_cycles
    # Quality is present and human-gated.
    assert len(spec.quality_conditions) >= 1
    # Evidence: a measurement + a completion sign-off + a quality result.
    ev_keys = {e.key for e in spec.evidence_requirements}
    assert "post_intervention_measurement" in ev_keys
    assert "technician_completion" in ev_keys
    assert "first_piece_quality" in ev_keys
    # Approvals: supervisor review + quality release, and machine control is explicitly denied.
    appr = {a.key: a for a in spec.approval_requirements}
    assert appr["contract_review"].required_role == Role.SUPERVISOR
    assert appr["quality_release"].required_role == Role.QUALITY_ENGINEER
    for a in appr.values():
        assert "machine_start" in a.denies and "automatic_quality_release" in a.denies
    # Baselines resolved onto scalar conditions from the profile.
    scalar = [c for c in spec.machine_conditions if c.op in (CompareOp.LTE, CompareOp.WITHIN_PCT)]
    assert any(c.baseline is not None for c in scalar)


def test_conveyor_profile_agrees_with_handtuned_template():
    spec = build_contract_from_profile(
        PROFILES["conveyor_drive"], incident_id="INC-2841", intervention_id="ITV-1", contract_no="RC-1042",
    )
    template = build_v1_spec("INC-2841", "ITV-1", "RC-1042")
    profile_keys = {c.key for c in spec.all_conditions()}
    template_keys = {c.key for c in template.all_conditions()}
    assert profile_keys == template_keys, (profile_keys, template_keys)


def test_profile_lookup_by_model():
    assert profile_for_model("CDX-220").equipment_class == "conveyor_drive"
    assert profile_for_model("IMX-90").equipment_class == "injection_molding_press"
    assert profile_for_model("HPU-50").equipment_class == "hydraulic_pump"
    assert profile_for_model("UNKNOWN-1") is None

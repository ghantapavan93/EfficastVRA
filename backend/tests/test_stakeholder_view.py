"""Stakeholder views — each persona sees only its relevant tabs/actions/approvals; app roles map to personas."""

from __future__ import annotations

from app.services.stakeholder_view import (
    STAKEHOLDER_VIEWS,
    all_stakeholder_views,
    stakeholder_view,
    view_for_role,
)


def test_seven_personas_exist():
    assert len(STAKEHOLDER_VIEWS) == 7
    assert {"operator", "maintenance_technician", "maintenance_supervisor", "production_supervisor",
            "quality_engineer", "plant_manager", "efficast_implementation_engineer"} == set(STAKEHOLDER_VIEWS)
    assert len(all_stakeholder_views()) == 7


def test_operator_sees_a_subset_of_the_plant_manager():
    op = set(stakeholder_view("operator")["tabs"])
    pm = set(stakeholder_view("plant_manager")["tabs"])
    assert op and op < pm                      # strict subset — the operator sees less


def test_quality_engineer_approves_quality_release_only():
    qe = stakeholder_view("quality_engineer")
    assert qe["can_approve"] == ["quality_release"]
    assert "comparability" in qe["tabs"] and "lot-at-risk" in qe["tabs"]


def test_app_roles_map_to_personas():
    assert view_for_role("supervisor")["persona"] == "maintenance_supervisor"
    assert view_for_role("quality_engineer")["persona"] == "quality_engineer"
    assert view_for_role("technician")["persona"] == "maintenance_technician"
    assert view_for_role("plant_admin")["persona"] == "plant_manager"
    assert view_for_role("unknown")["persona"] == "plant_manager"   # safe default: full oversight

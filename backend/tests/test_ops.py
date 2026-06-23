"""Enterprise operational-readiness tests (Phase 18): IAM least privilege, metrics, control checks."""

from __future__ import annotations

from app import observability
from app.domain.enums import Role
from app.security import PERMISSIONS, PROHIBITED_PERMISSIONS, can, permissions_for
from app.services.governance import control_checks
from app.workflow.demo import run_scenario


def test_least_privilege_permission_matrix():
    # Each role holds only what its job needs.
    assert can(Role.SUPERVISOR, "approve_contingency")
    assert not can(Role.SUPERVISOR, "submit_measurement")
    assert can(Role.TECHNICIAN, "submit_measurement")
    assert not can(Role.TECHNICIAN, "approve_contingency")
    assert can(Role.QUALITY_ENGINEER, "approve_quality_release")

    # The agent is a service principal: it proposes/monitors but can NEVER approve or close.
    assert can(Role.AGENT, "propose_recovery_contract")
    assert not can(Role.AGENT, "approve_contingency")
    assert not can(Role.AGENT, "approve_quality_release")

    # No role anywhere holds a machine-control (or model-closure) capability.
    for role, perms in PERMISSIONS.items():
        assert not (perms & PROHIBITED_PERMISSIONS), role
    assert permissions_for(Role.SUPERVISOR)  # sorted, non-empty


def test_metrics_snapshot_has_slis():
    observability.record_request(status=200, ms=12.0)
    observability.record_request(status=200, ms=30.0)
    observability.record_request(status=500, ms=5.0)
    snap = observability.snapshot()
    assert snap["requests_total"] >= 3
    assert snap["errors_total"] >= 1
    assert "p95" in snap["latency_ms"]
    assert snap["by_status"].get("2xx", 0) >= 2
    assert snap["uptime_seconds"] >= 0


def test_continuous_control_checks_all_pass(session):
    run_scenario(session, log=lambda *a: None)
    checks = {c["control"]: c["status"] for c in control_checks(session)}
    assert checks["Audit trail integrity (tamper-evident)"] == "pass"
    assert checks["No machine-control capability granted to any principal"] == "pass"
    assert checks["Least-privilege RBAC enforced"] == "pass"
    assert all(s in ("pass", "warn") for s in checks.values())

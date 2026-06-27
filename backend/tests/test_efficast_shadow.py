"""Replay adapter + shadow-mode evaluation over sanitised, enveloped bundles. No DB, no external writes."""

from __future__ import annotations

import pytest

from app.integration.efficast.adapters import (
    ReplayEfficastAdapter,
    SandboxEfficastAdapter,
    SyntheticEfficastAdapter,
)
from app.integration.efficast.fixtures import make_f27_bundle
from app.integration.efficast.shadow import run_shadow


def test_replay_full_window_shadow_proposes_verified():
    report = run_shadow(make_f27_bundle(cycles=30))
    assert report.writes_performed == 0                       # structural no-write guarantee
    inc = report.incidents[0]
    assert inc.proposed_disposition == "verified"
    assert inc.actual_outcome == "verified" and inc.agreement is True
    assert inc.sensor_trust == "trusted" and inc.comparability == "COMPARABLE"


def test_cycle17_relapse_shadow_proposes_failed():
    report = run_shadow(make_f27_bundle(cycles=30, relapse_at=17))
    inc = report.incidents[0]
    assert inc.proposed_disposition == "failed"
    assert inc.actual_outcome == "failed" and inc.agreement is True


def test_untrusted_sensor_refuses_verified():
    report = run_shadow(make_f27_bundle(cycles=30, sensor_status="untrusted"))
    inc = report.incidents[0]
    assert inc.proposed_disposition == "insufficient_evidence"   # an untrusted sensor can't satisfy a hard condition
    assert inc.sensor_trust == "untrusted"


def test_duplicate_webhook_is_reconciled_then_shadow_still_works():
    bundle = make_f27_bundle(cycles=30)
    report = run_shadow(bundle + [bundle[10]])                 # replayed webhook (same idempotency_key)
    assert report.reconciliation.counts.get("duplicate") == 1
    assert report.incidents[0].proposed_disposition == "verified"


def test_replay_adapter_serves_reads_and_records_proposals():
    a = ReplayEfficastAdapter(make_f27_bundle(cycles=5))
    assert a.get_asset_context("L4-CONV") is not None
    assert a.get_active_production_order("L4-CONV").order_id == "PO-2841"
    assert len(a.get_sensor_health("L4-CONV")) == 1
    pr = a.propose_incident_reopen("REPLAY-INC-1", reason="relapse")
    assert pr.accepted and pr.kind == "propose_incident_reopen" and len(a.proposals) == 1


def test_synthetic_adapter_is_a_replay_over_the_canned_bundle():
    a = SyntheticEfficastAdapter(cycles=5)
    assert a.get_asset_context("L4-CONV").machine_model == "CDX-220"


def test_sandbox_adapter_is_not_wired():
    sb = SandboxEfficastAdapter()
    with pytest.raises(NotImplementedError):
        sb.get_asset_context("L4-CONV")
    with pytest.raises(NotImplementedError):
        sb.publish_recovery_status("inc", "verified")

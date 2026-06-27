"""Contract v0.1 parsing + integration reconciliation (dedup / order / lateness / drift / unit / mapping /
partial / missing-mapping). Pure, no DB."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.integration.efficast.contract import TelemetryObservation, parse_event
from app.integration.efficast.reconciliation import reconcile

_BASE = datetime(2026, 1, 1, 8, 0, 0)


def _tel(idem, ts, *, ingest=None, unit="mm/s", mv="0.1", dq="OK", value=3.1, cid="c1", src="efficast"):
    return TelemetryObservation(
        source_system=src, schema_version="0.1", mapping_version=mv, tenant_id="t", plant_id="p",
        source_id="s1", correlation_id=cid, idempotency_key=idem, source_timestamp=ts,
        ingestion_timestamp=ingest or ts + timedelta(seconds=2), timezone="UTC", data_quality=dq,
        machine_id="m1", metric="vibration_rms", value=value, unit=unit)


def test_parse_event_discriminates_by_type():
    raw = _tel("k1", _BASE).model_dump(mode="json")
    ev = parse_event(raw)
    assert isinstance(ev, TelemetryObservation) and ev.metric == "vibration_rms"


def test_duplicate_idempotency_key_is_deduped():
    r = reconcile([_tel("dup", _BASE), _tel("dup", _BASE)])
    assert len(r.accepted) == 1 and r.counts.get("duplicate") == 1


def test_out_of_order_is_flagged_and_resorted():
    r = reconcile([_tel("a", _BASE + timedelta(seconds=60)), _tel("b", _BASE)])
    assert r.counts.get("out_of_order") == 1
    assert r.accepted[0].source_timestamp == _BASE  # downstream always sees source-time order


def test_late_event_is_flagged():
    r = reconcile([_tel("a", _BASE + timedelta(seconds=1000)), _tel("b", _BASE)])
    assert r.counts.get("late") == 1


def test_clock_drift_is_flagged():
    r = reconcile([_tel("a", _BASE, ingest=_BASE + timedelta(seconds=600))])
    assert r.counts.get("clock_drift") == 1


def test_unit_mismatch_is_flagged():
    r = reconcile([_tel("a", _BASE, unit="in/s")])  # expected mm/s
    assert r.counts.get("unit_mismatch") == 1


def test_mapping_version_change_is_flagged():
    r = reconcile([_tel("a", _BASE, mv="0.1"), _tel("b", _BASE + timedelta(seconds=60), mv="0.2")])
    assert r.counts.get("mapping_version_change") == 1


def test_partial_data_is_flagged():
    r = reconcile([_tel("a", _BASE, dq="SUSPECT")])
    assert r.counts.get("partial_data") == 1


def test_unknown_event_type_is_missing_mapping():
    r = reconcile([{"event_type": "totally_unknown", "idempotency_key": "x"}])
    assert r.counts.get("missing_mapping") == 1 and not r.accepted

"""Recovery Mission Intake — Bring-Your-Own-Plant-Data: schema detect → propose mapping → readiness →
incident reconstruction. Read-only/advisory; the qualification verdict is decided downstream, never here.
"""

from __future__ import annotations

from app.api.intake_routes import _sample_csv
from app.services.intake import analyze_upload, parse_content


def _mapping_index(result: dict) -> dict:
    return {(m["target_event"], m["target_field"]): m["column"] for m in result["mappings"] if m["target_event"]}


def test_messy_headers_are_mapped_to_the_contract():
    r = analyze_upload("northstar.csv", _sample_csv())
    m = _mapping_index(r)
    assert m.get(("asset", "source_id")) == "machine_code"
    assert m.get(("event", "source_timestamp")) == "event_time"
    assert m.get(("machine_event", "event_code")) == "fault"
    assert m.get(("production_cycle", "cycle_index")) == "cycle_no"
    assert ("telemetry", "value") in m
    assert r["mapped_count"] >= 5


def test_readiness_blocks_on_missing_approval():
    rd = analyze_upload("northstar.csv", _sample_csv())["readiness"]
    assert rd["verdict"] == "blocked"
    assert any("approval" in b.lower() for b in rd["blocked"])
    assert isinstance(rd["score"], int)


def test_reconstruction_detects_false_closure_and_missing_evidence():
    rc = analyze_upload("northstar.csv", _sample_csv())["reconstruction"]
    assert rc["false_closure_detected"] is True
    assert rc["fault_count"] == 1
    assert any(e["kind"] == "derived" and "did not sustain" in e["label"].lower() for e in rc["entries"])
    assert any(e["kind"] == "ai_interpretation" for e in rc["entries"])
    assert any(e["kind"] == "missing" for e in rc["entries"])
    assert "missing" in rc["summary"].lower()


def test_parses_json_and_jsonl():
    t = parse_content("x.json", '[{"machine":"M1","timestamp":"2026-01-01T08:00:00","fault":"F27"}]')
    assert t.fmt == "json" and t.rows[0]["machine"] == "M1"
    t2 = parse_content("x.jsonl", '{"machine":"M1","time":"2026-01-01T08:00:00"}\n{"machine":"M1","time":"2026-01-01T08:01:00"}')
    assert t2.fmt == "jsonl" and len(t2.rows) == 2


def test_clean_data_with_approval_is_not_blocked_on_authorization():
    csv = ("machine,timestamp,fault,quality_result,approved_by\n"
           "M1,2026-01-01T08:00:00,,pass,q.idris\n"
           "M1,2026-01-01T08:01:00,,pass,q.idris\n")
    rd = analyze_upload("clean.csv", csv)["readiness"]
    assert not any("approval" in b.lower() for b in rd["blocked"])

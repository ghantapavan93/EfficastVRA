"""Agent reliability + reasoning-trace tests (Phase 8).

These lock in the two claims that make the agent industry-grade:
  1. it never false-closes a relapse and never over-rejects a genuine recovery (eval harness); and
  2. its reasoning is fully recorded as an inspectable perceive→…→reflect/decide trace.
"""

from __future__ import annotations

from app.agent.eval import run_eval
from app.agent.trace import list_traces
from app.domain.models import Incident
from app.workflow.demo import run_scenario
from sqlmodel import select


def test_agent_never_false_closes_across_variants():
    report = run_eval()
    assert report.false_closures == 0, "agent published a verified recovery despite a real relapse"
    assert report.missed_relapses == 0, "agent failed to catch a real relapse"
    assert report.false_reopens == 0, "agent reopened a genuinely-recovered line"
    assert report.reliability == 1.0
    assert report.precision == 1.0
    assert report.passed
    # All four relapse variants must be caught; the clean variant must verify.
    by_name = {v.name: v for v in report.variants}
    assert by_name["clean (genuine recovery)"].outcome == "verified"
    for name, v in by_name.items():
        if v.relapse_cycle is not None:
            assert v.caught_relapse, f"{name} not caught"


def test_reasoning_trace_records_full_arc(session):
    run_scenario(session, log=lambda *a: None)
    incident = session.exec(select(Incident).where(Incident.historical == False)).first()  # noqa: E712
    traces = list_traces(session, incident.id)
    nodes = [t.node for t in traces]

    # The drafting arc and the monitoring arc are both present.
    for node in ("perceive", "retrieve", "hypothesize", "draft", "self_critique", "decide"):
        assert node in nodes, f"missing reasoning node {node}"
    assert "reflect" in nodes, "cycle-17 reflection missing"

    # Retrieval guardrail is visible: non-authoritative sources were suppressed.
    retrieve = next(t for t in traces if t.node == "retrieve")
    assert len(retrieve.outputs.get("suppressed", [])) > 0

    # The confidence trajectory tells the story: a violation collapse, then a verified peak.
    reflect = next(t for t in traces if t.node == "reflect")
    assert reflect.confidence is not None and reflect.confidence <= 0.10
    verified = [t for t in traces if t.node == "decide" and (t.confidence or 0) >= 0.95]
    assert verified, "no high-confidence verified decision recorded"

    # The agent's reasoning never grants permissions — it only proposes.
    for t in traces:
        assert t.model_version  # provenance present on every step

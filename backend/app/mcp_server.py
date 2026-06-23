"""Model Context Protocol (MCP) server — read-only, grounded interoperability.

MCP is the 2025-26 industry standard (Anthropic/OpenAI/Google/Microsoft) for letting any agent or
host (Claude, a copilot, another agent) discover and call a system's capabilities. This server exposes
the Verified Recovery Agent's **verified, grounded, read-only** tools over JSON-RPC 2.0 on stdio — so a
plant manager's Claude, or a supervising agent, can ask "is PO-2841 actually recovered? is the audit
intact?" and get answers backed by the deterministic evaluator and the tamper-evident log.

SAFETY — the interop layer respects the same boundary as everything else:
  • Only READ_ONLY tools are exposed. There is **no** MCP tool that writes state, grants an approval,
    reopens an incident, or controls a machine. Consequential actions still require the Agent Action
    Gateway + a human, and are not reachable here. (Enforced by tests/test_mcp.py.)

Self-contained (no SDK dependency) and spec-compliant for the tools capability: ``initialize``,
``tools/list``, ``tools/call``, ``ping``. Run:  python -m app.mcp_server   (then connect an MCP host).
"""

from __future__ import annotations

import json
import sys
from typing import Any, Callable, Optional

from sqlmodel import Session, select

from app.api import serializers as S
from app.db import engine
from app.domain.models import Incident
from app.rag import search
from app.workflow.audit import verify_audit_chain

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "verified-recovery-agent", "version": "0.1.0"}


# ── tool handlers (every one is strictly read-only) ───────────────────────────
def _incident(session: Session, args: dict) -> Incident:
    inc = session.get(Incident, args.get("incident_id", ""))
    if inc is None:
        raise ValueError(f"incident {args.get('incident_id')!r} not found")
    return inc


def _t_get_mission(session: Session, args: dict) -> Any:
    return S.mission_detail(session, _incident(session, args))


def _t_recovery_metrics(session: Session, args: dict) -> Any:
    inc = _incident(session, args)
    from app.domain.models import RecoveryContract

    out: dict = {"incident_id": inc.id, "state": inc.state.value, "reopened_count": inc.reopened_count}
    if inc.current_contract_id:
        contract = session.get(RecoveryContract, inc.current_contract_id)
        if contract is not None:
            out["evaluation"] = S.condition_views(session, contract)
    return out


def _t_search_requirements(session: Session, args: dict) -> Any:
    hits = search(session, args.get("query", ""), machine_model=args.get("machine_model"),
                  approved_only=True, k=int(args.get("k", 4)))
    return [{"document_id": h.document_id, "section": h.section, "revision": h.revision,
             "approval_status": h.approval_status, "excerpt": h.content[:240]} for h in hits]


def _t_historical_interventions(session: Session, args: dict) -> Any:
    fault = args.get("fault_code")
    q = select(Incident).where(Incident.historical == True)  # noqa: E712
    if fault:
        q = q.where(Incident.fault_code == fault)
    return [{"id": i.id, "fault_code": i.fault_code, "outcome": i.outcome_type.value if i.outcome_type else None,
             "summary": i.outcome_summary} for i in session.exec(q).all()]


def _t_verify_audit(session: Session, args: dict) -> Any:
    return verify_audit_chain(session, _incident(session, args).correlation_id)


def _t_machine_profiles(session: Session, _args: dict) -> Any:
    return S.machine_profiles_view()


def _t_diagnosis(session: Session, args: dict) -> Any:
    return S.diagnosis_view(session, _incident(session, args))


def _t_forecast(session: Session, args: dict) -> Any:
    return S.forecast_view(session, _incident(session, args))


def _t_troubleshoot(session: Session, args: dict) -> Any:
    from app.services.troubleshooting import troubleshoot

    return troubleshoot(session, fault_code=args.get("fault_code"),
                        machine_model=args.get("machine_model"), query=args.get("query", ""))


def _t_decision(session: Session, args: dict) -> Any:
    from app.services.decision import decide

    return decide(session, _incident(session, args))


def _t_reliability(session: Session, args: dict) -> Any:
    from app.services.reliability_stats import assess

    return assess(session, _incident(session, args))


def _t_provenance(session: Session, args: dict) -> Any:
    from app.services.provenance import closure_provenance

    return closure_provenance(session, _incident(session, args))


def _t_sensitivity(session: Session, args: dict) -> Any:
    from app.services.sensitivity import analyze

    return analyze(session, _incident(session, args))


def _t_knowledge(session: Session, _args: dict) -> Any:
    from app.services.knowledge import list_candidates

    return [S.knowledge_view(k) for k in list_candidates(session)]


def _t_open_alerts(session: Session, _args: dict) -> Any:
    return S.open_alerts_view(session)


_INCIDENT_ARG = {"type": "object", "properties": {"incident_id": {"type": "string"}},
                 "required": ["incident_id"]}

TOOLS: list[dict[str, Any]] = [
    {"name": "get_mission", "fn": _t_get_mission, "inputSchema": _INCIDENT_ARG,
     "description": "Full mission state for an incident: workflow state, progress, plain-language brief."},
    {"name": "get_recovery_metrics", "fn": _t_recovery_metrics, "inputSchema": _INCIDENT_ARG,
     "description": "Deterministic recovery-condition evaluation for an incident (the verified truth)."},
    {"name": "search_recovery_requirements", "fn": _t_search_requirements,
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"},
                     "machine_model": {"type": "string"}, "k": {"type": "integer"}}, "required": ["query"]},
     "description": "Approval/recency-filtered manual retrieval (obsolete/unapproved sources excluded)."},
    {"name": "search_historical_interventions", "fn": _t_historical_interventions,
     "inputSchema": {"type": "object", "properties": {"fault_code": {"type": "string"}}},
     "description": "Past incidents with the same fault and how they were actually resolved."},
    {"name": "verify_audit_integrity", "fn": _t_verify_audit, "inputSchema": _INCIDENT_ARG,
     "description": "Recompute the tamper-evident audit hash chain; reports if any entry was altered."},
    {"name": "list_machine_profiles", "fn": _t_machine_profiles, "inputSchema": {"type": "object", "properties": {}},
     "description": "Supported machine classes (the machine-agnostic Recovery Contract catalog)."},
    {"name": "get_incident_diagnosis", "fn": _t_diagnosis, "inputSchema": _INCIDENT_ARG,
     "description": "The agent's triage diagnosis: ranked root causes + proposed intervention + citations."},
    {"name": "get_recovery_forecast", "fn": _t_forecast, "inputSchema": _INCIDENT_ARG,
     "description": "Predicts whether the repair will hold before the fault recurs (advisory): competing-hypothesis support + early relapse warning."},
    {"name": "troubleshoot_fault", "fn": _t_troubleshoot,
     "inputSchema": {"type": "object", "properties": {"fault_code": {"type": "string"},
                     "machine_model": {"type": "string"}, "query": {"type": "string"}}},
     "description": "Grounded troubleshooting for a fault/machine: approved procedure, ranked causes, past-incident history, signals to check, and captured lessons."},
    {"name": "get_decision_intelligence", "fn": _t_decision, "inputSchema": _INCIDENT_ARG,
     "description": "Risk-adjusted decision view (advisory): cost/production exposure, expected cost of each option with a recommendation, and an FMEA (RPN)."},
    {"name": "get_reliability_assessment", "fn": _t_reliability, "inputSchema": _INCIDENT_ARG,
     "description": "Statistical confidence in the recovery verdict (advisory): zero-failure reliability-demonstration test (confidence vs. stable cycles, cycles needed for a target), window grade, and bathtub-curve hazard read."},
    {"name": "get_closure_provenance", "fn": _t_provenance, "inputSchema": _INCIDENT_ARG,
     "description": "Why the outcome was decided and whether it can be trusted: deterministic conditions, trust-weighted evidence, human approvals, interventions, proposed-vs-executed reconciliation, and audit-chain integrity."},
    {"name": "get_contract_sensitivity", "fn": _t_sensitivity, "inputSchema": _INCIDENT_ARG,
     "description": "Counterfactual contract calibration (advisory): replays the verifier over the real trajectory at different verification-window lengths — the minimum-safe window and which thresholds would have falsely closed before the relapse."},
    {"name": "list_knowledge", "fn": _t_knowledge, "inputSchema": {"type": "object", "properties": {}},
     "description": "Institutional knowledge base: candidate + human-approved lessons from past recoveries (with review status)."},
    {"name": "list_open_alerts", "fn": _t_open_alerts, "inputSchema": {"type": "object", "properties": {}},
     "description": "Open MAIA-style alerts awaiting triage."},
]
_BY_NAME = {t["name"]: t for t in TOOLS}


def _ok(req_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def handle_jsonrpc(request: dict, session: Session) -> Optional[dict]:
    """Pure MCP request handler (so it is unit-testable). Returns None for notifications."""
    method = request.get("method")
    req_id = request.get("id")
    if method == "initialize":
        return _ok(req_id, {"protocolVersion": PROTOCOL_VERSION,
                            "capabilities": {"tools": {"listChanged": False}},
                            "serverInfo": SERVER_INFO})
    if method == "ping":
        return _ok(req_id, {})
    if method and method.startswith("notifications/"):
        return None  # notifications get no response
    if method == "tools/list":
        return _ok(req_id, {"tools": [{"name": t["name"], "description": t["description"],
                                       "inputSchema": t["inputSchema"]} for t in TOOLS]})
    if method == "tools/call":
        params = request.get("params") or {}
        name = params.get("name")
        tool = _BY_NAME.get(name)
        if tool is None:
            return _ok(req_id, {"content": [{"type": "text", "text": f"unknown tool: {name}"}],
                                "isError": True})
        try:
            result = tool["fn"](session, params.get("arguments") or {})
            text = json.dumps(result, default=str, ensure_ascii=False, indent=2)
            return _ok(req_id, {"content": [{"type": "text", "text": text}], "isError": False})
        except Exception as exc:  # surface tool errors as MCP tool errors, not transport errors
            return _ok(req_id, {"content": [{"type": "text", "text": f"error: {exc}"}], "isError": True})
    if req_id is None:
        return None
    return _err(req_id, -32601, f"method not found: {method}")


def serve() -> None:
    """stdio JSON-RPC loop. Each request is handled in its own DB session."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        with Session(engine) as session:
            response = handle_jsonrpc(request, session)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    serve()

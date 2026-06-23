"""MCP server tests (Phase 15): spec compliance + the read-only safety guarantee.

Top-grade agents interoperate over MCP; this proves ours does — and that the interop layer cannot
write state or control a machine (it exposes only read-only, grounded tools).
"""

from __future__ import annotations

import json

from app.domain.models import Incident
from app.mcp_server import PROTOCOL_VERSION, TOOLS, handle_jsonrpc
from app.workflow.demo import run_scenario
from sqlmodel import select


def _active(session) -> Incident:
    return session.exec(select(Incident).where(Incident.historical == False)).first()  # noqa: E712


def test_initialize_handshake(session):
    res = handle_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, session)
    assert res["result"]["protocolVersion"] == PROTOCOL_VERSION
    assert "tools" in res["result"]["capabilities"]
    assert res["result"]["serverInfo"]["name"] == "verified-recovery-agent"


def test_notifications_get_no_response(session):
    assert handle_jsonrpc({"jsonrpc": "2.0", "method": "notifications/initialized"}, session) is None


def test_tools_list_is_read_only(session):
    res = handle_jsonrpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, session)
    names = {t["name"] for t in res["result"]["tools"]}
    assert "get_recovery_metrics" in names and "verify_audit_integrity" in names
    # No exposed tool may write state, approve, reopen, publish, or control a machine.
    forbidden = ("submit", "approve", "decide", "reopen", "publish", "draft", "start", "stop",
                 "restart", "escalate", "accept", "create", "triage", "advance", "read")
    for name in names:
        assert not any(verb in name for verb in forbidden), f"non-read-only tool exposed via MCP: {name}"
    # Every tool advertises a JSON-Schema input contract.
    for t in res["result"]["tools"]:
        assert t["inputSchema"]["type"] == "object"


def test_tools_call_returns_grounded_verified_data(session):
    run_scenario(session, log=lambda *a: None)
    inc = _active(session)

    metrics = handle_jsonrpc({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                              "params": {"name": "get_recovery_metrics",
                                         "arguments": {"incident_id": inc.id}}}, session)
    assert metrics["result"]["isError"] is False
    payload = json.loads(metrics["result"]["content"][0]["text"])
    assert payload["incident_id"] == inc.id and payload["state"] == "VERIFIED_RECOVERY"

    integ = handle_jsonrpc({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                            "params": {"name": "verify_audit_integrity",
                                       "arguments": {"incident_id": inc.id}}}, session)
    assert json.loads(integ["result"]["content"][0]["text"])["ok"] is True


def test_unknown_tool_is_a_tool_error_not_a_crash(session):
    res = handle_jsonrpc({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                          "params": {"name": "delete_everything", "arguments": {}}}, session)
    assert res["result"]["isError"] is True


def test_unknown_method_returns_jsonrpc_error(session):
    res = handle_jsonrpc({"jsonrpc": "2.0", "id": 6, "method": "bogus/method"}, session)
    assert res["error"]["code"] == -32601


def test_tool_count_matches_registry():
    assert len(TOOLS) == 13

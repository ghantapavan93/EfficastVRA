# MCP integration — read-only, grounded interoperability

The Verified Recovery Agent ships a **Model Context Protocol** server (`backend/app/mcp_server.py`) so
any MCP host — Claude Desktop, an IDE copilot, or another agent — can query its **verified, grounded**
state. MCP is the 2025-26 industry interop standard (Anthropic/OpenAI/Google/Microsoft).

## What it exposes (all read-only)
`get_mission` · `get_recovery_metrics` · `search_recovery_requirements` · `search_historical_interventions`
· `verify_audit_integrity` · `list_machine_profiles` · `get_incident_diagnosis` · `list_open_alerts`.

These reuse the same serializers/services the UI uses, so an external agent sees exactly the
deterministic, evidence-backed truth — e.g. *"is PO-2841 actually recovered, and is its audit intact?"*

## Safety — the interop layer respects the gateway
There is **no MCP tool that writes state, grants an approval, reopens an incident, publishes a
decision, or controls a machine.** Consequential actions still require the Agent Action Gateway + a
human and are unreachable over MCP. This is enforced by `tests/test_mcp.py` (the exposed tool set is
asserted read-only) and by the architecture fitness functions.

## Run it
```bash
cd backend && python -m app.mcp_server        # speaks JSON-RPC 2.0 over stdio
```
Spec-compliant for the tools capability: `initialize`, `tools/list`, `tools/call`, `ping`. It is
dependency-free (no MCP SDK required) so it doesn't compromise the "runs with just Python" guarantee.

## Connect from Claude Desktop
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "verified-recovery": {
      "command": "<path>/backend/.venv/Scripts/python.exe",
      "args": ["-m", "app.mcp_server"],
      "cwd": "<path>/backend"
    }
  }
}
```
Then ask Claude: *"Using verified-recovery, is INC-2841 recovered and is its audit chain intact?"* —
it will call `get_recovery_metrics` and `verify_audit_integrity` and answer from grounded data.

## Why this matters
A plant leader's existing AI assistant can now consult the recovery agent's *verified* answers instead
of guessing — without any ability to take an unsafe action. It makes the agent a trustworthy,
interoperable capability in a larger agent ecosystem, which is exactly how top-grade industrial AI is
deployed (see [`AGENT_CAPABILITY_AUDIT.md`](AGENT_CAPABILITY_AUDIT.md)).

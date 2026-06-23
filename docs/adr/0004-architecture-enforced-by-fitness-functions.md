# ADR 0004 — The architecture is enforced by tests, not just documented

**Status:** Accepted

## Context
Documented boundaries erode silently as a codebase grows: a convenient import quietly couples the
domain to the web layer, or lets the agent reach the gateway. For a safety-relevant system the most
important invariants (the LLM cannot actuate; machine control cannot exist) must not depend on
reviewer vigilance.

## Decision
Encode the architecture as **executable fitness functions** (`backend/tests/test_architecture.py`)
that parse the `app/` import graph and fail the build on violation:
1. the **domain core** imports no outer layer (it is the hexagon's center);
2. nothing but the API package + entrypoint depends on the **web layer**;
3. the **agent and reasoning layers never import the gateway** (they propose; only the workflow
   actuates);
4. the **tool registry is reachable only through the gateway**;
5. **no machine-control function** exists anywhere in the source.

## Consequences
- The architecture's load-bearing invariants are verified on every test run, alongside behaviour.
- New code that breaks a boundary fails immediately, with the offending file + import named.
- The ADRs above are kept honest — their guarantees are mechanically checked, not aspirational.

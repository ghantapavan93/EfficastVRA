# Architecture Decision Records

Each ADR captures one significant architectural decision: its context, the decision, and the
consequences. They are the *why* behind the structure; the *what* is in
[`../ARCHITECTURE.md`](../ARCHITECTURE.md) and the *enforcement* is in
`backend/tests/test_architecture.py` (executable fitness functions).

| # | Decision | Status |
|---|---|---|
| [0001](0001-hexagonal-ports-and-composition-root.md) | Hexagonal architecture: explicit ports + a composition root | Accepted |
| [0002](0002-deterministic-verifier-not-the-llm.md) | A deterministic verifier decides recovery; the LLM only proposes | Accepted |
| [0003](0003-agent-action-gateway-and-no-machine-control.md) | One gateway choke point for side effects; machine control is prohibited | Accepted |
| [0004](0004-architecture-enforced-by-fitness-functions.md) | The architecture is enforced by tests, not just documented | Accepted |

## Further decisions (recorded in their own docs)
- **Durable DB-backed state machine**, Temporal-compatible interface — [`../STATE_MACHINE.md`](../STATE_MACHINE.md).
- **Transactional outbox + active relay** for reliable, exactly-once event publication —
  [`../KNOWN_LIMITATIONS.md`](../KNOWN_LIMITATIONS.md), `app/workflow/audit.py`.
- **ISA-95 / Unified-Namespace addressing + a connector catalog** for integration —
  [`../INTEGRATION_ARCHITECTURE.md`](../INTEGRATION_ARCHITECTURE.md), [`../INDUSTRY_LANDSCAPE.md`](../INDUSTRY_LANDSCAPE.md).
- **Machine-agnostic Recovery Contract catalog** (declarative profiles) — [`../MACHINE_AGNOSTIC.md`](../MACHINE_AGNOSTIC.md).
- **Tamper-evident, hash-chained audit trail** — [`../SECURITY_MODEL.md`](../SECURITY_MODEL.md).
- **Bounded, Reflexion-style agent graph** grounded in SOTA research — [`../AGENT_RESEARCH.md`](../AGENT_RESEARCH.md), [`../AGENT_GRAPH.md`](../AGENT_GRAPH.md).

# Agent capability audit — top-grade industry vs. this prototype

Independent web research (2026-06-22) into what production/enterprise AI agents ship in 2025-26, mapped
honestly against what we have. The headline: the field has converged on an **"Evidence & Control
Layer"** (observability + evaluation + runtime-enforced guardrails before side effects) — which is
essentially this product's architecture — plus **MCP** as the interop standard, which we had *not* had
until now.

Sources: [Red Hat – Building agents with MCP](https://developers.redhat.com/articles/2026/01/08/building-effective-ai-agents-mcp),
[IBM – Secure enterprise agents with MCP](https://www.aigl.blog/architecting-secure-enterprise-ai-agents-with-mcp-ibm-oct-2025/),
[Oracle – Evidence & Control Layer](https://blogs.oracle.com/ai-and-datascience/evidence-control-layer-enterprise-ai),
[AI agents 2026: tools, memory, evals, guardrails](https://andriifurmanets.com/blogs/ai-agents-2026-practical-architecture-tools-memory-evals-guardrails),
[State of AI Agent Memory 2026 (Mem0)](https://mem0.ai/blog/state-of-ai-agent-memory-2026),
[AI Agent Observability guide](https://atlan.com/know/ai-agent-observability/).

## Capability matrix
| Capability | Top-grade industry (2025-26) | This prototype | Status |
|---|---|---|---|
| Stateful orchestration | LangGraph / Claude Agent SDK / CrewAI | bounded Reflexion-style Plan-Executor graph (LangGraph-compatible) | ✅ have |
| **MCP interoperability** | the standard (Anthropic/OpenAI/Google/MS); Gartner: 75% of API gateways by 2026 | **read-only MCP server** (`app/mcp_server.py`) exposing grounded/verified tools | ✅ have (added) |
| Runtime guardrails *before* side effects | Guardrails AI; "control layer" | **Agent Action Gateway** (12-stage, decides before execute); machine control prohibited | ✅ have (exceeds) |
| Observability | LangSmith / Langfuse / Arize tracing | reasoning traces + correlation IDs + structured logs + **tamper-evident audit** | ✅ have (+ integrity) |
| Evaluation — outcome | offline eval harnesses, pass^k | reliability eval: **0 false closures** across variants (`app.cli eval`) | ✅ have |
| Evaluation — **trajectory** | tool-choice correctness, arg validity, step count, policy compliance | the full reasoning trajectory is *recorded*; not yet *scored* step-by-step | 🟡 partial |
| Human-in-the-loop | approvals / interrupts | approvals + gateway; quality release & closure require the right human | ✅ have |
| Determinism / reproducibility | rare (LLMs are stochastic) | deterministic verifier + provider + scenario replay | ✅ have (differentiator) |
| Grounding / provenance | RAG + citations | approval/recency-filtered RAG, citations, evidence freshness/validity | ✅ have |
| Memory (prevent repeating failures) | Mem0 hierarchical memory; DriftGuard semantic guardrails | historical incidents + RAG + human-reviewed knowledge candidates (same goal) | 🟡 partial |
| Cost / latency accounting | token + $ + step budgets | request latency logged; embed cache; no token cost (deterministic by default) | 🟡 partial |
| Domain interop (ISA-95/UNS) | UNS brokers, connector catalogs | ISA-95 hierarchy + UNS topics + connector catalog | ✅ have |

## Honest reading
- **What top-grade had that we didn't:** MCP interoperability — **now closed** (read-only, gateway-
  respecting). See [`MCP_INTEGRATION.md`](MCP_INTEGRATION.md).
- **Where we already match or exceed:** the Evidence & Control Layer (our whole architecture),
  runtime guardrails, determinism/reproducibility, tamper-evident audit, provenance, HITL, ISA-95/UNS.
- **Honest partial gaps (next depth):** (1) *trajectory-level* evaluation — we record the reasoning
  trace but don't yet grade tool-choice/step-count/policy-adherence per step; (2) a *unified memory*
  layer (we have the pieces — historical incidents + knowledge candidates — but not a Mem0-style
  extract/recall service); (3) token/cost budgets (moot while the default provider is deterministic).

These partials are deliberate scope choices, not oversights — recorded here so the audit is honest
(consistent with the project's evidence-ledger discipline).

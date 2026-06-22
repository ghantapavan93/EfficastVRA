# Research Gaps & Unresolved Assumptions

This file tracks claims that could **not** be independently verified at build time, and the
conservative assumption used in their place. It is updated as verification becomes possible.

## Status of web access

At Phase-0 start, `WebSearch`/`WebFetch` and shell tools were gated by a hosted command-safety
classifier that was **temporarily unavailable**, so live web verification could not run. Per the
brief's contingency, browsing was treated as unavailable: claims were grounded in **directly
observable** local material (the nine Efficast product screenshots and the supplied landing-page
image) and conservative assumptions, with gaps recorded here for later verification.

> Re-verification log is appended at the bottom as tools recover.

## Technical claims to verify (used conservatively until confirmed)

| # | Claim / assumption used | Confidence | Verify by |
|---|---|---|---|
| T1 | **LangGraph** is OSS (MIT) and suitable for bounded agent flows. | High (prior knowledge) | langchain-ai/langgraph LICENSE on GitHub/PyPI |
| T2 | **FastAPI** (MIT), **Pydantic v2** (MIT), **SQLModel** (MIT) are permissive. | High | PyPI/GitHub LICENSE |
| T3 | **pgvector** (PostgreSQL License) integrates as a Postgres extension. | High | pgvector/pgvector repo |
| T4 | **Temporal** (MIT, Temporal Technologies) is a valid durable-workflow evolution. | High | temporalio/temporal LICENSE |
| T5 | **IBM AssetOpsBench / ReActXen** exist as published industrial-agent eval/agent resources. | AssetOpsBench **VERIFIED** ([arXiv 2506.03828](https://arxiv.org/abs/2506.03828), 2026-06-21); ReActXen still unverified | IBM research pages / arXiv / GitHub |
| T6 | **Microsoft agentic-factory**, **MongoDB / AWS / Intel** predictive-maintenance examples exist as referenceable patterns. | Low — **unverified** | vendor docs / GitHub |
| T7 | **PHM / ISO 13374 / ISO 10816** vibration-severity bands are the right framing for "acceptable vibration". | Medium | ISO 10816 / 20816 standards |

**Impact of T5–T7 being unverified:** none of the prototype's behavior depends on them. They are
cited only as *prior art / evolution context*, never as a source of truth for thresholds. All
numeric thresholds in the demo are `PROTOTYPE_ASSUMPTION`s chosen for narrative clarity, not
copied from any standard or product. They are documented as such in
[`RECOVERY_CONTRACT.md`](RECOVERY_CONTRACT.md).

## Efficast claims to verify

See [`EFFICAST_EVIDENCE_LEDGER.md`](EFFICAST_EVIDENCE_LEDGER.md). Everything tagged `OBSERVED` is
from the supplied screenshots/landing image; everything tagged `INFERRED`/`UNKNOWN`/
`PROTOTYPE_ASSUMPTION` is **not** asserted as fact about Efficast's real product or internals.

## Re-verification log

Web tools recovered later in the build; the following were verified independently (2026-06-21):

- **T1 — LangGraph license: CONFIRMED + important caveat.** `langgraph` / `langchain-core` are MIT
  (langchain-ai/langgraph LICENSE). **However, `langgraph-api` (the `langgraph dev` / `langgraph build`
  server runtime) is Elastic License 2.0** and needs a commercial key for production. *Mitigation
  already in place:* LangGraph is an **optional** dependency here and the `DeterministicReasoningProvider`
  carries the entire demo, so the prototype never depends on `langgraph-api` — no Elastic-licensed code
  is used. Recorded in [`LICENSE_AUDIT.md`](LICENSE_AUDIT.md).
- **Efficast — CONFIRMED as a real product** at `https://efficast.ai`. The public site corroborates the
  `OBSERVED` claims (industrial IoT/OEE platform, MAIA agent that reports/closes work orders/alerts
  bottlenecks, "AI supervisor on WhatsApp", PLC-sourced MES, legacy-machine compatibility). The
  Evidence Ledger upgrades those claims to `VERIFIED (public site)`. Private internals (E14–E17) remain
  `UNKNOWN`.
- **T5 — IBM AssetOpsBench: now VERIFIED (web, 2026-06-21).** Real paper — *AssetOpsBench: Benchmarking
  AI Agents for Task Automation in Industrial Asset Operations and Maintenance* ([arXiv 2506.03828](https://arxiv.org/abs/2506.03828),
  IBM Research, Jun 2025): 4 domain agents, 140+ NL queries, simulated IoT env (2.3M sensor points),
  Tool-As-Agent vs Plan-Executor evaluation. Captured in [`AGENT_RESEARCH.md`](AGENT_RESEARCH.md) and used
  to position our Plan-Executor agent. **ReActXen** not separately re-confirmed (still unverified).
- **Phase-8 agent SOTA — VERIFIED (web, 2026-06-21).** τ-bench ([2406.12045](https://arxiv.org/abs/2406.12045)),
  LLM-as-a-Judge survey ([2411.15594](https://arxiv.org/abs/2411.15594)), G-SPEC neuro-symbolic
  deterministic verification ([2512.20275](https://arxiv.org/abs/2512.20275)), Reflexion/self-reflection,
  and "illusions of reflection" ([2510.18254](https://arxiv.org/abs/2510.18254)) all confirmed and mapped
  to design in [`AGENT_RESEARCH.md`](AGENT_RESEARCH.md).
- **T6 — Microsoft/MongoDB/AWS/Intel examples: STILL UNVERIFIED.** The prototype depends on none of them
  (cited only as evolution context). Treat as unverified prior art.
- **T4 — Temporal:** MIT (temporalio/temporal), consistent with prior knowledge; used only as a
  documented future evolution path, not a runtime dependency.

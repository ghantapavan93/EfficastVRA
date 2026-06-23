# ADR 0002 — A deterministic verifier decides recovery; the LLM only proposes

**Status:** Accepted

## Context
The product's core claim is that *a completed work order is not proof of recovery*. The decision to
close, reopen, or escalate an incident is high-consequence. Frontier LLM agents are unreliable for
such decisions — τ-bench (arXiv 2406.12045) shows SOTA function-calling agents succeed on <50% of
tasks (pass^8 < 25%), and LLM-as-judge is biased and cannot verify against real observations
(arXiv 2411.15594). See [`../AGENT_RESEARCH.md`](../AGENT_RESEARCH.md).

## Decision
Split reasoning from adjudication (a neuro-symbolic design):
- The **LLM / `ReasoningProvider`** *proposes*: it drafts the Recovery Contract, identifies missing
  evidence, compares history, explains, and triages alerts — recorded as an inspectable reasoning
  trace.
- A **deterministic evaluator** (`app/services/evaluator.py`) *decides*: it computes each condition's
  status against real observations + human/quality evidence and produces the verdict. No LLM is on the
  authority path.

## Consequences
- Closure is reproducible, auditable, and immune to model error/hallucination — proven by the
  reliability eval (`python -m app.cli eval`: 0 false closures across scenario variants).
- The demo never depends on a hosted model (deterministic provider carries it); a hosted model only
  enriches explanations.
- Confidence shown in the UI is a *display aid*, never the decision.

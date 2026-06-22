# Agent Research → Design (SOTA, 2024–2026)

Independent literature review (web-verified 2026-06-21) of the newest agent research, mapped to
concrete design choices in this prototype. The headline result of the field is the strongest
justification for this product: **frontier LLM agents are not reliable enough to be the authority in
high-consequence settings**, so the agent must *propose* while **deterministic, symbolic code
verifies and gates**, with humans approving consequential actions.

## 0. The reliability problem (why this architecture exists)
- **τ-bench** — *Tool-Agent-User Interaction in Real-World Domains* ([arXiv 2406.12045](https://arxiv.org/abs/2406.12045),
  ICLR 2025). Even SOTA function-calling agents (e.g. GPT-4o) **succeed on <50% of tasks** and are
  **inconsistent (pass^8 < 25%)**. Introduces **pass^k** (reliability over k trials) and evaluates by
  comparing **final database state to an annotated goal state**.
  → **Adopted:** our eval harness uses a pass^k-style reliability metric and a **DB-state-vs-ground-
  truth** comparison (`app/agent/eval.py`); we treat the LLM as unreliable by construction.
- **A Survey on LLM-as-a-Judge** ([arXiv 2411.15594](https://arxiv.org/abs/2411.15594)) and
  **Agent-as-a-Judge** survey ([arXiv 2601.05111](https://arxiv.org/abs/2601.05111)): LLM judges are
  constrained by *bias, shallow single-pass reasoning, and inability to verify against real-world
  observations.*
  → **Rejected:** we never use an LLM to judge whether recovery happened. The **deterministic recovery
  evaluator** judges against real observations; the model only drafts/explains.
- **Illusions of reflection** ([arXiv 2510.18254](https://arxiv.org/abs/2510.18254)): self-reflection
  has *systematic failures* on open-ended tasks.
  → **Design consequence:** self-critique is used **only to improve a draft**, never as the verifier.
  The verifier is external and deterministic (see §2).

## 1. Reflexion / verification loops (the agent's shape)
- **Reflexion** (Actor · Evaluator · Self-Reflection) and **Self-Reflection in LLM Agents**
  ([arXiv 2405.06682](https://arxiv.org/abs/2405.06682)); **Self-Reflection for hallucination
  mitigation** ([arXiv 2310.06271](https://arxiv.org/abs/2310.06271)); **Chain-of-Verification**
  (Dhuliawala et al., [arXiv 2309.11495](https://arxiv.org/abs/2309.11495)).
  → **Adopted:** the agent graph is a Reflexion-shaped loop — **Actor** (drafts the Recovery Contract
  + missing-evidence analysis), **Evaluator** = our *deterministic* recovery evaluator acting as the
  reliable "environment feedback", **Self-Reflection** (critique → revise) bounded to ≤2 iterations.
  Crucially the Evaluator is symbolic, not an LLM — addressing the "illusions of reflection" failure.

## 2. Neuro-symbolic verification + guardrails (the safety core)
- **G-SPEC** — *Graph-Symbolic Policy Enforcement & Control* ([arXiv 2512.20275](https://arxiv.org/abs/2512.20275)):
  a neuro-symbolic framework that **constrains probabilistic planning with deterministic verification**,
  reporting **zero safety violations** on a simulated network; notes that *probabilistic supervision of
  probabilistic black boxes cannot provide a deterministic security bound.*
- **Neuro-Symbolic Verification of Instruction Following** ([arXiv 2601.17789](https://arxiv.org/abs/2601.17789));
  **Provably Secure Agent Guardrail** ([arXiv 2605.29251](https://arxiv.org/abs/2605.29251));
  **Policy-Compliant Agents / learned guardrails** ([arXiv 2510.03485](https://arxiv.org/abs/2510.03485));
  **Neuro-Symbolic Agents for Regulated Process Automation** ([arXiv 2606.13405](https://arxiv.org/abs/2606.13405)).
  → **Adopted (already core):** the **Agent Action Gateway** is exactly a symbolic policy-enforcement
  layer (risk classes, `PROHIBITED` machine control, role/policy/approval/idempotency/circuit-breaker
  gates). Per G-SPEC, the verifier is **deterministic**, never another LLM. This is the prototype's
  neuro-symbolic spine.

## 3. Industrial-agent benchmarks (domain grounding)
- **AssetOpsBench** — *Benchmarking AI Agents for Task Automation in Industrial Asset Operations and
  Maintenance* (IBM Research, [arXiv 2506.03828](https://arxiv.org/abs/2506.03828), Jun 2025):
  4 domain agents, **140+ human-authored queries**, a simulated IoT environment (**2.3M sensor points**,
  chillers/AHUs), and an evaluation framework contrasting the **Tool-As-Agent** vs **Plan-Executor**
  paradigms with automated failure-mode discovery. *(This resolves the earlier `UNVERIFIED` tag for
  AssetOpsBench — it is real.)*
  → **Positioning:** our agent is a **Plan-Executor** (an explicit bounded graph that plans then
  executes through the gateway) augmented with a deterministic verifier — the configuration
  AssetOpsBench-style analysis tends to favor for reliability/auditability over free Tool-As-Agent.
- **ReliabilityBench** ([arXiv 2601.06112](https://arxiv.org/abs/2601.06112)) and **GAF-Guard**
  agentic governance ([arXiv 2507.02986](https://arxiv.org/abs/2507.02986)).
  → **Adopted:** circuit breaker + idempotency + full audit trail + the eval harness are our reliability/
  governance instrumentation.

## 4. Retrieval & memory
- Approval/recency-aware retrieval and conflict surfacing (our RAG) align with the broad GraphRAG/
  provenance-aware-retrieval direction: **filter by applicability + approval before similarity** so a
  stale revision or unapproved note can never become authoritative; persist a candidate-knowledge loop
  gated by human review (never auto-promoted) — consistent with the LLM-as-judge caution above.

## Synthesis — the design we converged on
A **neuro-symbolic, verifier-gated, Reflexion-style Plan-Executor**:

| Layer | Role | Reliability stance |
|---|---|---|
| **Neural (LLM / deterministic provider)** | perceive, retrieve, hypothesize, draft contract, self-critique, explain | treated as *unreliable* (τ-bench) — proposes only |
| **Symbolic verifier** (deterministic evaluator) | judge recovery against real observations | the authority — reproducible, auditable (G-SPEC) |
| **Symbolic gateway** (policy enforcement) | classify risk, enforce policy/role/approval, block `PROHIBITED` | deterministic guardrail (provably-secure-guardrail direction) |
| **Human** | approve consequential actions, release quality | in command — never bypassed by the model |

## What we deliberately reject (and why)
- **LLM-as-judge for closure** — biased, unverifiable against observations (2411.15594).
- **Self-reflection as the verifier** — systematic failures (2510.18254); we use an external symbolic
  verifier.
- **Free Tool-As-Agent autonomy** over operational tools — τ-bench reliability is too low for OT
  consequences; everything crosses the gateway.
- **Probabilistic guardrails supervising the LLM** — cannot give a deterministic safety bound (G-SPEC).

See [`AGENT_GRAPH.md`](AGENT_GRAPH.md) for the implemented graph and [`EVALUATION.md`](EVALUATION.md)
for the pass^k reliability results.

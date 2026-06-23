# Provenance & evidence trust — "why did the system decide this, and can we trust the closure?"

A dashboard shows numbers; a **traceable operational system** can *reconstruct a decision*. This layer
answers the question an auditor, a regulator, or an industrial buyer actually asks: **who requested the
recovery, which evidence supported it, who approved it, what changed, and why it closed or reopened —
and can we trust that closure?** It is the difference between "the agent says it's fixed" and "here is
the chain of custody behind the verdict."

It sits **beside the deterministic evaluator, not inside the LLM layer**: the agent proposes a reasoning
path, but provenance is assembled *independently* from the data the system already records. Read-only and
advisory — it never changes state.

`app/services/provenance.py` · `app/services/evidence_quality.py` · `GET /api/incidents/{id}/provenance`
· MCP `get_closure_provenance` · UI **Provenance** tab · tests `tests/test_provenance.py`.

## 1. Evidence quality — not all evidence is equally trustworthy
The evaluator already gates closure on *validated* evidence. This adds **how strong** each piece is, via
a GRADE-style hierarchy of evidence (direct/empirical outranks inferred/secondary):

| Tier | Trust ceiling | Example |
|---|---:|---|
| Direct instrument reading | 1.00 | a sensor value |
| Measured human reading | 0.85 | a technician's vibration measurement (mm/s) |
| Technician observation | 0.60 | a pass/fail / "completed" note |
| Manual / document reference | 0.50 | a cited procedure revision |
| System-inferred | 0.40 | a derived/system value |

Then **validity and freshness discount the ceiling**: an unvalidated or conflicting item collapses to
`trust = 0` (it is not evidence yet); a stale item (older than its requirement's freshness window) is
halved. The summary surfaces the **weakest link**, not just the average — so a single stale note can't
hide behind four fresh sensor reads.

## 2. The closure-provenance record
`closure_provenance(session, incident)` assembles, from existing data:
- **Conditions** — the deterministic verifier's per-condition pass/fail (the actual basis of the verdict).
- **Evidence** — every item with its tier + trust + discount flags, and an aggregate (count, mean, weakest).
- **Approvals** — who authorised what (role, decision, reason, timestamp).
- **Interventions** — what was done, *including the failed first attempt* (history is preserved).
- **Reconciliation** — see §3.
- **Audit integrity** — the tamper-evident hash chain, recomputed (`ok`, `count`, first broken seq).
- A plain-language **summary** and a `trustworthy` flag (audit intact ∧ reconciled ∧ no zero-trust evidence).

Verified live (hero scenario): *Recovery VERIFIED — 7 conditions evaluated, 5 evidence items (mean trust
0.70), 3 approvals, proposed↔executed reconciled, audit chain intact (64 entries).*

## 3. Reconciliation — "logs alone are not proof"
Self-reported success is not proof of action. The reconciler **independently** compares every
`ActionProposal` against the `ToolExecution` records: it flags any proposal that claims `executed` with
no execution row, any proposal stuck `proposed`, and any execution with **no owning proposal** (a side
effect that bypassed the gateway's proposal step). On a clean run: *12 proposed / 12 executed, 0
unreconciled, 0 orphans*. This is the runtime complement to the gateway's allowlist invariant (H7) and the
savepoint-isolated failure path (H1).

## Why this is safe (and the right kind of "trust")
- **Independent of the LLM.** Provenance is built from the deterministic verifier, the gateway's
  proposal/execution log, and the hash-chained audit — never from the model's self-narration.
- **Retrieved content stays untrusted.** Manuals, tickets, and technician notes are treated as untrusted
  input (the RAG layer filters by approval/recency; the gateway enforces policy before any side effect),
  consistent with OWASP LLM prompt-injection guidance — so a poisoned document can inform a *hypothesis*
  but never an approval, a closure, or a tool permission.
- **Read-only & advisory.** It explains and grades; the deterministic evaluator still owns the verdict.

## References
- [What is AI traceability? Lineage, auditability & compliance (Snowflake)](https://www.snowflake.com/en/artificial-intelligence/ai-governance/ai-traceability/)
- [Data lineage & provenance for trustworthy AI pipelines](https://www.promptcloud.com/blog/data-lineage-and-provenance/)
- [TRiSM for Agentic AI — trust, risk & security management (arXiv 2506.04133)](https://arxiv.org/pdf/2506.04133)
- [GRADE / hierarchy of evidence](https://en.wikipedia.org/wiki/Hierarchy_of_evidence)
- OWASP Top 10 for LLM Applications — prompt injection (retrieved content is untrusted input).

# Organizational learning loop — tribal knowledge → institutional memory

The brief's hardest pain is *translating tribal knowledge into something the next shift can use*. This
closes that loop — and does it the way 2026 research says production agents should.

## What the research says (and what we do)
- **Human-as-judge curation** ([Tulip — human-in-the-loop in manufacturing](https://tulip.co/blog/human-in-the-loop-ai-explained/)):
  *"AI assistants make institutional knowledge accessible; the human acts as the judge, determining if
  that historical data applies."* → A verified recovery produces a **candidate** lesson; the required
  **reviewer role** judges whether it generalises before it becomes authoritative.
- **Continual learning by memory curation, not weight updates** ([Mem0 — State of Agent Memory 2026](https://mem0.ai/blog/state-of-ai-agent-memory-2026)):
  managing what the agent "knows" by curating a knowledge base sidesteps retraining and **avoids
  catastrophic forgetting**. → Our knowledge lives in a reviewed, queryable store, not model weights.
- **Org-scoped memory**: lessons are tagged with `applicable_models` + `component` (which machines a
  lesson applies to) — shared organizational context, not session scope.

## The loop
```
verified recovery ─▶ agent drafts KnowledgeCandidate (PENDING_REVIEW)
                  ─▶ reviewer (quality_engineer / plant_admin) approves or rejects   ← human judges
                  ─▶ APPROVED lesson becomes authoritative
                  ─▶ surfaces in Troubleshoot for the next shift / a sibling machine ← reused
```

- **Capture:** on verified recovery the agent records what failed, what worked, the conditions, and
  the applicable machine models (`create_knowledge_candidate`).
- **Curate:** `app/services/knowledge.py:review_knowledge` — **role-gated** (only the candidate's
  reviewer role or a plant admin; the agent can never approve its own lesson), audited
  (`KNOWLEDGE_REVIEWED`), idempotent. `GET /api/knowledge`, `POST /api/knowledge/{id}/review`, MCP
  `list_knowledge`, and the **Knowledge** page.
- **Reuse:** Troubleshoot shows *approved* lessons as authoritative and *pending* ones clearly labelled
  — so unreviewed knowledge is never presented as guidance.

## Why this is safe (and the right kind of "learning")
No model weights change, so there is no drift or catastrophic forgetting; knowledge is **explicit,
inspectable, attributed** (`reviewed_by`, reason, timestamp) and **human-curated** before it influences
anyone. Tested by `tests/test_knowledge.py` (capture → role-gated review → authoritative reuse).

This is the institutional-memory leg of the full loop: **detect → diagnose → verify → learn → reuse.**

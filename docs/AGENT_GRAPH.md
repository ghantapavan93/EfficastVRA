# The Recovery Agent Graph

The agent is a **bounded, neuro-symbolic, Reflexion-shaped Plan-Executor** (rationale + citations in
[`AGENT_RESEARCH.md`](AGENT_RESEARCH.md)). It lives in `backend/app/agent/` and is wired into the
durable workflow via `RecoveryService.draft_contract()` and `RecoveryService.advance()`.

> **The agent proposes; it never decides or acts on its own.** The deterministic recovery evaluator
> (`app/services/evaluator.py`) judges recovery, and the Agent Action Gateway (`app/gateway/`)
> authorises every side effect. The graph cannot grant a permission, mutate workflow state directly,
> or close an incident.

## Nodes

### Triage flow (front of the loop) — `RecoveryAgentGraph.triage(incident, alert)`
Closes the loop at the *front*: a MAIA-style alert is the trigger, and the agent diagnoses it and
proposes the intervention that the rest of the system then verifies.

| # | Node | What it does | Authority |
|---|------|--------------|-----------|
| 1 | **perceive** | reads the inbound `MaiaAlert` + the degraded machine snapshot | read-only |
| 2 | **classify** | classifies the degradation (mechanical drivetrain fault) | proposes |
| 3 | **retrieve** | approval/recency-filtered drivetrain procedures | read-only |
| 4 | **hypothesize** | ranks root causes — alignment (primary) vs. latent bearing (per INC-1990) | proposes |
| 5 | **propose** | recommends the intervention + contingency + citations; **awaits human acceptance** | proposes |

The agent never accepts its own diagnosis: `triage_from_alert` leaves the incident at
`INTERVENTION_PROPOSED`, and only a **supervisor** (`accept_diagnosis`) advances it to
`INTERVENTION_RECORDED`, where the drafting flow below takes over. Served at
`GET /api/incidents/{id}/diagnosis`; rendered in the **Agent Diagnosis** tab and the **MAIA Alerts**
inbox.

### Drafting flow — `RecoveryAgentGraph.draft(incident, intervention)`
| # | Node | What it does | Authority |
|---|------|--------------|-----------|
| 1 | **perceive** | reads the live machine snapshot through the Efficast port | read-only |
| 2 | **retrieve** | approval/recency-filtered manual retrieval + conflict detection; records which non-authoritative sources were **suppressed** | read-only |
| 3 | **hypothesize** | ranks failure hypotheses against historical precedent (alignment vs. latent bearing) | read-only |
| 4 | **draft** | structures the Recovery Contract spec (conditions, evidence, approvals, window, policy) | proposes |
| 5 | **self_critique** | a *deterministic* checklist over the draft (fault-non-recurrence enforced, ≥30-cycle window, human-gated quality, required evidence/approvals); Reflexion loop bounded to 2 iterations | symbolic check |
| 6 | **decide** | hands the contract to humans for review; emits a deliberately *low* recovery confidence | proposes |

### Monitoring flow — `RecoveryAgentGraph.observe(incident, contract, result, …)`
| Node | When | Confidence |
|------|------|-----------|
| **observe** | each monitoring batch while the window is open | rises with the stable streak, **capped at 0.80** (cautious by design) |
| **reflect** | on a deterministic `violated` verdict (e.g. F27 recurs at cycle 17) — explains the false recovery and recommends the contingency, *before* the gateway reopens | collapses to **0.05** |
| **decide** | on a deterministic `verified` verdict (30 stable cycles + quality release) | **0.97** |

Every node persists one `AgentReasoningTrace` row (`node, title, rationale, inputs, outputs,
citations, confidence, revision, model_version, prompt_version`). The full trace is served at
`GET /api/incidents/{id}/reasoning` and rendered in the mission's **Agent Reasoning** panel.

## The confidence trajectory (the story, in one column)
A real run of the canonical scenario produces:

```
#1 perceive                    Perceived L4-CONV post-intervention state
#2 retrieve                    Retrieved 4 approved sources; suppressed 6 non-authoritative
#3 hypothesize                 Ranked recovery hypotheses against historical precedent
#4 draft                       Drafted RC-1042 v1 — 7 conditions
#5 self_critique               Draft satisfies approved recovery policy
#6 decide        conf 0.40     Contract ready for human review
#7 observe       conf 0.54     Monitoring — cautious progress
#8 reflect       conf 0.05     Recovery Contract RC-1042 v1 violated — fault F27 recurred
#9 observe       conf 0.73     Monitoring (second window, post-bearing)
#10 decide       conf 0.97     Recovery verified — closure justified
```

`0.40 → 0.54 → 0.05 → 0.73 → 0.97` — the agent never reads as "victory" before the window proves it,
collapses honestly at the relapse, and only peaks once the deterministic evaluator confirms closure.

## LangGraph compatibility
Each node is a small method taking/returning a state dict, so the orchestration can be lifted into a
LangGraph `StateGraph` without changing node logic. We keep the framework-light version as the default
so the demo never depends on an external runtime or a hosted model — the
`DeterministicReasoningProvider` carries the entire flow (see [`PRODUCTION_EVOLUTION.md`](PRODUCTION_EVOLUTION.md)).

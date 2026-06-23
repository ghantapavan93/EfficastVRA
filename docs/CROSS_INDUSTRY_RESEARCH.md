# Cross-industry research — what manufacturing AI agents lag on

Web research (2026-06-23) into how AI agents work across industries, the gaps manufacturing agents
have versus them, and what we adopt. The decisive finding: *"manufacturing still needs to develop
robust **risk-adjusted decision frameworks**"* that finance already has
([CFO guide to AI agents 2026](https://www.houseblend.io/articles/ai-agents-finance-cfo-guide-2026),
[AI Decision Intelligence 2026](https://www.aitechboss.com/ai-decision-intelligence-2026/)).

## How agents differ by industry → what we take
| Industry | What their agents do well | Manufacturing's gap | What we adopt |
|---|---|---|---|
| **Finance** | **Risk-adjusted** decisions; *controlled autonomy — the agent acts but a human inspects every step*; the cost of being wrong is priced in | Technically focused (detect/diagnose/optimize); decisions aren't priced or risk-weighted | **Decision economics**: expected cost of each option (close / monitor / pre-stage), weighted by the Forecaster's P(relapse) → `app/services/decision.py` |
| **Aviation / reliability eng.** | **FMEA** — failure modes scored Severity × Occurrence × Detection = **RPN** ([RPN method](https://www.iqasystem.com/news/risk-priority-number/)); rank by RPN; recompute after a fix | Rarely surfaces structured failure-mode risk to the decision-maker | **FMEA table** with RPN, and a column showing the agent's detection *lowers* RPN |
| **Healthcare (clinical DS)** | Evidence-graded differential diagnosis; contraindication checks; explainability for liability | — | Grounded RAG + ranked causes + provenance (already present) |
| **Cybersecurity (SOC)** | Playbooks/runbooks; severity scoring; human-in-the-loop triage | — | Incident-response runbook + escalation + circuit breaker (already present) |

## The synthesis: a Decision Intelligence layer (the senior-manager view)
A 50-year plant manager doesn't decide in "P(relapse) = 0.87" — they decide in **dollars and risk**.
So the agent now answers the manager's question, not just the engineer's:

- **Cost exposure** — units at risk, throughput, hours to complete, and the **$ exposure of a false
  closure** (re-downtime + scrap).
- **Risk-adjusted recommendation** — the **expected cost** of *close now* vs *keep monitoring* vs
  *pre-stage the contingency*, weighted by the Forecaster's P(relapse); it recommends the cheapest and
  shows the math. The recommendation **flips with the probability** — exactly the finance-style frame
  manufacturing lacked.
- **FMEA / RPN** — the reliability-engineering rigor, including how the agent's own Forecaster cuts the
  detection score (and therefore RPN) versus flying blind.

Crucially, this matches finance's *controlled autonomy*: it is **advisory** — the deterministic
evaluator still decides closure, a human still makes the call, and every step is inspectable. We bring
finance's risk discipline and aviation's failure rigor into manufacturing **without** taking the
human out of command. See [`decision.py`] + the **Decision Intelligence** tab. (Cost/severity figures
are PROTOTYPE_ASSUMPTIONs, configurable via env — not Efficast data.)

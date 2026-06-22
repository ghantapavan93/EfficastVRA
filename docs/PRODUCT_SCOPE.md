# Product Scope

## The one job
Verify that **production actually recovered** after a maintenance intervention — and refuse to let a
"work order complete" status close an incident that the factory's real behavior contradicts.

The agent owns the **post-intervention verification loop**: define recovery (Recovery Contract),
gather required human evidence, observe the real trajectory, and close / conditionally-accept /
reopen / escalate.

## In scope (built)
- One end-to-end synthetic scenario: Northstar Packaging Plant, Packaging Line 4 conveyor drive,
  PO-2841, fault F27 — including the **cycle-17 relapse**, reopening, bearing contingency, and
  verified second recovery over 30 stable cycles.
- Recovery Contract primitive (drafted/explained by reasoning, **evaluated by deterministic code**).
- Durable 16-state workflow with audit, idempotency, approvals, verification windows, reopening.
- Agent Action Gateway (risk classification, policy, approval, circuit breaker) — every write goes
  through it; machine control is `PROHIBITED`.
- Bounded reasoning (deterministic provider carries the demo; hosted optional) + revision-/approval-
  aware RAG over a small synthetic manual corpus, with a prompt-injection defense test.
- Five required surfaces + the narrative screens (mission control/detail, contract, evidence,
  timeline, contingency, outcome, knowledge candidate), reading **real backend state**.
- Role-based identity (supervisor / technician / quality_engineer / plant_admin).

## Explicitly NOT in scope (non-goals)
General MES · full Efficast clone · CMMS · general predictive maintenance · multi-line optimization ·
general scheduling agent · digital twin · **autonomous machine control** · large multi-agent swarm ·
WhatsApp/email integration · Kubernetes · physics simulation · model training · generic OEE
dashboard · generic chatbot · agent marketplace.

## Why depth over breadth
A believable, *safe*, audited verification loop that catches a false recovery is worth more than a
shallow re-creation of an MES. The win condition is: **"we almost closed this — and the agent caught
what everyone would have missed,"** demonstrated through real state, not animation.

## Safety stance (non-negotiable)
No route/tool/mock performs or simulates physical machine control, PLC/set-point change, alarm or
interlock bypass, LOTO confirmation, safety certification, automatic quality release, or
model-controlled incident closure. These are `PROHIBITED` action classes, enforced by the gateway
and asserted by an automated test (`test_no_machine_control_exists`).

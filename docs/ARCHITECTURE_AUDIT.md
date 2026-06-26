# Architecture Audit & "Make It Real" Map (Phase 35 research pass)

*Established 2026‑06‑26. Method: six parallel, adversarial, research‑level audits — one per dimension
(verification core; safety/gateway/ops; intelligence layers; data/physics; integration/boundaries;
frontend/tests) — each read whole files and reported `file:line`‑backed findings with severity, effort,
and **frozen‑decision impact**. This doc is the deduplicated synthesis + the phased execution plan.*

> **Frozen‑decision check (global):** every fix below was vetted against the six frozen decisions in
> `CLAUDE.md`. **None requires changing a frozen decision.** Where a finding is *about* a frozen
> invariant being weaker than claimed (e.g. "every write goes through the gateway"), the fix
> *strengthens* it. Items needing Postgres/a broker to verify honestly are tagged **[infra]** and are
> deferred, not faked.

## Verdict up front
The **core thesis is genuinely well‑built and honest**: the deterministic evaluator solely owns closure,
the write‑side gateway is a real choke point, the safety *allowlist* test is a real invariant, the
Efficast **documentation** discipline is exemplary, the backend tests are more rigorous than `SYSTEM_OVERVIEW`
§7 admits, and the relabelling of heuristic numbers (H2–H6) largely landed. The gap between what the system
**claims** and what it **proves** is concentrated in five places — and closing them is the project's own
thesis applied to itself:

1. **"Machine‑agnostic" is real at the contract/spec layer but leaky in the runtime, serializers, and UI.**
2. **The "depth" analytics have honest labels but near‑zero epistemic content and no calibration harness.**
3. **The synthetic data is a single‑machine, single‑fault, noiseless, scripted trajectory** (schema is
   fleet‑ready; only the seed + generator are toy).
4. **Several self‑claims slightly overshoot:** anonymous⇒supervisor, "every write through the gateway"
   (telemetry ingest bypasses it), "exactly‑once outbox", audit "tamper‑evident" (tail truncation),
   "reached only via EfficastPort" (advisory/serializer reads bypass it).
5. **Frontend truthfulness regressions** where the backend did the honest work but the UI dropped the caveat.

---

## Findings (deduplicated, ranked within theme)

Legend — Sev: H/M/L · Eff: S/M/L · Frozen: ✅ safe / ⚠️ strengthens a frozen claim · Local: ✅ / **[infra]**.
"×N" = independently flagged by N audits (higher confidence).

### Theme A — Make verification genuinely machine‑agnostic & airtight
- **A1 [DONE, Phase 35b] ×3 — Evaluator hardcodes 4 conveyor metric keys.** `is_stable_observation` + the scalar
  key→field maps (`services/evaluator.py:59,143,179`) only know `vibration_rms/cycle_time/scrap/temperature`.
  Press/pump conditions (`melt_temperature`, `injection_pressure`, `oil_temperature`, `discharge_pressure`
  in `services/machine_profiles.py`) resolve to `None`→`BLOCKED` and **never gate the stable streak** — so the
  profile catalog can't actually be *verified*, only built. *Fix:* resolve `cond.key` against obs columns +
  `obs.raw` via a key map; drive a non‑conveyor profile through a full window in a test. **The deepest fix.**
- **A2 [H/M/✅] — Reopen/contingency path is hardcoded F27/bearing/BR‑6205.** `workflow/reopening.py:62‑80`
  always logs "fault F27 recurred" and always creates a `bearing_replacement`. On any other machine it
  reopens into a bearing job with a false audit reason. *Fix:* derive component + reason from the profile/
  violated condition (copy the M‑C `derive_knowledge_candidate` pattern).
- **A3 [DONE, Phase 35a] ×2 — Serializers hardcode "F27".** `api/serializers.py:328` `is_recurrence = o.fault_code=="F27"`;
  `:346‑351` before/after labels "F27 recurring"/"F27 absent". *Fix:* derive from `incident.fault_code`.
- **A4 [M/M/✅] — Verification‑timeline thresholds hardcoded in the frontend** (`components/timeline/
  verification-timeline.tsx:16‑21`), not contract‑derived (repo's open **M2**). *Fix:* pass thresholds from
  the contract conditions.
- **A5 [H/M/✅] — `stable_streak` is a single trusted mutable int.** `services/cycle_engine.py:84‑87` maintains
  it; `evaluate` trusts the cached int instead of recomputing from persisted observations. Single point of
  failure for the core "verified" claim. *Fix:* recompute the trailing streak in `evaluate()`; treat the
  column as a cache to assert against.
- **A6 [H/S/✅] — `required_stable_cycles` divergence.** `recovery_service.py:277,381` opens windows with
  `max(10, spec)`; the COUNT_GTE condition uses the spec value; `window_complete` uses the window value
  (`evaluator.py:138,213`). A contract authored <10 closes the window gate at a number its own contract JSON
  doesn't state. *Fix:* one source of truth; drop the floor; builder asserts COUNT_GTE.threshold == window.
- **A7 [M/S/✅] — Liveness holes:** `max_duration_min` (`domain/contract.py`) is never read; a DECLINING
  condition with `deadline_kind="window"` never fires (`evaluator.py:49‑56`); a secondary *unmatched* fault
  zeroes the streak but yields no `violated`/escalation — incidents can strand silently in `monitoring`.
  *Fix:* enforce `max_duration_min`; define window‑deadline for DECLINING; escalate on unmatched fault.
- **A8 [M/M/✅] — Scalar deadline checks only the latest reading** (`evaluator.py:142‑175`): a metric that
  recovered once then drifted out of spec can still read `PASSED`. *Fix:* require "within spec across the
  window" for scalar closure. Plus temperature is invisible to the streak (add a DECLINING branch).
- **A9 [M/S/⚠️] — Builder accepts silent contract gaps** (unresolved `blocks_conditions`, null baseline,
  missing QUALITY/COUNT_GTE) → safe‑but‑silent stalls. *Fix:* a deterministic contract linter in
  `workflow/contract_builder.py`.

### Theme B — Honesty & safety hardening (the thesis, applied to itself)
- **B1 [DONE, Phase 35a] ×2 — Anonymous ⇒ supervisor.** Missing `X-VRA-User` resolves to privileged `s.vega`
  (`auth.py:35`, `security.py:38`) with no demo‑mode gate — and "RBAC: pass" is still reported. *Fix:* gate
  the fallback on `settings.demo_mode`; 401 otherwise. **Highest‑ROI honesty fix.** *(done Phase 35a)*
- **B2 [H/M/⚠️] — Telemetry ingest bypasses the gateway and feeds the verdict.** `POST /api/telemetry/{id}`
  (`api/routes.py:396`) writes `TelemetrySample` with no plant scope, no audit, no idempotency — an attacker
  can manufacture "30 stable cycles". *Fix:* route ingest through a gateway tool (plant‑scope + audit +
  idempotency) or, minimally, add a plant‑scope guard + per‑batch audit.
- **B3 [DONE, Phase 35a] ×3 — Telemetry provenance is faked.** Every observation is stamped
  `source="SyntheticEfficastPort", freshness_s=2` (`cycle_engine.py:57`) even when `resolve_source` served
  *ingested* data. The product's own "can we trust the evidence?" thesis, violated by the data layer.
  *Fix:* derive `source`/`freshness_s` from the resolved `TelemetrySource` + timestamps. *(done Phase 35a)*
- **B4 [H/M/⚠️] — Audit tail‑truncation is undetectable**; deleting the last *k* rows still verifies `ok`,
  and governance only checks the single busiest correlation (`workflow/audit.py:44`, `services/governance.py:21`).
  Per‑correlation chains start from `""` so a forged parallel chain verifies clean. *Fix:* persist per‑correlation
  head/length; a global `AuditAnchor` chaining heads; verify all/anchor; optional HMAC over the head.
- **B5 [M/M/⚠️] — Outbox is at‑least‑once at best, barely used, relayed cross‑transaction in request
  middleware** (`main.py:83`); docstring claims "exactly‑once". *Fix:* publish in the state‑change session;
  move the relay to a background loop; add a consumer idempotency id; relabel as at‑least‑once + idempotent
  consumer. (Broker delivery is **[infra]**; durability+relay are SQLite‑verifiable.)
- **B6 [M/M/⚠️] — RBAC drift + read‑path scope.** `security.PERMISSIONS` is tested against itself but the
  gateway authorizes on `allowed_roles`, not `can()`; by‑id read routes aren't scoped to the principal's
  plant/tenant (`api/routes.py:74‑151`). *Fix:* make `PERMISSIONS` the gateway authority (or assert
  consistency); scope reads by plant. **[partly infra]** for multi‑tenant.
- **B7 [M/S/⚠️] — Safety is a substring denylist at the route/AST layer.** `test_architecture.py:92` greps a
  fixed name list; a new `/api/drive/engage` route passes. Only the *tool* allowlist is a real invariant.
  *Fix:* a route‑level fitness test — every mutating route calls the gateway or is on a reviewed allowlist.

### Theme C — Research‑grade intelligence (honest labels exist; epistemic content doesn't)
- **C1 [H/M/✅] — No calibration harness anywhere.** Of seven probabilistic‑looking outputs, one (zero‑failure
  reliability) is genuine; the rest are planted/hand‑tuned. *Fix:* `services/calibration.py` — randomized
  relapse cycles + noisy precursor → Brier, reliability diagram, AUC, lead‑time distribution on a read‑only
  route + card. **The single biggest lever** — gives the intelligence story a falsifiable number.
- **C2 [M/S/✅] — Stochastic precursor.** Replace the noiseless `0.20+0.06·i` ramp (`adapters/synthetic.py:71`)
  with a seeded degradation process so the forecaster faces real uncertainty (makes C1 meaningful).
- **C3 [H/S/✅] — Benefit numbers are constants.** FMEA `detection_without_agent` (`services/decision.py:111`),
  `diagnostic_confidence:0.7` (`agent/graph.py:319`). *Fix:* make them functions of live signals (forecast
  state, corroborating citations) so the improvement is *mechanical*, not asserted.
- **C4 [M/S‑M/✅] — SPRT `p1` reverse‑engineered to cycle 17** (`reliability_stats.py:71`). *Fix:* derive `p1`
  from a power target; ship the OC/ASN curves so the α/β "guarantees" are interpretable.
- **C5 [M/M/✅] — RAG is hashed bag‑of‑words but docstring says "semantic"** (`rag/embeddings.py:24`,
  `rag/retrieval.py:1`). *Fix:* local MiniLM (or no‑dep TF‑IDF+LSA) behind the existing `embed()` port +
  a paraphrase‑retrieval test; fix the docstring meanwhile. (Approval‑before‑similarity filter is already
  correct — the strongest RAG property.)
- **C6 [M/M/✅] — Reflexion loop is vestigial** (`agent/graph.py:172`) and the "never false‑closes" eval only
  exercises the deterministic spine. *Fix:* adversarial *draft* variants judged by a held‑out LLM (legitimate
  — judges *drafting*, never closure) + assert the injection doc never enters a model prompt.

### Theme D — Mind‑blowing, real, local data
- **D1 [H/L/✅] — Seeded generative physics core.** Replace the scripted per‑cycle lookup
  (`adapters/synthetic.py:50‑91`) with degradation‑as‑integrated‑state + physical coupling (wear→vibration→
  heat) + seeded Gaussian noise + **emergent** faults. Determinism via `default_rng((seed, machine_id,
  window_seq))` (no wall‑clock). Evaluator unchanged (same emitted keys). Preserve the hero (cycle‑17 relapse
  under a fixed seed).
- **D2 [H/M/✅] — Fleet seed.** N machines × M lines × P plants with varied baselines, each mapped to the
  existing 3‑class profile catalog, + a corpus of historical incidents (schema already supports it; today =
  one machine, one historical incident). Keep `northstar.IDS` stable so tests/deep‑links resolve.
- **D3 [M/M/✅] — Scenario library:** clean / relapse / slow‑degrade / partial / multi‑fault / sensor‑dropout /
  false‑alarm — gives the SPRT and forecaster real variety to prove themselves against.
- **D4 [M/M/✅] — Live fleet control‑room + what‑if injection** (beyond‑the‑pain): a deterministic tick
  advancing many concurrent incidents; replay/inject via the existing `POST /api/telemetry` seam so the
  *real* evaluator runs live on injected streams. Highest demo "wow per effort"; the UI shell + hierarchy
  already exist.

### Theme E — Integration realism & boundary honesty
- **E1 [H/M/⚠️] — Read‑side hexagon leaks.** `services/decision.py:45`, `services/reliability_stats.py:181`,
  `api/serializers.py` read `session.get(Machine/ProductionOrder/MaterialLot)` directly, so "swap only the
  composition root" is false for advisory/serializer reads. *Fix:* route those through `EfficastPort`
  (`get_machine_snapshot` exists) + a fitness test banning `session.get(Machine|…)` outside `adapters/`+`seed/`.
- **E2 [H/M/✅] — Prove agnosticism with a second protocol.** A loopback MQTT/UNS (or in‑proc) second
  `EfficastPort` impl swapped via `composition.build_port`, round‑tripping a snapshot in + verdict out —
  turns `EfficastApiPort`'s `NotConfigured` skeleton into a demonstrably swappable adapter. (Broker is
  optional; an in‑proc impl is fully local.)
- **E3 [M/S/✅] — ISA‑95/UNS overclaim.** `integration/isa95.py:8` says it's "the layer the agent reasons
  over" but nothing in `agent/` imports it. *Fix:* thread `asset_path` into the agent's perceive inputs, or
  soften the docstring. Also: Area level is synthesized from the line name (`isa95.py:50`).
- **E4 [L/S/⚠️] — In‑code honesty residual.** `reliability_stats.py:75` comment says priors are "from real
  historical incidents" — they're synthetic. Relabel as PROTOTYPE_ASSUMPTION. (Docs are clean.)

### Theme F — Frontend truthfulness & robustness + test rigor
- **F1 [H/S/⚠️] — `indicative` flag computed but never rendered.** DecisionPanel shows "50% relapse risk" +
  dollar figures when there's no live forecast (`components/mission/decision-panel.tsx:25`); the backend set
  `indicative:true` precisely to prevent this. *Fix:* neutral tone + "indicative" marker; mirror in ForecastPanel.
- **F2 [M/S/⚠️] — `recovery_progress` shown as a hero %** with no heuristic qualifier on the list/status strip
  (`mission-card.tsx:85`, `status-strip.tsx:31`). *Fix:* label "Progress (heuristic)" / step indicator.
- **F3 [H/S‑M/⚠️] — "Emergency pause — block all agent side effects" is client‑only state** (`command-bar.tsx:47`,
  `shell-context.tsx:17`) — blocks nothing server‑side. *Fix:* relabel "local only" or implement a real
  gateway breaker.
- **F4 [M/S/✅] — `--text-faint` fails WCAG AA** (~2.97:1, `globals.css:24`). *Fix:* lift to ≥4.6:1.
- **F5 [M/M/✅] — Per‑panel staleness never surfaced**; `OfflineState`/`PermissionDeniedState` are dead code.
  *Fix:* per‑panel stale chip from `dataUpdatedAt`; wire the dead states.
- **F6 [H/M/✅] — Frontend negative‑path tests almost entirely absent.** Panels are happy‑path‑only; the
  audit‑badge 3‑way logic and the `indicative` caveat are untested. *Fix:* parametrized error/empty/`available:
  false` per panel; audit‑badge test; indicative test; connection‑status test; harden the e2e role test to
  assert server‑side 403.
- **F7 [M/M/✅ + [infra]] — Backend test gaps:** no 2‑thread concurrency test (H8); no freshness‑at‑closure
  via the HTTP path. (True concurrent‑writer testing is **[infra]** on Postgres.)

### What's genuinely solid (do not "fix")
Deterministic evaluator solely owns closure (verified: zero violations found); agent self‑approval provably
blocked; write‑side gateway is a real 13‑stage choke point with a savepoint; the **allowlist** safety
invariant (`test_safety.py:152`); audit chain detects middle edit/delete/reorder + `UNIQUE(correlation_id,seq)`;
SPRT/argmin/risk‑scaling tests are real; the vacuous‑contract guard, any‑fault streak reset, fail‑closed
quality release, and freshness‑at‑closure (Phase 34); the Efficast **documentation** confidence‑tagging; the
3‑class profile catalog at the spec layer; the hexagonal *write* boundary + engine confinement.

---

## Phased execution plan
Small, tested units; preserve the hero scenario (VERIFIED_RECOVERY at cycle 17) after every unit; commit only
when asked.

- **Phase 35a — Honesty quick wins (in progress):** B1 (anon gate), B3 (honest provenance), A3 (serializer
  de‑hardcode). Each + a test. *Lowest risk, pure thesis.*
- **Phase 35b — Machine‑agnostic core:** A1 (key‑driven evaluator) + A2 (data‑driven reopen) + a second
  profile driven **end‑to‑end** through relapse→reopen→verify (the proof). Then A6/A5 (one source of truth)
  and A7 (liveness).
- **Phase 36 — Mind‑blowing data:** D1 (seeded generative physics) → D2 (fleet seed) → D3 (scenario library),
  preserving the hero under a fixed seed. Then D4 (fleet control‑room) as the demo headline.
- **Phase 37 — Research‑grade intelligence:** C2 (stochastic precursor) → C1 (calibration harness + card) →
  C3/C4 (mechanical benefit numbers, honest SPRT OC) → C5 (real embeddings) → C6 (adversarial draft eval).
- **Phase 38 — Safety/integrity hardening:** B4 (audit anchor) → B2 (ingest via gateway) → B5 (durable
  outbox, local parts) → E1 (port‑mediated reads + fitness test) → B7 (route fitness) → B6 (RBAC unify).
- **Phase 39 — Frontend truth + tests:** F1/F2/F3 (truthfulness) → F4/F5 (a11y/staleness) → F6 (negative‑path
  tests) → A4 (contract‑derived timeline) → F7 (backend concurrency/HTTP‑freshness tests).
- **Phase 40 — Integration proof:** E2 (second EfficastPort) → E3 (ISA‑95 wired or softened) → E4 (residual).

**[infra] deferred** (need Postgres/broker to verify honestly, not faked): real OIDC multi‑tenant isolation,
exactly‑once broker delivery, true concurrent‑writer audit‑fork tests, durable scheduler/outbox worker at scale.

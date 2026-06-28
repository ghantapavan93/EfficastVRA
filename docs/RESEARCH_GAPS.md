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

## Discovery questions — Efficast‑internal unknowns (to confirm, not assert)

Surfaced by the 12 discovery questions (answered in [`DISCOVERY_QA.md`](DISCOVERY_QA.md)). These concern
Efficast's *own* product/customers and cannot be verified by us; the prototype asserts none of them.

| # | Open question about Efficast | Assumption used | Confidence |
|---|---|---|---|
| D1 | What work stays manual after MAIA recommends/closes? | physical repair + human "it's fixed" judgment + WO close are manual; verification is the gap | INFERRED |
| D2 | Does MAIA prove production *recovered* after a WO is closed (vs just closing it)? | it closes; post‑close recovery proof is the gap we fill | INFERRED |
| D3 | Does Efficast auto‑reopen on fault recurrence within a window? | unknown | UNKNOWN |
| D4 | Does MAIA hold long‑running incident state across shifts? | unknown | UNKNOWN |
| D6 | What coordination still happens in WhatsApp/calls/spreadsheets post‑alert? | ad‑hoc triage/evidence/approval | INFERRED |
| D8 | Does Efficast unify machine/production/quality/lot/worker/planner into one incident? | unknown | UNKNOWN |
| D10 | Where in Efficast's architecture would a recovery agent sit? | as a read‑only verification layer + verdict publish‑back | INFERRED |

**Resolution path:** a discovery call with Efficast. Until then, our claims are scoped to *our* system
(proven by tests) and the integration is a *proposal* (`EFFICAST_INTEGRATION_SPEC.md`), not a contract.

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

**Deeper Efficast public-web sweep (2026‑06‑26).** A fuller read of `efficast.ai` (ES + `/en/`) plus
Argentine press was folded into [`EFFICAST_EVIDENCE_LEDGER.md`](EFFICAST_EVIDENCE_LEDGER.md) §D3, tagged
`VERIFIED (public site)` vs `REPORTED (third-party)`. New site‑verified detail: nine named modules; OEE
computed **live from the PLC ~every 15 s** (A/P/Q by asset/shift/order); AI agents that report, **close
work orders**, alert bottlenecks, and run a 24/7 WhatsApp supervisor; PLC/sensor/I‑O/WiFi/4G/Ethernet
connectivity for machines 2005+; single‑shift install; named customer logos; leadership (Carpman CEO,
Simons CRO); LatAm footprint; sales‑led pricing. Reported (not confirmed): founded 2023 in Rosario, a
US$1.5M seed round, and a CCU Innpacta win — recorded as press claims, asserted by us as fact **nowhere**.
- **Discovery questions sharpened, not resolved:** D2 (does MAIA prove *recovery* after a WO closes?) and
  D10 (where would a recovery agent sit?) are now better‑evidenced — the public surface shows MAIA *closes*
  OTs and computes live OEE, but describes **no post‑closure recovery‑verification / reopen‑on‑relapse**
  loop. That remains the prototype's distinct primitive (still `UNKNOWN` whether Efficast does it
  internally, E17). Resolution still requires a discovery call; no affiliation/partnership/API is claimed.

**Collaborations / customers / funding / market sweep (2026‑06‑26).** Four web‑grounded tracks added
`EFFICAST_EVIDENCE_LEDGER.md` §D4. Highlights (tagged there): CCU **Innpacta** win = US$10k prize +
*water‑efficiency* pilot (Fundación Chile official); ecosystem ties to Cancillería, BCR Startup Network,
ORT Uruguay incubator, ChileGlobal Ventures; **no technology/PLC/cloud/SI partners** (Efficast sells
vertical integration); 8 vendor‑attested customer logos (plastics‑heavy; only Plasticraft narrated; no
quantified results; **Heineken is NOT a customer**); **US$1.5M seed is a target, not confirmed closed**
(investors UNKNOWN; only confirmed money = the US$10k prize); team Carpman (CEO) + reported Plano (CMO),
Scavuzzo (CTO).
- **⚠️ Self‑correction:** a first‑pass page fetch had recorded a "**Jason Simons (CRO)**" as VERIFIED in
  the ledger D3/E25; the deeper sweep found **no public source** for that person. It has been **retracted
  to UNKNOWN** in the ledger and memory. (A reminder that even `VERIFIED (public site)` facts get
  re‑checked — the project's own evidence standard, applied to itself.)
- **Market read (INFERRED):** Efficast occupies an SMB · legacy‑machine · Spanish‑first · agent/WhatsApp
  niche; product‑shape peers are Guidewheel/FourJaw, with Tulip/MachineMetrics broader. The independent
  Verified Recovery layer stays defensible on **determinism + statistical proof + auditability + structural
  independence**, not on "having an agent."

**Deepest sweep (2026‑06‑27).** Four more tracks → ledger §D5 (MAIA teardown · edge/stack · founders &
media · per‑customer/ICP). Highlights: the **public agent is a single "MAIA"** WhatsApp persona (closes
OTs/reports/alerts; **gating mechanism UNKNOWN** — the seam our deterministic+gated+audited layer
contrasts); the multi‑agent console from the original screenshots is **not** public‑verifiable; the **edge
is a self‑installable wireless device** tapping PLC/Modbus/I‑O (OPC‑UA/MQTT/"Efficast Edge" name all
**unverified** — don't assert); software stack (from the CTO's GitHub) ≈ Postgres/Python/TypeScript‑React/
Flutter; founding arc = Inventu (2012) → "Un Respiro" ventilator (2020) → Efficast, **pivoting from
water‑efficiency cleantech (CCU) to general OEE/MES**; ICP = Santa Fe SME plastics‑injection + metalworking
shops (Molinos Cañuelas the marquee outlier).
- **⚠️ Re‑correction lesson (Jason Simons, full trail):** first‑fetch reported → recorded VERIFIED →
  §D4 press/LinkedIn sweep found nothing → **retracted to UNKNOWN** → §D5 site‑team‑section read confirmed
  it **is on the official site**. Net: **role listed on the site (VERIFIED); person's identity/background
  UNVERIFIED.** The retraction was an over‑correction — a reminder that *corrections themselves get
  re‑checked*, and that "absent from press/LinkedIn" ≠ "absent from the primary site." Don't assert the
  person's background; do record the role is site‑listed.

## Security-hardening assumptions (Phase 43, 2026-06-28)
All `PROTOTYPE_ASSUMPTION` (our deployment choices, env-tunable — not claims about Efficast or any external
system), surfaced live at `/api/security`:
- **Rate-limit defaults** (600 requests / 60s per identity) are illustrative, not tuned to a real workload.
  The limiter is **per-instance / in-memory** — multi-instance quotas need a shared store (Redis).
- **Body-size limit** (1 MiB) is a default guard, not a measured requirement.
- **Keyed audit signing is OFF by default** (`VRA_AUDIT_HMAC_KEY` empty). When enabled, the key is read from
  an env var — a real deployment sources it from a vault/KMS and rotates it. The SHA-256 hash chain is always on.
- **Security-event detection** is an in-process ring + structured log (SIEM-ready), not a wired SIEM.
- **TLS/HSTS** are deployment-stage; HSTS is off until TLS terminates at/above this service.

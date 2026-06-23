# Verified Recovery Agent

> **Work completed does not mean production recovered.**

An independent, **Efficast-aligned** prototype of an autonomous *Verified Recovery Agent* for
discrete manufacturing. It begins **after** a maintenance intervention is proposed or completed,
defines what successful recovery must look like as a machine-readable **Recovery Contract**,
requests the human evidence it is missing, observes the **real post-intervention trajectory**,
and then **closes, conditionally accepts, reopens, or escalates** the incident — refusing to let a
"work order complete" status masquerade as a recovered factory.

---

## ⚠️ Honest scope & disclaimers (read first)

- This is an **independent prototype**. It is **not** affiliated with, endorsed by, partnered with,
  or integrated with Efficast. "Efficast-aligned" means the prototype is *designed to sit on top of*
  a host MES via an adapter boundary; it uses **no** Efficast code, API, credentials, or private data.
- **All manufacturing data is synthetic and deterministic.** The "Northstar Packaging Plant",
  machines, sensors, lots, manuals, and faults are fabricated for demonstration.
- **No physical machine control exists.** There is no route, tool, or mock that starts, stops,
  restarts, modifies a PLC/set-point, bypasses an alarm/interlock, or confirms lockout/tagout. These
  are classified `PROHIBITED` and are enforced by the Agent Action Gateway and by an automated test.
- **The LLM is never the source of truth.** Reasoning is bounded; deterministic code evaluates the
  contract and owns all state. The full demo runs with **no API key** via a deterministic provider.
- Every Efficast-related claim in the docs is tagged `VERIFIED` / `OBSERVED` / `INFERRED` /
  `UNKNOWN` / `PROTOTYPE_ASSUMPTION`. See [`docs/EFFICAST_EVIDENCE_LEDGER.md`](docs/EFFICAST_EVIDENCE_LEDGER.md).

---

## What it does (the hero scenario)

Packaging Line 4's conveyor-drive assembly is faulting (F27), vibration/temperature/cycle-time
climbing, scrap rising, on production order **PO-2841** (8,420 units remaining). A coupling-alignment
correction is completed. The agent:

1. Drafts a **Recovery Contract** (machine + production + quality conditions, required evidence,
   approval gates, verification window, closure/reopening/escalation policy).
2. Blocks monitoring until **required human evidence** (post-alignment measurement, first-piece
   quality, technician completion, approval) exists and is **fresh + valid**.
3. Monitors the real cycle trajectory. Things look like they're recovering…
4. **At cycle 17, F27 recurs.** The agent **refuses closure**, marks the contract **violated**,
   **reopens** the incident, preserves the first intervention + evidence, and activates the
   **bearing-replacement contingency** (RC-1042 → V2) — which requires fresh approval.
5. After the second intervention, a new verification window runs **30 stable cycles**, quality
   release is enforced by a quality engineer, and **verified recovery** is published.
6. A **Knowledge Candidate** is created — explicitly *pending expert review*, never auto-approved.

Every step is real backend state, audited, and idempotent — not a scripted animation.

---

## Architecture at a glance

Three deliberately separated systems behind an adapter:

| System | Owns | Tech |
|---|---|---|
| **A. Manufacturing Evidence** | machines, sensors, orders, lots, quality, manuals, interventions, observations, provenance | SQLModel + SQLite (Postgres/pgvector in prod) |
| **B. Durable Operational Workflow** | incident & contract lifecycle, approvals, evidence requests, verification windows, reopening, escalation, audit, idempotency | DB-backed state machine (Temporal-compatible interface) |
| **C. Bounded AI Reasoning** | manual interpretation, requirement extraction, historical comparison, missing-evidence ID, contract drafting, explanations, summaries | `ReasoningProvider` (deterministic + optional hosted) |

System C runs as a **bounded agent graph** — a neuro-symbolic, Reflexion-shaped Plan-Executor. It
closes the full loop: a MAIA-style alert is triaged (`perceive → classify → retrieve → hypothesize →
propose`), a human accepts the proposed intervention, the contract is drafted (`draft → self-critique
→ decide`), and recovery is monitored (`observe/reflect`). Every step is recorded as an inspectable
reasoning trace (served at `/api/incidents/{id}/reasoning`, rendered in the **Agent Reasoning** tab;
the diagnosis is in the **Agent Diagnosis** tab and the **MAIA Alerts** inbox). The agent *proposes*;
the deterministic evaluator judges recovery and the gateway authorises actions — it never accepts its
own diagnosis, performs physical work, or controls a machine. Grounded in 2024-2026 research
([`docs/AGENT_RESEARCH.md`](docs/AGENT_RESEARCH.md), [`docs/AGENT_GRAPH.md`](docs/AGENT_GRAPH.md)) and
proven by a reliability eval that **never false-closes a relapse** (`python -m app.cli eval`).

All host-MES access crosses **`EfficastPort`** (`SyntheticEfficastPort` for the prototype;
`EfficastApiPort` is a documented real-integration skeleton). All model-proposed side effects cross
the **Agent Action Gateway** (schema → identity → plant scope → role → risk class → policy → approval
→ idempotency → circuit breaker → audit → execute → validate → transition). See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

The engine is **machine-agnostic** — equipment classes (conveyor, injection press, hydraulic pump, …)
are declared as data (`MachineProfile`) and verified by the same deterministic evaluator
([`docs/MACHINE_AGNOSTIC.md`](docs/MACHINE_AGNOSTIC.md)) — and **real-data ready**: a `TelemetrySource`
seam lets real readings (`POST /api/telemetry/{machine}`) drive verification in place of the synthetic
plant, with no other change ([`docs/REAL_DATA_INTEGRATION.md`](docs/REAL_DATA_INTEGRATION.md)). Every
mission also carries a plain-language **operator brief** (what happened · what to do now · who).

---

## Run it

> Designed to run with **just Python 3.11+ and Node 18+** — **Docker is optional**. SQLite and an
> in-process vector store are the defaults so there is nothing to provision for the demo.

**One command (after `install`):**
```powershell
./run.ps1 install      # Windows: backend + frontend deps      (or: make install)
./run.ps1 dev          # backend :8000 + frontend :3000, both hot-reload   (or: make dev)
```
`run.ps1` (Windows) and `Makefile` (macOS/Linux/Git-Bash) both expose `install · dev · backend ·
frontend · seed · reset · demo · eval · test`. Use **dev** (`next dev`) while developing — it
hot-reloads; `npm start` serves a production build and won't reflect edits without a rebuild.

Manual steps below if you prefer.

### Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
python -m app.cli seed              # build the deterministic Northstar scenario
uvicorn app.main:app --reload       # http://localhost:8000  (docs at /docs)
```

### Frontend
```powershell
cd frontend
npm install
npm run dev                          # http://localhost:3000
```

### Seed / reset / demo / test
```powershell
python -m app.cli seed     # load synthetic plant + scenario (idempotent)
python -m app.cli reset    # one-command wipe + reseed
python -m app.cli demo     # run the full PO-2841 recovery replay headless
python -m app.cli eval     # agent reliability eval — proves it never false-closes a relapse
python -m app.mcp_server   # Model Context Protocol server (read-only) — connect Claude/any MCP host
pytest                     # backend test suite (deterministic, no network)
cd ../frontend && npm test # frontend tests
```

Open [`docs/demo-film.html`](docs/demo-film.html) in a browser for a self-contained animated film of
the recovery story (monitoring → cycle-17 relapse → reopen → verified).

### Docker (optional, production-shaped: Postgres + pgvector)
```powershell
docker compose up --build
docker compose run --rm backend python -m app.cli seed
```

---

## Documentation

| Doc | Purpose |
|---|---|
| [`docs/SYSTEM_OVERVIEW.md`](docs/SYSTEM_OVERVIEW.md) | **Start here** — the whole system in depth (stack, architecture, every feature, flow) **+ an honest critique & prioritized gap list** |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System design (C4), boundaries, data flow |
| [`docs/adr/`](docs/adr/README.md) | Architecture Decision Records — the *why*, enforced by fitness functions |
| [`docs/PRODUCT_SCOPE.md`](docs/PRODUCT_SCOPE.md) | What this is / is not |
| [`docs/RECOVERY_CONTRACT.md`](docs/RECOVERY_CONTRACT.md) | The core primitive |
| [`docs/RECOVERY_FORECASTING.md`](docs/RECOVERY_FORECASTING.md) | **New primitive** — surfaces a degradation precursor that diverges *before* the fault recurs, as an early warning (advisory; a transform of one measured channel, not a learned probability) |
| [`docs/STATE_MACHINE.md`](docs/STATE_MACHINE.md) | States, transitions, guards |
| [`docs/AGENT_RESEARCH.md`](docs/AGENT_RESEARCH.md) / [`docs/AGENT_GRAPH.md`](docs/AGENT_GRAPH.md) | SOTA agent research (cited) & the implemented reasoning graph |
| [`docs/MACHINE_AGNOSTIC.md`](docs/MACHINE_AGNOSTIC.md) / [`docs/REAL_DATA_INTEGRATION.md`](docs/REAL_DATA_INTEGRATION.md) | Any-machine contract catalog & the real-data / Efficast-API seams |
| [`docs/INDUSTRY_LANDSCAPE.md`](docs/INDUSTRY_LANDSCAPE.md) / [`docs/INTEGRATION_ARCHITECTURE.md`](docs/INTEGRATION_ARCHITECTURE.md) | How real platforms deliver agents (cited) & our ISA-95/UNS connector layer |
| [`docs/AGENT_CAPABILITY_AUDIT.md`](docs/AGENT_CAPABILITY_AUDIT.md) / [`docs/MCP_INTEGRATION.md`](docs/MCP_INTEGRATION.md) | Top-grade agent capabilities vs. us (cited) & the read-only MCP server |
| [`docs/CROSS_INDUSTRY_RESEARCH.md`](docs/CROSS_INDUSTRY_RESEARCH.md) | Cross-industry agent research → the **Decision Intelligence** layer (risk-adjusted economics + FMEA) |
| [`docs/RELIABILITY_STATISTICS.md`](docs/RELIABILITY_STATISTICS.md) | **Recovery confidence** — zero-failure reliability-demonstration test + **Wald SPRT** (sequential accept/reject) + machine/fault-scoped bathtub-curve hazard |
| [`docs/PROVENANCE.md`](docs/PROVENANCE.md) | **Closure provenance & evidence trust** — why the outcome was decided, evidence ranked by provenance tier, proposed-vs-executed reconciliation, audit integrity |
| [`docs/ORGANIZATIONAL_LEARNING.md`](docs/ORGANIZATIONAL_LEARNING.md) | The **knowledge learning loop** — tribal knowledge → human-curated institutional memory (continual learning without weight updates) |
| [`docs/SECURITY_MODEL.md`](docs/SECURITY_MODEL.md) / [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) | Gateway, authz, OT safety, threats |
| [`docs/GOVERNANCE.md`](docs/GOVERNANCE.md) | Security · logging · auditability posture, mapped to IEC 62443 / ISO 27001 / SOC 2 / NIST / EU AI Act (live at `/api/governance`) |
| [`docs/OPERATIONS.md`](docs/OPERATIONS.md) / [`docs/INCIDENT_RESPONSE.md`](docs/INCIDENT_RESPONSE.md) | SLOs · ownership (RACI) · on-call · uptime, and the system-incident runbook |
| [`docs/EFFICAST_EVIDENCE_LEDGER.md`](docs/EFFICAST_EVIDENCE_LEDGER.md) | Tagged claims about Efficast |
| [`docs/REPOSITORY_AUDIT.md`](docs/REPOSITORY_AUDIT.md) / [`docs/LICENSE_AUDIT.md`](docs/LICENSE_AUDIT.md) | Phase-0 audit & licenses |
| [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) | Step-by-step demo |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | Test strategy & results |
| [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md) / [`docs/PRODUCTION_EVOLUTION.md`](docs/PRODUCTION_EVOLUTION.md) | Honest gaps & the path to prod |
| [`docs/FRONTEND_RESEARCH.md`](docs/FRONTEND_RESEARCH.md) / [`docs/DESIGN_DIRECTION.md`](docs/DESIGN_DIRECTION.md) / [`docs/INTERACTION_SYSTEM.md`](docs/INTERACTION_SYSTEM.md) / [`docs/ACCESSIBILITY.md`](docs/ACCESSIBILITY.md) | Forge System design |
| [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) | Attributions |

## License

Prototype source: MIT (see [`LICENSE`](LICENSE)). Third-party components: see
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and [`docs/LICENSE_AUDIT.md`](docs/LICENSE_AUDIT.md).

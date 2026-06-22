# Known Limitations

Stated plainly. This is a hackathon prototype optimised for **depth of one workflow**, not breadth.

## Scope
- **One scenario, one plant.** Northstar PO-2841 is fully wired; the system is not a general MES/CMMS
  and does not do multi-line optimization, scheduling, or planning.
- **Synthetic data & physics.** `ScenarioPhysics` is a deterministic narrative model, not a real
  drivetrain simulation. The cycle-17 relapse is intentional and reproducible, not learned.
- **Reasoning is deterministic by default.** The `DeterministicReasoningProvider` carries the demo.
  The hosted provider only enriches narrative text and is untested against a live endpoint here.

## Security / identity (demo-grade)
- Identity is an `X-VRA-User` header → seeded user. **No real IdP, tokens, password, or session.** Do
  not expose this beyond a local demo.
- No transport encryption, secrets management, rate limiting, or CSRF protection in the local profile.
- Synthetic telemetry is trusted as authentic; there is no device-signed provenance.

## Infrastructure
- **Default stack is single-node:** SQLite + in-process NumPy cosine retrieval + in-process worker.
  Concurrency is demo-level; SQLite is not for production write load.
- The **Docker Compose / Postgres + pgvector** path is provided and standard, but the *verified* path
  in this build is the local SQLite one; the Compose images were authored but not exhaustively
  run-tested in the build environment.
- The transactional **outbox** is written but its background publisher is a simple in-process drain,
  not a separate durable worker; there is no real external broker.

## RAG
- Embeddings are a **deterministic lexical hash** (no semantic model), good enough to demonstrate
  applicability/approval filtering and conflict detection, but not production retrieval quality.
  pgvector + real embeddings is the documented upgrade.

## Frontend
- Screens cover the required surfaces; it is **not** a full Efficast UI (no planner, inventory editor,
  generic dashboards).
- Live updates use polling (`refetchInterval`), not websockets/SSE.
- Automated **screenshot capture** was blocked by a tooling timeout in the build environment; the UI
  was instead verified functionally via live DOM inspection against the running backend (Mission
  Control, Contract, Timeline cycle-17 reveal, Outcome all confirmed rendering real state).
- Accessibility targets WCAG 2.2 AA with the patterns in [`ACCESSIBILITY.md`](ACCESSIBILITY.md);
  a full screen-reader + 400%-zoom manual sweep is recommended before any real use.

## Workflow
- Escalation and `CANCELLED` paths exist in the state machine but are lightly exercised by the demo.
- Verification windows advance by an explicit "advance cycles" action (demo controllability) rather
  than a wall-clock timer/scheduler.

See [`PRODUCTION_EVOLUTION.md`](PRODUCTION_EVOLUTION.md) for how each of these would be hardened.

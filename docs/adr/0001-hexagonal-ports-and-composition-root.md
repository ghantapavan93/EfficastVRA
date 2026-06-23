# ADR 0001 — Hexagonal architecture: explicit ports + a composition root

**Status:** Accepted

## Context
The prototype must run on deterministic synthetic data today, yet be replaceable by a real Efficast
MES, OPC-UA/UNS telemetry, and a hosted model later — without rewriting the application core. We do
not know Efficast's private APIs, so the boundary to the outside world must be explicit and narrow.

## Decision
Adopt a **ports-and-adapters (hexagonal)** structure:
- The outside world is reached only through **ports** (`app/ports/`): `EfficastPort` (host MES),
  `ReasoningProvider` (bounded LLM/deterministic reasoning), `TelemetrySource` (per-cycle readings),
  plus the notification and publish sinks.
- Adapters implement the ports: `SyntheticEfficastPort` / `EfficastApiPort` (skeleton),
  `DeterministicReasoningProvider` / hosted, `SyntheticTelemetrySource` / `IngestedTelemetrySource`.
- A single **composition root** (`app/composition.py`) decides which adapters are wired; driving
  adapters (API, CLI) ask it for a service rather than constructing ports themselves.

## Consequences
- Going to production changes *one file* (`composition.py`): swap `SyntheticEfficastPort` →
  `EfficastApiPort`, deterministic → hosted reasoner. The domain, evaluator, gateway, workflow, and UI
  are untouched.
- The core is testable in isolation (every test injects a synthetic adapter via the same seam).
- Enforced by `test_architecture.py` (the domain core imports no outer layer; the web layer is a
  driving adapter nothing else depends on).

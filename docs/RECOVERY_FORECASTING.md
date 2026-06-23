# Recovery Forecasting — a new primitive

**The novel idea:** conventional predictive maintenance forecasts equipment *failure* from raw sensors.
This forecasts **recovery** — it predicts whether a *specific repair actually worked*, **before** the
originating fault recurs. To our knowledge that is not something off-the-shelf industrial AI does; it
is the natural next step beyond the product's reactive "catch the false closure at cycle 17."

## How it works (`app/services/forecaster.py`)
At triage the agent raises two competing hypotheses (see [`AGENT_GRAPH.md`](AGENT_GRAPH.md)):
- **H1 — the intervention fixed it** (recovery holds), and
- **H2 — a latent fault will relapse** (e.g. drive-end bearing degradation).

During monitoring the forecaster scores, each cycle, which hypothesis the live trajectory supports. The
key signal is a **degradation precursor** the headline metrics mask — drive-end bearing high-frequency
vibration / crest factor (`RecoveryObservation.bearing_precursor`). Vibration, temperature, cycle time
and scrap can all look fully recovered while the precursor quietly rises; that divergence is the early
tell. It produces `P(holds)` vs `P(relapse)`, the competing-hypothesis support, and — when `P(relapse)`
crosses the warning threshold — a **predicted relapse cycle**.

## What it caught (verified, canonical scenario)
By **cycle 7** — with vibration ≤ 4.0 mm/s, temperature declining, scrap < 2% (everything "looks
recovered") and **no fault fired** — the forecaster flagged `P(relapse) = 0.87` and predicted a false
recovery. The real F27 fault does not recur until **cycle 17**: roughly **10 cycles of lead time** from
a signal the obvious metrics hide. Served at `GET /api/incidents/{id}/forecast` and over MCP
(`get_recovery_forecast`); rendered as the **Recovery forecast** panel on the verification timeline.

## Safety — advisory only
The forecaster **never decides, reopens, closes, or acts.** The deterministic evaluator still requires
a real condition violation to reopen, and a human still decides closure. So a wrong forecast can cause
**neither a false close nor a false reopen** — it only gives the team *earlier insight* (e.g. "don't
celebrate yet; this is diverging — pre-stage the bearing"). This keeps the entire trust model
([ADR 0002](adr/0002-deterministic-verifier-not-the-llm.md)) intact while adding genuine foresight.
Tested by `tests/test_forecaster.py` (predicts before the fault; confident for a genuine recovery;
state never changes).

## For real data
`bearing_precursor` is synthetic here; in a real deployment it is a standard condition-monitoring
feature (high-frequency band energy, crest factor, kurtosis, envelope analysis) streamed through the
telemetry seam ([`REAL_DATA_INTEGRATION.md`](REAL_DATA_INTEGRATION.md)). The forecaster logic is
unchanged — it consumes whatever precursor the machine class defines.

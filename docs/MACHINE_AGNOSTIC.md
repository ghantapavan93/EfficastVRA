# Machine-agnostic Recovery Contracts

The Recovery Contract is a **primitive**, not a conveyor scenario. The deterministic evaluator
(`app/services/evaluator.py`) already speaks a generic language — `CompareOp` (`LTE`, `WITHIN_PCT`,
`NOT_RECUR`, `DECLINING`, `COUNT_GTE`, …) over *arbitrary* metric keys — so any equipment class
described declaratively is verified, reopened, and closed by the same engine, unchanged.

## How it works
- A `MachineProfile` (`app/services/machine_profiles.py`) declares, **as data**, what recovery means
  for an equipment class: its signals + thresholds, the originating fault to watch, the stable-cycle
  window, the required human evidence, and the approval gates.
- `build_contract_from_profile(profile, …)` instantiates a fully-valid `RecoveryContractSpec` from it.
- Adding a new machine class is **data, not code** — append a profile to the catalog.

## Catalog (today)
| Equipment class | Models | Signals | Stable cycles | Fault |
|---|---|---|---|---|
| `conveyor_drive` | CDX-220 | vibration · temp trend · cycle time · scrap | 30 | F27 |
| `injection_molding_press` | IMX-90, IMX-160 | melt temp · injection pressure · cycle time · scrap | 25 | E12 |
| `hydraulic_pump` | HPU-50 | vibration · oil temp · discharge pressure | 20 | P09 |

Served at `GET /api/machine-profiles`. The Northstar conveyor keeps its hand-tuned template
(`contract_templates.py`) on the live path; `test_machine_profiles.py` asserts the conveyor *profile*
produces the **same condition set** as that template, so the catalog and the proven path agree.

## Every profile is guaranteed (by test) to produce
- an originating-fault `NOT_RECUR` condition (the reopening trigger),
- a `COUNT_GTE` stable-cycle window of the profile's required length,
- a human-gated quality condition + first-piece evidence,
- a technician measurement + completion sign-off before monitoring,
- supervisor (review) and quality-engineer (release) approvals — both with machine control explicitly
  `denied` (start/stop/restart/PLC/setpoint/alarm/interlock/LOTO/auto-quality-release).

## Adding a machine class (no code change to the engine)
1. Append a `MachineProfile` to `PROFILES` with its signals/thresholds/fault.
2. `profile_for_model("<model>")` resolves telemetry from a real machine to its profile.
3. Feed real readings through the telemetry seam ([`REAL_DATA_INTEGRATION.md`](REAL_DATA_INTEGRATION.md));
   the evaluator handles the rest.

This is what makes the prototype *compatible with any machinery* a host MES like Efficast connects —
the verification logic is universal; only the profile is per-class.

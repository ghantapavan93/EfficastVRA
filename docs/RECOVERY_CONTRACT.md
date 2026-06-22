# The Recovery Contract

The product's original primitive. A machine-readable agreement describing **what successful recovery
must look like** after an intervention — so a "work order complete" status can be tested against the
factory's real behavior. The model may *draft and explain* it; **deterministic code evaluates it**
(`app/services/evaluator.py`).

Schema: `app/domain/contract.py` (`RecoveryContractSpec`). Persisted as normalised, queryable rows
(`RecoveryContract` + `RecoveryCondition` + `EvidenceRequirement` + `ApprovalRequirement`) plus a JSON
`spec` snapshot for display and version comparison.

## What a contract represents
Incident · intervention · operational goal · machine / production / quality expectations · required
human evidence · approval gates · data-freshness requirements · verification window · closure /
reopening / escalation policy · **contract version** · **policy version**.

## Conditions
Each condition has: key, kind (`MACHINE|PRODUCTION|QUALITY`), label, comparison op, threshold, unit,
baseline, sensor tag / fault code, deadline (cycles | minutes | window), evaluated status + current
value, and a policy reference. Comparison ops: `<= < >= > == within_pct declining not_recur count_gte`.

### Northstar PO-2841 — contract RC-1042 (thresholds are PROTOTYPE_ASSUMPTIONs)
| # | Condition | Op | Target | Deadline | Source |
|---|---|---|---|---|---|
| C1 | Vibration RMS | ≤ | 4.0 mm/s | within 10 cycles | VIB-L4-01 |
| C2 | Temperature trend | declining | begins declining | within 15 min | TMP-L4-01 |
| C3 | Fault F27 non-recurrence | not_recur | F27 absent | across window | events |
| C4 | Cycle time vs baseline | within_pct | ±5% of 12.2 s | within 10 cycles | CYC-L4-01 |
| C5 | Scrap rate | < | 2.0 % | across window | production |
| C6 | Consecutive stable cycles | count_gte | ≥ 30 | window | derived |
| C7 | First-piece inspection | == | pass | window | quality evidence |

**Evidence (required before):** post-alignment vibration measurement (technician, ≤4.5, fresh ≤2h),
technician completion (technician), first-piece quality (quality engineer, pass) — *before quality
release*. **Approvals:** contract review (supervisor, before monitoring); quality release (quality
engineer, before closure). V2 adds the **release-contingency** approval (supervisor) granting reserve
BR-6205 / assign technician / begin second window.

## Deterministic evaluation
`evaluate(session, contract)` reads the active window's observations + validated evidence and returns
a verdict: `monitoring | violated | verified | insufficient_evidence`, plus per-condition status,
stable-streak, and `awaiting_quality`. Rules:
- A condition is **VIOLATED** if its deadline passes unmet, or (for `not_recur`) the fault recurs.
- A cycle is **stable** iff it satisfies every continuous machine/production condition and has no
  fault; the streak resets on any unstable cycle.
- **verified** requires: all machine + production conditions `PASSED`, ≥30 stable cycles, first-piece
  `PASSED` (validated quality evidence), **and** a quality-engineer `quality_release` approval.
- Stale or wrong-role evidence cannot satisfy a requirement (`app/services/evidence.py`).

## Versioning
RC-1042 **V1** verifies the coupling alignment. When V1 is violated at cycle 17, **V2** (bearing
replacement) is drafted; V1 is retained with `status=violated`, `superseded_by=V2`. The UI compares
versions side by side (Contingency tab).

## Why deterministic evaluation matters
The contract is auditable, reproducible, and safe: the same observations always yield the same
verdict, independent of any model. The model's role is to make the contract *understandable* and to
*explain* failures — never to decide closure.

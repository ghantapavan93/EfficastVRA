# Demo Script

The story: **"We almost closed this — and the agent caught what everyone would have missed."**

## Fastest path (headless replay)
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.cli reset      # fresh Northstar scenario at INTERVENTION_RECORDED
python -m app.cli demo       # drives the whole loop, prints each step
```
Expected tail:
```
⑥ cycle 17 — outcome=reopened → CONTINGENCY_AWAITING_APPROVAL
⑨ 30 stable cycles + quality release — outcome=verified → VERIFIED_RECOVERY
✓ VERIFIED_RECOVERY · reopened 1× · audit events 64 · knowledge candidate PENDING_REVIEW
```

## Guided UI demo (recommended for an audience)
1. Start backend + frontend (see [`README`](../README.md)). Open `http://localhost:3000`.
2. **Landing** → "Open live recovery mission". The recovery-trajectory animation previews the journey.
3. **Mission Control** shows the active mission `INC-2841` (state *Intervention recorded*, machine
   L4-CONV, PO-2841, 8,420 units remaining).
4. Open the mission. Click the floating **Demo** button (bottom-right) to open the demo controller,
   which calls **real backend endpoints** step by step:

| Step | What it does | Watch |
|---|---|---|
| 1 | Draft recovery contract | state → *Contract drafted*; RC-1042 v1 with 7 conditions |
| 2 | Submit evidence & approve | technician measurement (3.6 mm/s) + completion + supervisor approval |
| 3 | Begin monitoring | window 1 opens |
| 4 | Advance 16 cycles | **Timeline** trajectory trends down — looks recovered (resist the urge to close) |
| 5 | **Cycle 17 — F27 recurrence** | contract **violated**; calm red band: *"Recovery Contract violated at cycle 17 · Work completed. Recovery not proven. · Incident reopened automatically."* Incident reopens; **Contingency** tab appears |
| 6 | Approve bearing contingency | scope dialog shows what you ARE / are NOT authorizing; reserves BR-6205, assigns technician |
| 7 | Complete bearing replacement | technician evidence → window 2 opens |
| 8 | Advance 29 stable cycles | ticker shows green cells, no fault |
| 9 | Quality release | quality engineer passes first-piece + releases hold |
| 10 | Verify recovery (cycle 30) | state → **Verified recovery** |

5. **Outcome** tab: before/after (7.4→3.1 mm/s, 84→63 °C, F27 recurring → absent for 30 cycles),
   stable-cycle count, lots released, and the **Knowledge candidate** marked *Pending expert review*.
6. **Timeline** tab: full event spine + cycle ticker with cycle 17 highlighted; toggle metrics on the
   trajectory.

## Manual driving (without the demo controller)
Each mission's sticky **action bar** offers the contextual next step (Draft → Review & approve →
Begin monitoring → Advance cycles → Approve contingency → Complete → Release quality). Switch roles via
the top-right role switcher to perform technician/quality actions; the backend enforces authorization
and surfaces clear reasons when an action isn't permitted for your role.

## Command palette
`Ctrl/Cmd-K` → open mission, view contract/evidence/timeline/outcome, reset synthetic plant, replay
scenario, pause agent side effects. Machine-control commands are never offered.

## Reset
`python -m app.cli reset` or **Reset** in the demo controller / command palette. Deterministic — the
relapse always lands at cycle 17.

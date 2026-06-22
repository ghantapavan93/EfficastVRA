# Interaction & Motion System

Motion communicates **state, causality, progress, and confirmation** — never decoration.

## Motion tokens
| Token | Duration | Use |
|---|---|---|
| instant | 100ms | hovers, toggles, focus rings |
| fast | 170ms | popovers, tooltips, row expand |
| standard | 260ms | drawers, route transitions, condition status change |
| emphasis | 520ms | mission state transition, cycle-17 reversal, verified outcome reveal |

Easings: enter `cubic-bezier(.16,1,.3,1)` · exit `(.4,0,1,1)` · state-change `(.2,.8,.2,1)` ·
critical-alert `(.3,.7,.1,1)`. **Spring** only for direct-manipulation (drag/expand). All values live
in `--t-*` CSS vars and a `motion.ts` constants module shared with Framer Motion.

## Where motion is used
State changes · evidence arrival · contract-condition updates · timeline progression · approval
completion · **reopening** · drawer/command-palette transitions · route transitions (shared layout
on the mission object).

## Where motion is forbidden
Constant decoration · random floating cards · endless gradient movement · particles · unrelated
hover effects · spinning loaders for long-running work (use **meaningful progress labels**:
"Validating evidence", "Comparing recovery requirements", "Monitoring cycles", "Awaiting quality
approval", "Reopening incident").

## The cycle-17 reversal (signature moment)
1. Trajectory `actual` line bends down; an **event marker** appears at cycle 17 (F27 recurrence).
2. Affected condition rows transition `passing → violated` (color + icon + label + ring).
3. A ~120ms hold ("freeze for clarity"), then a diagnostic band slides in (failure/warning).
4. Three calm, sequential lines: *"Recovery Contract violated at cycle 17." → "Work completed.
   Recovery not proven." → "Incident reopened automatically."*
5. Total 300–700ms. **No flashing, no shake, no sound** (unless explicitly enabled). A polite ARIA
   live-region announces the violation + reopening for screen readers.
6. The mission progress rail **branches** into the contingency lane.

## Reduced motion (`prefers-reduced-motion`)
Trajectory animation and layout morphing are removed; transitions snap to final state. All state
**labels, icons, and announcements remain**. The cycle-17 reversal becomes an immediate state swap
plus the same diagnostic band and announcement — equally informative, just not animated.

## Direct-manipulation & feedback
Hover = 1px raise + `--line-strong`. Focus = always-visible 2px `--agent` ring. Press = scale .98.
Optimistic UI is **not** used for safety-relevant writes (approvals, closure) — those reflect
confirmed backend truth only. Numbers interpolate (`tween`) only for **non-safety** display values;
threshold/pass-fail values update discretely.

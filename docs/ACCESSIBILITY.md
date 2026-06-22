# Accessibility — Target WCAG 2.2 AA

Accessibility is a safety property here: an operator under pressure must never misread a recovery
state. State is therefore **never** communicated by color alone.

## Commitments
- **Color independence:** every state carries an icon + text label (and often a shape/ring).
  Pass = check + solid; violated = ✕ + ring; pending = dot + dashed; stale = clock.
- **Keyboard:** full operability; logical tab order; visible 2px `--agent` focus ring on every
  interactive element; `Esc` closes overlays; arrow-key nav in the command palette and lists.
- **Landmarks & headings:** one `<h1>` per page; ordered `h2/h3`; `<nav>`/`<main>`/`<aside>` regions
  with `aria-label`s; skip-to-content link.
- **Dialogs:** Radix Dialog focus-trapping, restore-focus on close, `aria-modal`, labelled title +
  description. Approval confirmations are dialogs, never `window.confirm`.
- **Live regions:** a polite `aria-live` region announces: recovery monitoring started · evidence
  missing · approval required · **Recovery Contract violated** · **incident reopened** · recovery
  verified. Critical alerts use `aria-live="assertive"` sparingly.
- **Reduced motion:** `prefers-reduced-motion` removes trajectory animation/layout morph; labels and
  announcements remain (see [`INTERACTION_SYSTEM.md`](INTERACTION_SYSTEM.md)).
- **Contrast:** body/label text targets ≥ 4.5:1 on its surface; large text/icons ≥ 3:1; focus ring
  ≥ 3:1 against adjacent colors. Token pairs chosen to meet this on `--surface-1/2/3`.
- **Targets:** interactive controls ≥ 24×24px (AA 2.2 *Target Size (Minimum)*); touch contexts
  (mobile evidence/approval) use ≥ 44×44px.
- **Zoom/reflow:** layouts reflow to 320px width / 400% zoom without loss; no horizontal scroll traps.
- **No flashing:** nothing flashes > 3×/s (cycle-17 uses a single controlled transition).
- **Charts:** every trajectory/sparkline has an accessible text summary (units, baseline, threshold,
  current, trend) via `role="img"` + `aria-label` and an adjacent visually-hidden description.
- **Forms:** labelled inputs, inline validation messages tied via `aria-describedby`, error summaries.

## Verification plan
- Automated: `@axe-core` checks in component tests; Playwright keyboard-only path through the hero
  scenario; a reduced-motion test; a modal focus-trap test; a command-palette keyboard test.
- Manual checklist (Phase 7): screen-reader pass on cycle-17 + approval; 400% zoom; tab-order sweep.

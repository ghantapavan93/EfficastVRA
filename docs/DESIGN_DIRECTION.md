# Design Direction — The FORGE SYSTEM

> "An autonomous industrial recovery command center designed for 2032, built with the restraint and
> usability required for a plant operating today."

Forge is dark-first, dense-but-breathable, and **earns** its futurism through information
architecture, interaction quality, and motion that always means something — not through neon or
decoration. It is deliberately **Efficast-aligned**: it keeps Efficast's warm-graphite canvas and
amber brand accent (so it reads as belonging on top of the host MES), then adds a disciplined
signal palette and a dedicated *agent-intelligence* color.

## North-star feelings
Reliability · Precision · Accountability · Intelligence · Safety · Momentum · **Human control**.

## 1. Color system (semantic tokens — never raw hex in components)

Dark-first. Values are the source of truth for `frontend/app/forge.css` / Tailwind theme.

### Surfaces (warm graphite, not pure black)
| Token | Value | Use |
|---|---|---|
| `--forge-bg` | `#0A0C10` | app canvas (slightly warm near-black) |
| `--forge-bg-raised` | `#0E1116` | sunken panels, rails |
| `--surface-1` | `#12151C` | cards |
| `--surface-2` | `#171B23` | elevated cards / popovers |
| `--surface-3` | `#1E232C` | menus, command palette |
| `--scrim` | `rgba(6,8,11,.72)` | modal backdrop |

### Borders / lines
| Token | Value | Use |
|---|---|---|
| `--line` | `#222834` | default hairline |
| `--line-strong` | `#323a48` | active/focused element border |
| `--grid` | `rgba(120,140,170,.05)` | low-contrast technical grid motif |

### Text
| Token | Value | Use |
|---|---|---|
| `--text-hi` | `#EEF2F8` | primary |
| `--text` | `#C2CAD6` | body |
| `--text-mut` | `#8A93A3` | secondary / captions |
| `--text-faint` | `#5C6573` | disabled / placeholder |

### Brand + signal (every state also carries icon/shape/label — never color-only)
| Token | Value | Meaning | Notes |
|---|---|---|---|
| `--brand` | `#F5A524` | Efficast brand / primary CTA | amber, the signature accent |
| `--brand-press` | `#D98A12` | pressed CTA | |
| `--agent` | `#4C7DFF` | **agent intelligence** / active reasoning / selected evidence | ion-blue, our addition |
| `--verified` | `#2DD4A7` | verified recovery / pass | controlled emerald, never fluorescent |
| `--pending` | `#FBBF24` | pending / awaiting | warm amber-gold |
| `--warning` | `#FB923C` | warning / degrading | industrial orange |
| `--failure` | `#FF5D5D` | violation / fail / reopened | controlled vermilion |
| `--approval` | `#8B7DFF` | human approval gates | violet/indigo (echoes Efficast agents screen) |
| `--evidence` | `#34D3D3` | evidence / provenance / data freshness | cool cyan |
| `--muted` | `#6B7686` | inactive / N/A | steel gray |

### Data-viz ramps
- Trajectory **actual**: `--agent` (in-progress) → `--verified` (passing) / `--failure` (violated).
- Trajectory **expected**: dashed `--text-mut`.
- Threshold line: `--warning`; baseline line: `--text-faint`; condition band fill: 8% alpha of state.

### Gradients (used *only* for: progression, primary CTA, subtle surface light, trajectory, agent)
- `--grad-brand`: `linear(135deg,#F5A524,#F2C14E)`
- `--grad-agent`: `linear(135deg,#4C7DFF,#7AA0FF)` — agent-active glow
- `--grad-progress`: mission rail fill, state-aware
- `--grad-surface`: `radial` 4% brand light at top of hero surfaces only

**Accessibility rule:** all state-bearing UI pairs color with an icon, a text label, and/or a shape
(pass = check + solid; fail = x + ring; pending = dot + dashed). Verified emerald is used *sparingly*.

## 2. Typography
- **Product sans:** Inter / Geist-style grotesk (system fallback stack) for UI + copy.
- **Mono:** JetBrains-Mono-style (`ui-monospace` fallback) for **IDs, metric values, timestamps,
  correlation IDs, policy/contract versions, evidence IDs** — always **tabular numerals**.

| Role | Size / weight / tracking |
|---|---|
| Display | 40–56 / 600 / -0.02em — mission identity & major outcome only |
| H1 | 28–32 / 600 / -0.01em — page / incident title |
| H2 | 20–22 / 600 — workflow section |
| H3 | 16 / 600 — card / evidence grouping |
| Body | 14–15 / 400 / 1.55 line-height |
| Technical label | 11–12 / 600 / **uppercase** / +0.08em — metadata (echoes Efficast section labels) |
| Metric | 14–22 / 550 / mono / tabular |
| Caption | 11–12 / 450 / `--text-mut` — source, freshness, confidence, timestamp |

No oversized marketing type inside workflow pages.

## 3. Spacing / radius / elevation
- **Base grid: 4px.** Step scale 4/8/12/16/20/24/32/40/56/72.
- Density: **comfortable** (default) and **compact** (operator) modes via a `data-density` attr that
  scales paddings/row heights; tablet adapts column count, not just shrinks.
- **Radius:** `--r-sm 6px`, `--r 10px`, `--r-lg 14px`, `--r-pill 999px`. No rounded-card overload —
  hairline borders + elevation do the separation work.
- **Elevation:** e0 flat → e3, via layered border + low-spread shadow + 1px inset top-light, never
  glow-on-every-card.

## 4. Motion tokens (see [`INTERACTION_SYSTEM.md`](INTERACTION_SYSTEM.md))
`--t-instant 100ms` · `--t-fast 170ms` · `--t-standard 260ms` · `--t-emphasis 520ms`.
Easings: enter `cubic-bezier(.16,1,.3,1)`, exit `(.4,0,1,1)`, state-change `(.2,.8,.2,1)`,
critical-alert `(.3,.7,.1,1)`. Spring only for direct-manipulation. **`prefers-reduced-motion`**
removes trajectory animation/layout morph and snaps to end state while preserving all labels.

## 5. Status / domain token sets
- **Recovery-state tokens** — one per workflow state (color + icon + label), e.g.
  `MONITORING_RECOVERY` = agent-blue pulse dot, `RECOVERY_FAILED`/`INCIDENT_REOPENED` = failure,
  `VERIFIED_RECOVERY` = verified, `*_AWAITING_*` = pending/approval.
- **Evidence-confidence tokens** — `valid` (verified), `stale` (warning + clock), `invalid`/
  `conflicting` (failure), `missing` (muted dashed), `pending` (pending).
- **Severity tokens** — `S1` failure / `S2` warning / `S3` pending / `S4` muted, always with a rank glyph.
- **Interactive-state tokens** — hover (raise + `--line-strong`), focus (2px `--agent` ring, always
  visible), active (press scale .98), disabled (40% + reason tooltip), selected (`--agent` left bar).

## 6. What we deliberately reject (and why)
Neon cyberpunk, glow-on-everything, big empty heroes inside the app, decorative particles, constant
pulsing, gratuitous 3D, gaming/hacker-terminal clichés, green-on-black, rainbow charts, pie/donut
gauges. Each obscures dense manufacturing data or fakes urgency — the opposite of the north-star.

See [`FRONTEND_RESEARCH.md`](FRONTEND_RESEARCH.md) for references studied and patterns retained vs
rejected, and [`ACCESSIBILITY.md`](ACCESSIBILITY.md) for the WCAG 2.2 AA commitments.

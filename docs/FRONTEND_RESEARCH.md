# Frontend Research

> Live web access was unavailable at build time (see [`RESEARCH_GAPS.md`](RESEARCH_GAPS.md)), so this
> records (a) **directly observed** primary material — the nine Efficast product screenshots — and
> (b) **prior-knowledge** interface conventions from well-known products, used only at the level of
> information architecture. No reference is recreated one-to-one; no proprietary asset is copied.

## A. Primary source: the Efficast screenshots (observed)
Studied: home, planner, production orders, worker view, quality, stock, reports, agents.

**Retained (because they fit manufacturing and read as "belongs on Efficast"):**
- Deep warm-graphite canvas; elevated cards with hairline borders; **amber/orange brand accent**.
- Emerald = good (OEE/Activo), coral-red = bad (atrasado/stopped), teal/blue = data, violet on the
  agents surface.
- **Uppercase tracked section labels** ("KPIS DEL TURNO", "INTERVENCIÓN DE CALIDAD PENDIENTE").
- **Monospace/tabular** order IDs, metrics, timestamps.
- Slim left icon rail + breadcrumb top bar + **right contextual rail** (orders to complete / pending
  quality interventions) — adopted as our right "intelligence/evidence" panel.
- Dense tables with per-column filter/sort; status pills; Pareto cause analysis; machine-state bars;
  work-order progress bars; colored-top-accent report cards.

**Rejected / reduced:** the marketing landing aesthetics (big hero) inside the app; broad
multi-module navigation (we ship a focused mission-oriented IA, not Dashboard/Analytics/Reports).

## B. Prior-knowledge conventions (information architecture only)
| Reference | Pattern retained | Why it fits | Rejected |
|---|---|---|---|
| Linear | command palette, keyboard-first, calm density, state pills | operators move fast under pressure | playful empties |
| Vercel/Geist | restrained dark surfaces, hairlines, mono for IDs | matches Efficast + credibility | over-minimalism that hides density |
| Sentry | issue→event timeline, severity, "what changed" | maps to incident→cycle timeline | noisy charts |
| Stripe | progressive disclosure, provenance drawers | evidence/source inspection | none material |
| Palantir/Anduril/control-room/aviation | mission framing, status strips, "human-in-command", high-density legibility | OT urgency + accountability | sci-fi prop theatrics |
| Retool | dense data cards, role-aware affordances | role experience | generic builder chrome |

## C. Patterns explicitly designed for *this* product
- **Expected-vs-actual recovery trajectory** with threshold band + cycle markers + the cycle-17
  event marker (no generic chart panels).
- **Agent vs human responsibility** split in the mission header (the agent coordinates digital
  verification; humans do physical work + approvals).
- **Recovery Contract as a structured agreement**, not a form.
- **Approval scope panel** that states what you *are* and *are not* authorizing (machine control
  always shown as not-authorized).
- **Cycle-17 reversal** as a controlled 300–700ms state change with an accessible live announcement,
  no flashing/alarm.

## D. Component-library strategy (21st.dev / shadcn / Radix)
Prefer Radix primitives + `cmdk` under a single Forge design layer. No component used unchanged; any
borrowed pattern is re-themed to Forge tokens, de-dependencied, simplified, made accessible, and
attributed in [`/THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md). One motion lib (Framer Motion),
one data layer (TanStack Query), one icon set (Lucide), hand-built SVG charts.

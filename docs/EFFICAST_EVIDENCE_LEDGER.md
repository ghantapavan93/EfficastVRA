# Efficast Evidence Ledger

Every statement this prototype makes about Efficast is tagged. The prototype's behavior depends on
**none** of these being a faithful description of Efficast's real product or internals.

**Tags**
- `VERIFIED` — confirmed against an authoritative Efficast source (none claimed here; live web
  verification was unavailable at build time).
- `OBSERVED` — directly visible in material supplied to this build (nine product screenshots +
  the landing-page image). Describes *surface UI/feature presence only*.
- `INFERRED` — a reasonable deduction from observed material; **not** asserted as fact.
- `UNKNOWN` — explicitly not known; we do not invent it.
- `PROTOTYPE_ASSUMPTION` — a choice made by *this* prototype, not a claim about Efficast.

> ⚠️ Live web verification (efficast.ai) was not available at build time (see
> [`RESEARCH_GAPS.md`](RESEARCH_GAPS.md)). Hence the strongest tag used for an Efficast fact is
> `OBSERVED`, never `VERIFIED`.

## A. Product surface (from supplied screenshots / landing image)

| ID | Statement | Tag | Source |
|---|---|---|---|
| E1 | Efficast presents an industrial intelligence / MES product with a dark, dense operations UI. | OBSERVED | all screenshots |
| E2 | A home/"Inicio" dashboard shows plant KPIs (OEE Promedio, Producción Total, Mejor/Peor OEE), per-machine activity tiles with status, "Órdenes próximas a completar", and cause analysis (Scrap/Paradas por causa, Pareto). | OBSERVED | `home.webp` |
| E3 | A "Vista de Operario" (Worker View) lets an operator register Production/Scrap/Parada, view shift KPIs (Disponibilidad/Rendimiento/Calidad/Scrap/Producido), machine-state bar, work-order progress, and an activity log. | OBSERVED | `worker.webp` |
| E4 | A "Calidad" (Quality) area runs quality checks/audits per machine & work order, with a "Intervención de calidad pendiente" queue. | OBSERVED | `calidad.webp` |
| E5 | A "Planificador de Producción" provides a machine-by-time Gantt with Día/Recursos/Hito views. | OBSERVED | `planner.webp` |
| E6 | "Órdenes de Producción" is a table of orders with Estado (Pendiente/En Progreso/Excepcional), Progreso, Cantidad, Fecha Límite, Inicio Prog/Real. | OBSERVED | `ordenes-de-produccion.webp` |
| E7 | "Stock / Productos" tracks Disponible / Por Producir / Por Consumir / Proyectado per SKU. | OBSERVED | `stock.webp` |
| E8 | "Reportes" offers dynamic + scheduled reports (Cadencia, KPIs del mes, Avance de Work Orders, Gestión de Incidencias, Histórico de Mantenimiento, …). | OBSERVED | `reportes.webp` |
| E9 | Efficast surfaces multiple named AI agents (e.g. **Maia/MAIA**, Mirko, Claw, Mundia, Susan, EVA) with active/stopped toggles, per-agent message IN/OUT counts, and per-agent **cost** tracking (hoy/mes/total). | OBSERVED | `agentsv2.webp` |
| E10 | Landing copy positions the product around "your factory stops being a black box", real-time visibility, AI agents (MAIA), smart planning, quality & traceability, actionable reports, and edge hardware; cites OEE-improvement / downtime-reduction marketing stats and named manufacturer logos. | OBSERVED | landing image |
| E11 | The UI language includes Spanish; the visual system is dark graphite with amber/orange brand accent, emerald "good", red "bad", teal/blue data, monospace IDs/metrics. | OBSERVED | all screenshots |

## B. Capabilities the brief attributes to Efficast (treated as context, not verified)

| ID | Statement | Tag |
|---|---|---|
| E12 | Machine/sensor/PLC/IIoT connectivity, "Efficast Edge", Live View, WhatsApp/email notifications, bottleneck ID, some automated operational actions. | INFERRED from brief + E10; not independently `VERIFIED` |
| E13 | "MAIA and additional AI agents" perform monitoring/analysis/alerting. | OBSERVED (agents exist, E9) + INFERRED (their exact function) |

## C. Efficast internals — explicitly UNKNOWN (never invented)

| ID | Statement | Tag |
|---|---|---|
| E14 | Efficast's private APIs, DB, data model, schemas, IDs. | UNKNOWN |
| E15 | Cloud provider, model provider, agent framework, retrieval/memory/prompt design. | UNKNOWN |
| E16 | Orchestration layer, security model, internal roadmap. | UNKNOWN |
| E17 | Whether Efficast has any "recovery contract" / post-intervention verification concept. | UNKNOWN — this is **our** original primitive |

## D. This prototype's own choices (not Efficast facts)

| ID | Statement | Tag |
|---|---|---|
| P1 | "Northstar Packaging Plant", Packaging Line 4, PO-2841, fault code **F27**, sensor IDs (VIB-L4-01…), bearing part BR-6205, all thresholds, all manual text. | PROTOTYPE_ASSUMPTION |
| P2 | `EfficastPort` method names/shapes (`get_machine_snapshot`, `publish_recovery_decision`, …). | PROTOTYPE_ASSUMPTION — a plausible adapter, **not** Efficast's real API |
| P3 | Roles supervisor/technician/quality_engineer/plant_admin. | PROTOTYPE_ASSUMPTION |
| P4 | The Recovery Contract schema, the 16 workflow states, the Agent Action Gateway pipeline. | PROTOTYPE_ASSUMPTION (original design) |

## D2. Web verification addendum (2026-06-21)

Live verification of `https://efficast.ai` later became available and **corroborated** the screenshot
observations. The following are upgraded to `VERIFIED (public site)` — describing Efficast's *publicly
marketed* product only, never its private internals:

| ID | Statement | New tag |
|---|---|---|
| E1/E10 | Efficast is a real industrial IoT / OEE / MES platform with a dark operations UI and marketed AI agents. | VERIFIED (public site) |
| E9/E13 | A **MAIA** agent exists and is marketed as reporting, closing work orders, alerting on bottlenecks, and answering operational questions ("AI supervisor on WhatsApp"). | VERIFIED (public site) |
| E12 | PLC/sensor-sourced data, single-day install, legacy-machine compatibility, hardware+software+AI offering. | VERIFIED (public site) |

**Notably**, public sources indicate MAIA can *close work orders*. That makes this prototype's thesis
sharper, not weaker: our agent verifies whether **production actually recovered after** an intervention/
work-order is completed — a distinct, complementary post-closure verification loop. Efficast's private
APIs, data model, security model, and roadmap (E14–E17) remain **UNKNOWN** and are not asserted.

## E. How alignment is kept honest in the product

- A persistent badge — **"Synthetic manufacturing environment · Independent Efficast-aligned
  prototype"** — is shown in the app shell (not hidden in a footer).
- The adapter boundary (`EfficastPort`) is the *only* contact point a future authorized integration
  would replace; nothing else assumes Efficast internals.
- No screenshot asset, proprietary illustration, or wording is reproduced in the shipped UI; the
  screenshots informed *design language* (color/typography/density), not copied layouts.

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
- `VERIFIED (public site)` — stated on Efficast's public website (efficast.ai). Verifies *what the site
  says* — the publicly marketed product — never private internals.
- `REPORTED (third-party)` — stated by credible third‑party press/sources; **not** independently
  confirmed and **not** asserted by this prototype as fact (e.g. funding, awards, founding details).

> Live web verification of `https://efficast.ai` became available after Phase‑0 and was used in the D2
> (2026‑06‑21) and **D3 (2026‑06‑26, deeper sweep)** addenda below. Site‑stated facts are tagged
> `VERIFIED (public site)`; third‑party press facts are tagged `REPORTED`. Private internals remain
> `UNKNOWN`. The prototype's behavior depends on none of it.

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

## D3. Deeper public-web sweep (2026‑06‑26)

A fuller read of `efficast.ai` (Spanish site + `/en/` pages) plus third‑party press. Site‑stated facts
are `VERIFIED (public site)`; press facts are `REPORTED` (not independently confirmed; the prototype
asserts none of them). Sources listed at the end of this section.

### D3.1 Product, as marketed on efficast.ai — `VERIFIED (public site)`

| ID | Statement | Tag |
|---|---|---|
| E18 | **Positioning:** "Inteligencia Industrial IoT" / "Tu empleado de IA industrial · 24/7" / "Habla con tu planta, en tiempo real." Single‑vendor "hardware + software + AI + support." | VERIFIED (public site) |
| E19 | **Nine modules** are marketed: (1) Live View, (2) Planner (Gantt drag‑&‑drop + load simulation), (3) Production Orders (OF/OT/sequences unified, traceable to operator/machine/shift), (4) Automatic OEE, (5) Worker View (shop‑floor tablet: start/end OT, log downtime w/ cause, quality checks), (6) Quality (mandatory checks per OT, traceable rejections + scrap reason), (7) Stock & Traceability (RM/WIP/FG linked to operator/shift/order), (8) Reports (drag‑&‑drop builder, email scheduling, plant templates), (9) AI Agents. | VERIFIED (public site) |
| E20 | **OEE is computed live from the PLC, updating ~every 15 s**, broken out as Availability / Performance / Quality, by asset, shift, and order — "no spreadsheets." (Illustrative dashboard shows OEE 78.4% = 92%·87%·98%; an *example*, not a customer metric.) | VERIFIED (public site) |
| E21 | **AI agents** (MAIA et al.) are marketed to: build reports autonomously, **close work orders (OTs)**, alert on bottlenecks, answer "how are we doing?" conversationally, and act as a **24/7 WhatsApp supervisor**. | VERIFIED (public site) |
| E22 | **Connectivity:** PLC · sensors · I/O · WiFi · 4G · Ethernet; **machines model‑year 2005 or newer**; **single‑shift install** with production running. | VERIFIED (public site) |
| E23 | **Named on the site as customers:** Gemplast, Bustinza Goma, Fadep, Fundemap, Molinos Cañuelas, Plásticos FR, Plasticraft, Textil Calchaquí. (Recorded as *logos shown on the vendor site*; the depth of each relationship is UNKNOWN.) | VERIFIED (public site) that the logos are shown; relationship depth UNKNOWN |
| E24 | **Geography:** marketed across Argentina, Uruguay, Paraguay, México; "Diseñado en Argentina." | VERIFIED (public site) |
| E25 | **Leadership & team** — full roster in §D5.1 (from the official site team section). Headline: **Simón Carpman (CEO)**; **Jason Simons (CRO, USA)**; **Iván Bercovich (Advisor, USA — notably built Graphiq, the NLU/Q&A engine behind Amazon Alexa)**. The site lists **no "CTO"/"CMO"**: Lautaro Scavuzzo = "Full Stack", Nahuel Plano = "Expansion Manager" (the CTO/CMO titles on data‑aggregators are stale). Contact `info@efficast.ai`. ⚠️ See the **re‑correction note in §D5.0** on "Jason Simons." | Roles **listed** = VERIFIED (site); "Jason Simons" *identity/background* UNVERIFIED |
| E26 | **Pricing is sales‑led** (no public price list); a free trial ("Empezá gratis") + "contact an advisor" are the CTAs. | VERIFIED (public site) |

### D3.2 Company context — `REPORTED (third-party)` (not asserted as fact)

| ID | Statement | Tag |
|---|---|---|
| E27 | Founded **2023**, originating in **Rosario, Argentina**; verticals AI / Industry 4.0 / IoT. | REPORTED (third‑party press) |
| E28 | A **US$1.5M seed round** was reported (raised/closing for LatAm expansion, 2024). | REPORTED — funding; not confirmed closed; not asserted |
| E29 | Won **CCU Innpacta** (7th edition, an open‑innovation challenge run by drinks group CCU + ChileGlobal Ventures), 2024; featured by Argentina's foreign‑ministry "Next from Argentina." | REPORTED — award/recognition; not asserted |
| E30 | Press describes deployments in sectors such as beverage, plastics, and aluminum casting. | REPORTED; consistent with E23 logos |

### D3.3 What the deeper read sharpens (fit) — `INFERRED`

Efficast's *public* surface is **detect → monitor (live OEE from PLC) → plan → execute (OT/quality/stock)
→ and AI agents that report and CLOSE work orders**. It does **not** publicly describe a *post‑closure
recovery‑verification* loop (prove the line actually recovered after the OT closed; reopen on relapse;
intervention‑consistency/causal read). That gap is exactly this prototype's primitive — so the Verified
Recovery Agent **complements** Efficast (a read‑only verification layer that would consume Efficast events
and publish a verdict back), rather than duplicating its monitoring/closing. This is `INFERRED` from the
public surface; whether Efficast already does any of it internally remains **UNKNOWN** (E17). No
affiliation, partnership, or API access is claimed.

### D3.4 Sources (public, 2026‑06‑26)
- efficast.ai — home (ES) + `/en/homes/` + `/en/pricing-en/` (product, modules, OEE‑from‑PLC, agents,
  connectivity, named logos, leadership, sales‑led pricing).
- Argentine press for E27–E29: *El Ecosistema Startup* (funding), *Startups Latam* / *El Litoral* /
  *Rosario3* / *Infonegocios* (CCU Innpacta win), Argentina MFA *Cancillería* "Next from Argentina."
  Treat as reported, not confirmed.

## D4. Collaborations, customers, funding & market — deep sweep (2026‑06‑26)

Four parallel web‑grounded research tracks. Tags as before; primary/official sources raise confidence
above press. **The prototype asserts none of this as fact and claims no affiliation.**

### D4.1 Collaborations & ecosystem — `VERIFIED (official)` unless noted

| Partner / Program | Type | What it involved | Confidence |
|---|---|---|---|
| **CCU Innpacta (7th ed.)** | Corporate open‑innovation challenge (CCU + ChileGlobal Ventures / Fundación Chile) | Efficast **won 1st** (100+ entrants, 22 countries), Apr 2024 — prize **US$10,000 + a pilot opportunity**. The use‑case was **industrial water‑consumption efficiency**, not OEE. | VERIFIED (Fundación Chile official) |
| CCU plant pilots — Ciudadela (AR), Pan de Azúcar (UY) | Corporate PoC | Reported water‑monitoring pilots followed the win. Conversion to a paid rollout is **not confirmed**. | REPORTED (press) |
| **Cancillería "Next from Argentina"** | Gov export‑promotion | Official MFA startup profile (founded 2023, SAS, ~12 staff, "validation" stage). | VERIFIED (gov) |
| **BCR Startup Network** (Bolsa de Comercio de Rosario) | Startup network | Added Mar 2025 ("Industry 4.0 via AI + IoT"). | VERIFIED (BCR Innova) |
| **ORT Uruguay — CIE incubator** | University incubator | Listed active incubated venture (2025); CEO has ORT background. | VERIFIED (ORT) |
| URUCAP / angel Robert Campbell (UY) | Investor/ecosystem | Reported Uruguayan angel support; coworking presence. | REPORTED (single outlet) |
| **Technology / cloud / PLC / SI / distributor partners** | — | **None disclosed.** Efficast's Partners page lists **only customers** and stresses an **in‑house, end‑to‑end** model (HW+SW+AI+support, one vendor). | UNKNOWN (no evidence) |

**Signal:** the flagship "partnership" is a **won competition** (validation + a logo + a sponsored pilot), not a commercial alliance; the verifiable ties are **public‑sector / accelerator scaffolding** (gov, BCR, Fundación Chile, ORT). Efficast deliberately sells **vertical integration**, not a tech‑partner ecosystem.

### D4.2 Customers & sectors

- **Eight logos on the site under "empresas que ya miden con Efficast"** (vendor‑attested *measuring* relationship, stronger than logo‑only but **no per‑customer figures**): Gemplast, Bustinza Goma, Fadep, Fundemap, Molinos Cañuelas, Plásticos FR, Plasticraft, Textil Calchaquí. `VERIFIED (vendor)` that they're listed; relationship depth `UNKNOWN`.
- **Only one narrated story: Plasticraft** (plastic injection, Rosario) — qualitative only, **no quantified result**. `REPORTED`.
- **Sector mix = plastics‑heavy** (≈4/8: Plasticraft, Gemplast, Fadep, Plásticos FR) + foundry/aluminum (Fundemap), rubber (Bustinza Goma), technical textiles (Textil Calchaquí), food/milling (Molinos Cañuelas, the lone large enterprise). `VERIFIED` from the mix.
- ⚠️ **Heineken is NOT an Efficast customer** — it appears only via CCU's regional licensing; do not list it. The **site dashboard numbers (OEE 78.4% etc.) are a generic UI demo**, not a customer result. **"Plásticos FR" is not independently verifiable** as a company (logo only). `REPORTED / UNKNOWN`.

### D4.3 Funding & team

- **US$1.5M seed is NOT confirmed closed** — every source says *seeking/opening* ("busca cerrar"). **No named investors, no valuation, no close date.** A prior small round is mentioned but undocumented. The **only confirmed external money is the US$10k Innpacta prize** (non‑dilutive). `REPORTED (target) / UNKNOWN (investors)`.
- **Team (~12 staff, gov; "2–10" on LinkedIn):** Simón Carpman (CEO, mech. eng. UNR, ex‑Tenaris), **Nahuel Plano (CMO)**, **Lautaro Scavuzzo (CTO)** — *no "Jason Simons."* Stage self‑described **"validation," B2B**. `VERIFIED (Carpman) / REPORTED (others)`.
- **Entity:** Argentine **SAS**, Rosario (San Martín 3773); a **"Efficast Inc"** US‑facing brand appears on LinkedIn but **no US incorporation confirmed**. Founding year **2023 (gov)** vs ~2022 (some press) — minor conflict. Revenue/ARR/customer‑count **never disclosed** ("doubled initial 2023 expectations" — qualitative). `REPORTED`.

### D4.4 Market & competitive read — `INFERRED` analysis

- **The opportunity is the gap:** LatAm SMB manufacturing is largely un‑digitized ("9 of 10 record production on paper," per Efficast's gov profile; IDB confirms very low Industry‑4.0 adoption, micro‑firms ≈90% of units). LatAm "AI in manufacturing" is a small but fast‑growing market (third‑party est. ~26% CAGR — *vendor estimate, not audited*).
- **Closest product‑shape peers:** **Guidewheel / FourJaw** (machine‑agnostic clamp‑on OEE, fast install). Broader field: **Tulip** (no‑code app platform, ~$120M Series D), **MachineMetrics** (CNC depth + "MaxAI"), **L2L**, **Worximity**, **Evocon**, **AspenTech/GE APM** (enterprise/process). **No dominant, well‑funded LatAm‑native productized peer surfaced** → a relatively open regional field.
- **Efficast's niche & moat:** the **SMB · legacy‑machine · Spanish‑first · agent‑led · WhatsApp‑native** corner. Its defensible edge is **GTM + interaction model** (LatAm‑native support, Spanish, an agent that *acts* — closes WOs, answers on WhatsApp), **not** core technology (the clamp‑on/OEE concept is commoditizing; an LLM "agent" is easy to copy).

### D4.5 Implications for the Verified Recovery Agent — `INFERRED`

Efficast/MAIA's loop ends at **"close the work order"**; our layer begins exactly there (a closed WO ≠ a recovered line → verify recovery, reopen on relapse). **Complementary, not substitutive.** But because incumbents could extend "close" → "confirm it stayed fixed," the wedge is defensible **only on what we already build**: a **deterministic, verdict‑owning evaluator** (not an LLM), **statistical rigor** (SPRT, calibration/Brier, freshness‑at‑closure), a **signed/audited governance gateway**, a **strict no‑physical‑control advisory posture**, and **structural independence** (a read‑only, host‑agnostic verifier is more trustworthy than one owned by the vendor that closed the WO). **Do not** position on "having an agent." This sharpens — not changes — the frozen architecture.

### D4.6 Sources (public, 2026‑06‑26)
Official/primary: [Fundación Chile — Innpacta winner](https://fch.cl/noticias/solucion-que-gestiona-y-optimiza-el-consumo-de-agua-industrial-gano-7-edicion-de-innpacta/) · [Cancillería — Next from Argentina](https://cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/efficast-ia) · [BCR Innova](https://www.innova.bcr.com.ar/node/210) · [ORT Uruguay CIE](https://cie.ort.edu.uy/emprendimientos/efficast-ai) · [efficast.ai partners](https://efficast.ai/en/partners-en/). Press: [Ecosistema Startup](https://ecosistemastartup.com/efficast-ia-para-fabricas-y-ronda-de-us15m/) · [SomosPymes](https://www.somospymes.com.ar/casos-exito/efficast-la-startup-rosarina-que-revoluciona-la-industria-argentina-produccion-inteligente-n5396663) · [Startups Latam](https://startupslatam.com/efficast-gana-7-edicion-del-desafio-innpacta-de-ccu/) · [Rosario3](https://www.rosario3.com/informaciongeneral/Una-startup-rosarina-gano-el-CCU-Innpacta-20240417-0034.html) · [Tekios](https://tekiosmag.com/2024/04/24/startup-argentina-efficast-gana-concurso-ccu-innpacta-de-innovacion-en-eficiencia-hidrica/). Market: [IDB digital‑transformation LAC](https://publications.iadb.org/en/360-digital-transformation-firms-latin-america-and-caribbean) · competitor sites (Tulip/MachineMetrics/Guidewheel/FourJaw/L2L). *Market sizes are third‑party vendor estimates; funding/traction rest on single‑outlet reporting; investors UNKNOWN.*

## D5. Deepest sweep — agent, hardware, team, history, per‑customer (2026‑06‑27)

Four more web‑grounded tracks (MAIA teardown · edge/stack · founders & media · per‑customer). Same tags.

### D5.0 ⚠️ Re‑correction: "Jason Simons (CRO)" — the full, honest trail
This is the integrity discipline applied to itself, end to end: (1) a first page fetch reported **Jason Simons (CRO)**; (2) the §D3 entry recorded it as VERIFIED (public site); (3) the §D4 sweep's press/LinkedIn tracks found **no** trace and I **retracted it to UNKNOWN**; (4) the §D5 founders track then confirmed the name **is literally on the live efficast.ai team section** ("Jason Simons — Chief Revenue Officer · CRO · USA"). **Net resolution:** the **role‑listing on the official site is VERIFIED**; the **person's real identity/background is independently UNVERIFIED** (no resolvable LinkedIn/press). So: the retraction was an over‑correction; the right statement is "site‑listed, identity uncorroborated — don't assert the person's background." (Lesson logged in `RESEARCH_GAPS.md`.)

### D5.1 Team roster — `VERIFIED (official site team section)` (identity/background confidence varies)
| Name | Role (as on efficast.ai) | Note |
|---|---|---|
| Simón Carpman | **CEO / founder** | Mech‑eng UNR; founded **Inventu** (2012, custom machinery); led **"Un Respiro"** COVID ventilator (2020, Inventu+UNR); ex‑Tenaris (reported). |
| Jason Simons | **CRO · USA** | Listed on site; identity/background **UNVERIFIED** (see D5.0). |
| Iván Bercovich | **Advisor · USA** | Built **Graphiq** → the NLU/Q&A engine behind **Amazon Alexa** (acquired by Amazon); now Partner, ScOp VC. Explains the "Alexa for manufacturing" framing. |
| Nahuel Plano | **Expansion Manager** (Mexico) | Aggregators say "CMO" — **stale**. |
| Lautaro Scavuzzo | **Full Stack** | Aggregators say "CTO" — **stale**; **the site lists no CTO**. GitHub stack: PostgreSQL · Flutter · TypeScript · Python. |
| Javier Rambaldo | Full Stack + **Embedded** | R&D / IoT. |
| Agustín Rambaldo | Front End + **AI** | AI automation. |
| Nicolás Midulla | **Electronics · PCB** | In‑house board design. |
| Juan Manuel "Toto" Cena | Electronics · Math | |
| María Laura Cornalo Bassan | Scrum Master | |
| Leandro Pubill | **Plant implementation** (Mexico) | Field device install. |
| Pablo Ortiz | **Country Manager · Uruguay** | |
| Sebastián Vottero | Commercial & Expansion · LatAm | |

Team ≈ a genuine HW+SW+AI vertical team (embedded/PCB · IoT infra · full‑stack · mobile/Flutter · AI/ML · field install). The **US presence (CRO + advisor)** signals US‑investor/market ambition.

### D5.2 MAIA agent teardown — `VERIFIED (site)` capabilities; mechanism `UNKNOWN`
- Public agent = **one persona, "MAIA"**, marketed as a **24/7 WhatsApp "industrial AI employee"**: *"arman reportes, cierran OTs, avisan cuellos de botella y contestan '¿cómo venimos?' sin que abras un dashboard"* + writes the shift closure. The **multi‑agent console in the original screenshots (Mirko/Claw/Mundia/Susan/EVA, per‑agent cost)** has **no public footprint** — likely an older/internal build (E9 stays OBSERVED‑from‑screenshots; not public‑verifiable).
- **The load‑bearing claim — that the agent *closes* work orders — is marketing‑stated but never publicly demonstrated, and its gating (confirmation/role/write‑back) is `UNKNOWN`.** No public mention of the LLM/model, framework, or guardrails. *This is exactly the seam our deterministic, gated, audited verification layer contrasts against.*

### D5.3 Hardware / protocols / stack
- **Edge:** an **Argentine‑designed, self‑installable wireless IoT device** that taps the machine (**PLC / Modbus / I‑O / "if it has a cable…"**) and backhauls over **WiFi/4G/Ethernet**; machines **2005+**; **single‑shift install**; **~15 s** cadence. In‑house PCB design. ⚠️ **NOT publicly verified:** the product name **"Efficast Edge"**, **OPC‑UA**, **MQTT/Sparkplug**, fieldbuses, vibration/temperature sensing, cloud provider, OTA — do not assert.
- **Sensed:** cycle/piece counts, machine on/off + stop‑cause, scrap/quality, **energy (kWh)**, and **water flow** (flagship via the CCU pilot). 
- **Software stack** (from CTO's public GitHub + roles, `INFERRED`): PostgreSQL · Python (ML) · TypeScript/React/Node (web) · **Flutter** (Worker‑View tablet/mobile). No public company GitHub/firmware.

### D5.4 Founding history & the water→OEE pivot — `REPORTED`
Inventu (2012) → "Un Respiro" ventilator (2020) → Efficast (**2022/2023**, sources differ). **Original positioning was water‑efficiency cleantech** (the CCU Innpacta win, Apr 2024, was a *water‑consumption* device + AI assistant) → **broadened to general live‑OEE/MES + the MAIA agent**; the current site has dropped the water‑only framing. Self‑reported marketing (single‑source, treat as `PROTOTYPE_ASSUMPTION`‑grade): clients saving **~US$600k/yr**; "doubled 2023 expectations." A US "Boston Demo Day" appears once — **unconfirmed**.

### D5.5 ICP & per‑customer read — `INFERRED` from public profiles
- **ICP:** **Santa Fe / Greater Rosario‑anchored SME‑to‑mid discrete manufacturers (~20–300 staff), plastics‑injection‑dominant + metalworking**, buying retrofit live‑OEE / downtime / scrap / traceability on **legacy mixed machinery** — with a marquee enterprise logo (**Molinos Cañuelas**, ~3,000+ staff, ~14 plants, food/milling) for credibility.
- **Module‑fit highlights:** Plasticraft (the one press‑named reference; ISO 9001 injection) & Fundemap (aluminum die‑cast + CNC) are the cleanest OEE/cycle‑time/scrap fits; Fadep/Molinos add food‑grade **traceability**; Molinos is the natural **water/energy** case.
- **Relationship depth remains `UNKNOWN`** for 7 of 8 logos (vendor‑attested "measuring," no case figures). "Plásticos FR" resolves (probably) to *Plásticos FR SA, Rosario* but the generic name keeps it `INFERRED`. **Heineken is NOT a customer.**

### D5.6 Water / ESG — `INFERRED`: a use‑case + demand‑gen wedge, not a separate product
Water/energy ride on the **same** IoT+AI stack; there's no separate water SKU. ESG/water language lives almost entirely in the **CCU/sustainability press**; Efficast's own site and the gov "Next from Argentina" page lead with **OEE/productivity** ("9 of 10 LatAm plants log on paper"), not sustainability. So water is an **opportunistic vertical/award narrative** layered on an OEE product — most material to water‑intensive food/beverage (Molinos, CCU).

### D5.7 Sources (public, 2026‑06‑27)
Official: [efficast.ai](https://efficast.ai/) (team section, Agentes AI, PLC/Modbus, 15 s) · [Cancillería](https://cancilleria.gob.ar/es/nuevas-tecnologias/next-from-argentina/efficast-ia). Primary stack: [Scavuzzo GitHub](https://github.com/Scavuzzo) · advisor [ivanbercovich.com](https://ivanbercovich.com/about/). History: [Infobae — "Un Respiro"](https://www.infobae.com/economia/2020/04/13/la-historia-de-la-pyme-que-junto-a-la-universidad-de-rosario-fabrico-un-respirador-en-15-dias/) · [PuntoBiz (Inventu)](https://puntobiz.com.ar/noticias/val/125477/). CCU/water: [CCU](https://www.ccu.cl/solucion-que-gestiona-y-optimiza-el-consumo-de-agua-industrial-gano-7-edicion-de-innpacta/). Customers: company sites cited in §D4.6 + [Gemplast/La Capital](https://www.lacapital.com.ar/negocios/de-las-cenizas-la-exportacion-la-historia-gemplast-la-fabrica-rosarina-que-resurgio-tres-veces-n10197527.html), [Plasticraft](https://plasticraft.com.ar/), [Molino Cañuelas](https://www.molinocanuelas.com/es). Media: [CNN Salta CEO interview](https://www.youtube.com/watch?v=s-vCbB69VAs). Aggregators (weak corroboration only): ZoomInfo/RocketReach/CB Insights. *Single‑source / self‑reported items flagged inline; the prototype asserts none as fact.*

## E. How alignment is kept honest in the product

- A persistent badge — **"Synthetic manufacturing environment · Independent Efficast-aligned
  prototype"** — is shown in the app shell (not hidden in a footer).
- The adapter boundary (`EfficastPort`) is the *only* contact point a future authorized integration
  would replace; nothing else assumes Efficast internals.
- No screenshot asset, proprietary illustration, or wording is reproduced in the shipped UI; the
  screenshots informed *design language* (color/typography/density), not copied layouts.

# How this fits with Efficast — complementary, and honest about it

This is an **independent, Efficast-aligned** prototype on **synthetic data**. It is *not* affiliated with
Efficast, claims *no* partnership, integration, or API access, and reverse-engineers nothing. This page
states the positioning for a pitch — and is explicit about which claims are verified vs. not, because
"don't assert what you can't verify" is the product's own thesis.

## The wedge (grounded in a fact we can stand behind)
On the public site, Efficast's AI agent **MAIA** doesn't just alert — it **closes work orders** (an
"AI supervisor on WhatsApp" that generates reports, closes work orders, flags bottlenecks, answers
operational questions). The entire thesis of this prototype is:

> **A closed work order is not a recovered line.**

So the fit is not "they alert, we alert better." It is: **MAIA detects → alerts → and can close the work
order; we verify the closure actually held** — cycle-by-cycle, deterministically, and we **auto-reopen on
relapse** (the cycle-17 moment). We are the *verification layer on top of* a detect→alert→close loop, not
a competitor to it.

| Efficast (public capabilities) | Verified Recovery Agent (this prototype) |
|---|---|
| Detect anomalies / predict failure | **Verify** the fix held (deterministic, post-intervention) |
| Alert (incl. MAIA on WhatsApp) | **Orchestrate** the cross-functional evidence + approval gates |
| **Close** the work order | **Prove** it recovered — and **auto-reopen** if the fault recurs |
| Live OEE / dashboards | Recovery Contract + cycle-by-cycle evaluation + tamper-evident audit |
| IoT sensor ingestion (legacy machines) | Same data via the `EfficastPort` seam — verification on top |

The pitch line: **"Efficast can tell you the work order is closed. We tell you the line actually
recovered — and catch it if it didn't."**

## The integration seam (no API access claimed)
The core depends only on the `EfficastPort` interface. `SyntheticEfficastPort` drives the demo;
`EfficastApiPort` ([backend/app/adapters/efficast_api.py](../backend/app/adapters/efficast_api.py)) is a
**documented skeleton** that raises `NotConfigured` until an *authorized* client is injected — it never
calls a live endpoint, and (as everywhere) exposes **no machine-control method**. Its REST/MQTT mappings
(telemetry · OEE · production orders · quality/lots · MAIA alerts · inventory · publish-event) are
labelled *illustrative, to be confirmed against a real authorized API — currently UNKNOWN.*

## Claim confidence — what we assert, and what we don't
| Confidence | Statement |
|---|---|
| **VERIFIED (public site)** | Efficast is a real industrial IoT/OEE/MES product; live OEE; PLC/sensor-sourced data with legacy-machine, fast-install compatibility; an AI agent **MAIA** marketed as a WhatsApp "AI supervisor" that reports, **closes work orders**, flags bottlenecks, answers questions. |
| **OBSERVED (hackathon brief)** | The brief listed customers (e.g. Molino Cañuelas, Plásticos FR, Plasticraft, Textil Calchaquí, Gemplast). |
| **INFERRED (plausible, unconfirmed)** | Consumption/energy & shift-report features; the specific REST/MQTT endpoint shapes in `EfficastApiPort`. Treated as a *design reference*, not a contract. |
| **NOT ASSERTED (unverified — we will not state these as fact)** | Specific funding rounds/amounts/dates; specific awards; named enterprise customers beyond the brief; exact published improvement percentages; internal APIs, data model, cloud/model providers, agent framework, security model. If referenced at all, they are flagged "publicly reported, unverified by us." |

This last row is deliberate. Putting an unverifiable customer name or metric in a pitch and having it be
wrong is exactly the "work completed ≠ verified" failure this product exists to prevent — so we hold the
same standard for our own claims. **That discipline is part of the pitch**, not a limitation of it.

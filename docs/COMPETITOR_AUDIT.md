# Competitor Audit — post-repair verification & return-to-service

*Independent web research (parallel agent sweep). Every row is confidence-tagged. This is an honest
landscape, not a sales sheet — read the "overclaims to avoid" section before writing any marketing copy.*

**The one question:** which products actually (1) **verify** that a completed repair restored production
(post-repair *efficacy*, not anomaly detection), (2) **auto-reopen** on relapse, (3) **link** maintenance
closure to **quality / lot release**?

| Product | Focus | Verifies repair efficacy | Auto-reopen | Links to quality/lot | Confidence |
|---|---|:--:|:--:|:--:|:--:|
| **Augury** (+MaintainX; Bently Nevada OEM) | Vibration/ML machine health | **yes** (single-signal) | partial | no | OBSERVED |
| **Tractian** | Sensors + native CMMS, "closed loop" | partial | unknown | no | OBSERVED |
| **MaintainX** | CMMS + CoPilot + anomaly detection | partial | partial | no | VERIFIED |
| **UpKeep** | CMMS, verification gates before closure | partial | partial | no | OBSERVED |
| **Fiix** (Rockwell) | CMMS, failure codes, WO analytics | no | no | no | OBSERVED |
| **Oxmaint** | CMMS w/ pharma IQ/OQ/PQ RTS gating | partial | no | **yes** (pharma) | OBSERVED |
| **Siemens Senseye** (+Insights Hub) | Failure forecasting, RUL, workflow | unknown | unknown | no | OBSERVED |
| **IBM Maximo** (Manage/Health/Predict) | EAM/CMMS + asset health | no | no | no | INFERRED |
| **PTC ThingWorx** (+Closed-Loop Quality) | IIoT platform + PLM quality feedback | no | no | partial | OBSERVED |
| **Tulip** (+Frontline QMS) | No-code apps; QMS, CAPA, lot disposition | no | no | partial | OBSERVED |
| **GE Vernova Proficy** | MES; quality gates lot release; CIL | no | no | partial | OBSERVED |
| **Microsoft Cloud for Mfg** (agents) | Failure-prediction / ops copilots | no | no | no | VERIFIED |
| **AWS Monitron / Lookout** (Lookout EOL Oct 2026) | Sensor anomaly + technician feedback | no | partial | no | VERIFIED |
| **Google Cloud Mfg** (MDE + Gemini) | Data unification + visual quality AI | no | no | partial | INFERRED |

## The narrowest *defensible* differentiation
The market splits the return-to-service verdict across **two disjoint silos**:
- **Machine-data silo** (Augury, Tractian, AWS, Siemens) — does post-repair efficacy checks **on the
  vibration/health signal only**: confirms the bearing signature normalized, *not* that the line makes good
  parts at rate, and never conditions on comparable load or touches lot disposition. **Augury is the single
  closest** (timestamps the repair, re-reads vibration, marks it Successful/Acceptable) — but single-signal,
  no published auto-reopen-against-contract, no quality/lot bridge.
- **Compliance-workflow silo** (Oxmaint, Tulip QMS, GE Proficy) — gates RTS on qualification status and lot
  release, but driven by **human sign-off / IQ-OQ-PQ checklists**, *not* automated verification that machine
  behavior actually recovered. **Oxmaint is the closest** on RTS gating — but pharma-specific, never checks telemetry.

> **Defensible gap (a SCOPE/FUSION claim, not a "nobody does X" claim):** no single product fuses
> **machine-behavior recovery + condition-comparability + throughput + quality + lot disposition +
> admissible evidence + human authority** into one auditable verdict, with **deterministic auto-reopen on
> verified relapse** and the verdict owned by a non-LLM evaluator. That cross-silo, evaluator-owned
> requalification is what no competitor offers end-to-end today.

## Overclaims to avoid (do NOT say these)
- ❌ "No competitor verifies that a repair restored production." — Augury (and Tractian/Siemens/AWS) run
  post-repair efficacy review. The gap is *single-signal, siloed* verification, not its absence.
- ❌ "We're the only one linking maintenance to quality/lot release." — Oxmaint/GE Proficy/Tulip already tie
  quality/non-conformance to lot disposition. We tie release to **automated machine-behavior recovery**.
- ❌ "We're the only closed loop / the only one that reopens." — "closed-loop" is industry-standard
  marketing; CMMS tools reopen via corrective WOs. Only **deterministic auto-reopen on verified relapse
  against a contract** is undocumented.
- ❌ "Nobody requires comparable operating conditions." — frame as **not surfaced in available sources**,
  never "they cannot."
- ❌ "Our deterministic evaluator is novel technology." — rule/threshold gating exists in CMMS
  (UpKeep gates, Oxmaint qualification locks). The novelty is **scope + fusion + LLM-excluded authority**.
- ❌ Asserting OBSERVED/INFERRED/UNKNOWN competitor capabilities as confirmed fact — much is marketing copy.

## How to read confidence (verified vs inference vs unknown)
- **VERIFIED** — stated in the vendor's own product documentation / a primary source.
- **OBSERVED** — stated in vendor marketing, blogs, or third-party write-ups (not primary product docs).
- **INFERRED** — reasoned from adjacent evidence, not directly stated.
- **UNKNOWN** — not found in available public sources (a gap in *our* research, **not** a claim the vendor
  lacks the capability).
- **PROTOTYPE_ASSUMPTION** — applies only to *our* own configurable figures (thresholds, costs, SPRT), not
  to anything in this competitor table. See `EFFICAST_EVIDENCE_LEDGER.md`.

Capability cells are a point-in-time read of public sources (mid-2026) and may be stale; treat OBSERVED/
INFERRED/UNKNOWN as provisional, not as findings about what a vendor can or cannot do.

## Sources (one primary URL per product)
- Augury — https://www.augury.com/blog/customers-partners/from-alert-to-action-5-things-to-know-about-the-augury-maintainx-integration/
- Tractian — https://tractian.com/en/blog/predictive-maintenance-analytics
- MaintainX — https://help.getmaintainx.com/about-work-orders
- UpKeep — https://upkeep.com/blog/corrective-action-request/
- Fiix — https://fiixsoftware.com/cmms/work-orders/
- Oxmaint — https://oxmaint.com/article/pharmaceutical-manufacturing-maintenance-gmp-equipment-qualification
- Siemens Senseye — https://www.siemens.com/global/en/products/services/digital-enterprise-services/analytics-artificial-intelligence-services/senseye-predictive-maintenance/maintenance-workflow-management.html
- IBM Maximo — https://www.ibm.com/new/announcements/expanding-the-journey-to-reliability-with-maximo-application-suite-8-11
- PTC ThingWorx — https://www.ptc.com/en/resources/iiot-on-demand/thingworx-at-vestas
- Tulip — https://support.tulip.co/docs/frontline-qms-1
- GE Vernova Proficy — https://etechgroup.com/blog/manufacturing/a-look-at-ge-proficy-plant-applications/
- Microsoft Cloud for Manufacturing — https://adoption.microsoft.com/en-us/scenario-library/manufacturing/maintenance-prediction-agent/
- AWS Monitron — https://aws.amazon.com/monitron/faqs/
- Google Cloud Manufacturing — https://cloud.google.com/solutions/manufacturing

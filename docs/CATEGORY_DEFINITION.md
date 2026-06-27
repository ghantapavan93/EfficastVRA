# Category Definition — Post-Intervention Production Requalification (PIPR)

*Synthesized from parallel research into return-to-service standards across aviation, pharma-GMP, nuclear,
and ISO quality management. The headline finding: **this workflow is not invented — it is a faithful
generalization of established, standards-backed practice** from high-consequence regulated domains, applied
to general discrete manufacturing where the pieces exist but are rarely bound into one loop.*

## The category
**Post-Intervention Production Requalification (PIPR):** the deterministic, advisory-gated verification —
performed *after* a maintenance/corrective intervention closes — that a production line has actually
returned to service, by **jointly** requiring machine-behavior recovery to pre-fault baseline, verified
under **comparable operating conditions**, restored throughput, in-spec quality, and cleared lot
disposition, held over a monitoring window against an admissible-evidence standard with explicit human
authority, and **automatically reopened on relapse**.

## Primary positioning
> A closed work order is not a recovered line. The Verified Recovery Agent requalifies a production line
> *after* an intervention via a deterministic **Recovery Contract** — verifying behavior recovery under
> comparable operating conditions, restored throughput, in-spec quality, and cleared lot disposition over a
> monitoring window — with the closure verdict owned by a deterministic evaluator (never an LLM, never
> machine control) and **auto-reopen on relapse**.

## Our coined terms ↔ established standards (say both)
| Our term | Established equivalent | Domain |
|---|---|---|
| Recovery Contract | Acceptance criteria / qualification protocol (OQ/PQ, PMT, CAPA success criteria) | pharma / nuclear / ISO |
| Comparable-Conditions Gate | "Test under actual production conditions" (PQ); integrated-vs-segmented test (NRC) | pharma / nuclear |
| Verification window | Continued Process Verification (FDA Stage 3); CAPA effectiveness window (30–90d); burn-in / infant-mortality monitoring | pharma / ISO / reliability |
| Reopen on relapse | Repeat-fault / callback (low first-time-fix rate); CPV out-of-trend; CAPA recurrence | field service / pharma |
| Recovery Debt / Conditional | **Concession / deviation permit / "use-as-is"** release (ISO 9000) | quality engineering |
| Qualification Record / Certificate | Return-to-Service (FAA 43.5/43.7) / Certificate of Release to Service (EASA 145.A.50); qualification dossier | aviation / pharma |
| Quality release + lot disposition | MRB quarantine / nonconforming-product disposition; PSSR/ORR startup gating | quality / process safety |

## Standards that validate the workflow (confidence-tagged)
- **Aviation — Return to Service / CRS** (FAA AC 43-9C; EASA Part-145 145.A.50): certification is
  **deliberately task-scoped** — signing off a tire change certifies only the tire change, *not* whole
  airworthiness. This is exactly our thesis that a closure event is narrow and needs independent verification. *(VERIFIED)*
- **Pharma-GMP — IQ/OQ/PQ + Requalification + Continued Process Verification (CPV, FDA Stage 3):** PQ tests
  under **actual production conditions**; CPV is **lifecycle** statistical monitoring, "not a periodic
  checkbox." Direct precedent for the comparability gate + verification window + reopen-on-out-of-trend. *(VERIFIED)*
- **Nuclear/power — Post-Maintenance Testing (PMT)** (NRC IP 71111.19; DOE-STD-1065): confirms (a) the
  deficiency is corrected, (b) no new deficiency introduced, (c) ready for service. The NRC's documented
  **"segmented tests must reflect overall system performance"** lesson is a real-plant warning that a narrow
  post-fix check can pass while integrated function is still impaired — our line-vs-component framing. *(VERIFIED)*
- **ISO quality — CAPA effectiveness check** (ISO 9001 8.5.2/10.2; 21 CFR 820.100): time-bound (30–90d)
  proof the action eliminated the root cause **and the issue did not recur** under real conditions. The
  closest cross-industry precedent for verify-then-reopen. *(VERIFIED)*
- **Reliability — bathtub curve / burn-in:** after a major repair the asset re-enters **infant mortality**
  and is temporarily *more* likely to fail — the physical justification for a verification window. *(VERIFIED)*

## Honest gaps (where we import rigor rather than reflect universal practice)
- The integrated verify-then-reopen loop is fully codified only in **regulated** domains. In ordinary
  discrete/CMMS manufacturing the pieces exist (first-time-fix rate, MRB, shift handover) but are rarely
  bound into one loop — so PIPR is a **value-add import**, framed as such, not "universal existing practice."
- Real comparability specs define **how** comparability is established (load/throughput/material tolerances).
  Our gate is an MVP (categorical match + numeric tolerance); the research recommends upgrading to
  **standardized-mean-difference + baseline prediction band + CUSUM change-point** (see RESEARCH_GAPS).
- Verification-window length is **risk/physics-based** in practice (CAPA 30–90d, burn-in ~48h), not a single
  global default — ours is a PROTOTYPE_ASSUMPTION and should eventually scale with failure mode / criticality.
- **Independence of the verdict authority** (certifier ≠ executor) is a recognized regulated safeguard; our
  deterministic-evaluator-owns-closure design aligns, but the data feeding it must stay independent of the actor.

## Sources (standards & primary references — all VERIFIED from primary/official sources)
- FAA Return to Service (14 CFR 43.5/43.7) — https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_43-9C_CHG_2.pdf
- EASA Certificate of Release to Service (Part-145 145.A.50) — https://skybrary.aero/articles/certificate-release-service-crs
- IQ/OQ/PQ (pharma-GMP) — https://www.pharmagmp.in/understanding-the-role-of-installation-operational-and-performance-qualification-iq-oq-pq-in-gmp/
- Requalification (periodic/change-driven) — https://zamann-pharma.com/2024/04/22/iq-oq-pq-essential-steps-for-equipment-qualification/
- Continued Process Verification (FDA Stage 3) — https://ispe.org/pharmaceutical-engineering/july-august-2020/continued-process-verification-stages-1-3
- Post-Maintenance Testing (NRC IP 71111.19) — https://www.nrc.gov/docs/ML1808/ML18089A591.pdf
- Guide to Good Practices for PMT (DOE-STD-1065) — https://www.standards.doe.gov/standards-documents/1000/1065-astd-1994
- Pre-Startup Safety Review / Operational Readiness Review — https://www.aiche.org/resources/publications/cep/2025/june/process-safety-beacon-operational-readiness-reviews
- CAPA effectiveness check (ISO 9001 / 21 CFR 820.100) — https://sgsystemsglobal.com/glossary/capa-effectiveness-check/
- First-Time-Fix rate / repeat-fault KPI — https://www.ptc.com/en/blogs/service/what-are-most-important-kpis-field-service-management
- Material Review Board / lot disposition — https://tulip.co/blog/material-review-board/
- Concession / deviation permit (ISO 9000) — https://connect981.com/glossary/concession
- Shift handover (HSE HSG48) — https://www.hse.gov.uk/humanfactors/topics/shift-handover.htm
- Bathtub curve / burn-in — https://tractian.com/en/glossary/bathtub-curve

*Confidence: the standards above are **VERIFIED** from primary/official sources. The mapping of our coined
terms to them is **INFERRED** (our interpretation). Our own thresholds/windows remain **PROTOTYPE_ASSUMPTION**.*

# Novelty Claims — what we may say, and what we must not

*Adversarially reviewed against the competitor audit + standards research. This is the product's integrity
thesis applied to itself: claim only what is defensible, and write down the overclaims so they don't creep
back into a deck.*

## ✅ Defensible (you may state these, with the framing given)
1. **Cross-silo fusion verdict.** No single product fuses *machine-behavior recovery + condition-comparability
   + throughput + quality + lot disposition + admissible evidence + human authority* into one auditable
   return-to-service verdict that auto-reopens on relapse.
   *Why defensible:* the market splits this across the machine-data silo (verifies only the health signal,
   never lot disposition) and the compliance silo (gates lot release on human sign-off, never checks
   telemetry). It is a **scope** claim, not a "nobody does X" claim.
2. **Comparability-conditioned verdict.** Conditioning the recovery verdict on *comparable operating
   conditions* (same speed/load/state/product/lot — so a quiet idle machine cannot "pass") is **not surfaced
   in any competitor's published return-to-service verdict.**
   *Why defensible:* comparability-under-load is central in pharma PQ, burn-in, and nuclear integrated
   testing, and is the documented NRC failure mode — but is not documented in any competitor verdict. State
   as *"not surfaced in available sources,"* never *"they cannot."*
3. **Deterministic auto-reopen + LLM-excluded authority.** Deterministic auto-reopen on *verified relapse
   against a pre-defined contract*, with the verdict owned by a deterministic evaluator the LLM cannot override.
   *Why defensible:* "closed-loop" is widely marketed and CMMS tools reopen via corrective WOs, but a
   deterministic reopen tied to a relapse-against-contract test **plus explicit LLM exclusion** is not
   documented as a product feature. Defensible **only if stated this precisely.**

## ❌ Overclaims — do NOT say (and the honest replacement)
1. "We're the only one that verifies a repair restored production." → Augury/Tractian/Siemens/AWS run
   post-repair efficacy review. Say: **"verification today is single-signal and siloed."**
2. "We're the only one linking maintenance to quality/lot release." → Oxmaint/GE Proficy/Tulip do. Say:
   **"we tie lot release to *automated machine-behavior recovery*."**
3. "We're the only closed loop / the only one that reopens." → heavily marketed; CMMS reopen via WOs. Say:
   **"deterministic auto-reopen on verified relapse against a contract is undocumented."**
4. "Nobody requires comparable operating conditions." → reframe as **"not part of any published verdict,"**
   never "they cannot."
5. "Our deterministic rules/threshold evaluator is novel technology." → rule gating exists in CMMS. Keep
   only the **scope + fusion + LLM-excluded-authority** framing.
6. "An entirely new workflow nobody does." → the verify-then-reopen loop is codified in nuclear PMT, pharma
   CPV/requalification, aviation RTS/CRS, ISO CAPA. Say: **"importing regulated rigor into general
   discrete/CMMS manufacturing."**
7. Conflating predictive failure/anomaly detection (Monitron, Lookout [EOL Oct 2026], Senseye, MS/Google
   agents) with post-repair efficacy verification — several stop at predicting failure + notifying planners.
8. Asserting OBSERVED/INFERRED/UNKNOWN competitor capabilities as confirmed fact — much is marketing copy.
9. Any claim that the prototype's SPRT/confidence numbers reflect real-plant statistical validity — they are
   **illustrative on synthetic data**; keep the PROTOTYPE_ASSUMPTION disclosure.

*See [COMPETITOR_AUDIT.md](COMPETITOR_AUDIT.md) for the evidence and [CATEGORY_DEFINITION.md](CATEGORY_DEFINITION.md)
for the standards mapping. This file supersedes any louder claim made earlier in the project.*

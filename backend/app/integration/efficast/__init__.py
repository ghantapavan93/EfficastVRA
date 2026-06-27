"""Efficast Recovery integration-readiness layer (contract v0.1).

A narrow, versioned, testable seam for integrating Verified Recovery with a host MES (Efficast) WITHOUT
assuming any private API, database, cloud, or customer data. Additive — it sits beside the existing
hexagonal ``EfficastPort`` and never claims a live connection. The Sandbox adapter is an interface + config
boundary only; it invents no endpoints. Real data arrives as *sanitised, enveloped* event bundles replayed
through the same deterministic evaluator the synthetic demo uses.
"""

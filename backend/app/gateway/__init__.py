"""The Agent Action Gateway — the single choke point for every operational side effect.

No model-generated action reaches a tool except through :func:`execute`, which runs the full
pipeline: schema → identity → plant scope → role → risk class → policy → human-approval →
idempotency → circuit-breaker → audit → execute → result validation → state transition.
"""

from app.gateway.gateway import GatewayError, execute

__all__ = ["execute", "GatewayError"]

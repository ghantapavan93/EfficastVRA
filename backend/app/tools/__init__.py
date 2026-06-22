"""Real backend tools. Every tool has Pydantic IO, an authorization policy, an action class,
explicit errors, provenance (source/timestamp/freshness), an audit event, and (for writes) an
idempotency key. Tools are only ever invoked through the Agent Action Gateway.
"""

from app.tools.registry import REGISTRY, get_tool

__all__ = ["REGISTRY", "get_tool"]

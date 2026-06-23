"""Ports — the hexagonal boundaries of the application core.

Everything the core needs from the outside world crosses one of these interfaces. Adapters (synthetic
today, real tomorrow) implement them; the **composition root** (`app/composition.py`) decides which
adapter is wired in. This is the single seam that lets the prototype run on deterministic synthetic
data while a real deployment swaps in Efficast / OPC-UA / a Unified Namespace / a hosted model —
without touching the domain, evaluator, gateway, workflow, or UI.

  • EfficastPort     — read evidence from / publish events to the host MES (no machine control)
  • ReasoningProvider — bounded LLM/deterministic reasoning (proposes; never decides or actuates)
  • TelemetrySource   — per-cycle readings for the verification window (synthetic or ingested real data)

The notification sink (`app/services/notifications.py:dispatch`) and the publish sink
(`app/main.py:_publish_sink`) are the other two swap points (WhatsApp/email; Kafka/MQTT broker).
"""

from app.adapters.efficast_port import EfficastPort
from app.reasoning.base import ReasoningProvider
from app.services.telemetry import TelemetrySource

__all__ = ["EfficastPort", "ReasoningProvider", "TelemetrySource"]

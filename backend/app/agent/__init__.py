"""The bounded Recovery Agent: a neuro-symbolic, Reflexion-shaped Plan-Executor.

See docs/AGENT_RESEARCH.md for the research basis and docs/AGENT_GRAPH.md for the graph. The agent
*proposes* (perceive→retrieve→hypothesize→draft→self_critique→decide; observe/reflect while
monitoring); the deterministic evaluator and the policy gateway *decide and act*.
"""

from app.agent.confidence import confidence_label, recovery_confidence
from app.agent.graph import DraftResult, RecoveryAgentGraph
from app.agent.trace import latest_confidence, list_traces, record_trace

__all__ = [
    "RecoveryAgentGraph",
    "DraftResult",
    "record_trace",
    "list_traces",
    "latest_confidence",
    "recovery_confidence",
    "confidence_label",
]

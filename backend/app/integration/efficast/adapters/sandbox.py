"""SandboxEfficastAdapter — the interface + configuration boundary for a FUTURE Efficast integration.

This adapter intentionally does NOTHING. It exists to define where a real REST / webhook / event-stream
integration would plug in, and to hold its configuration — but it invents no Efficast endpoints and makes no
network calls. Every method raises ``NotImplementedError`` pointing at the open questions. Do not claim the
system is connected to Efficast until a real endpoint (or a sanitised dataset via ReplayEfficastAdapter) is
provided and tested. See docs/EFFICAST_OPEN_QUESTIONS.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SandboxConfig:
    base_url: str = ""            # set when Efficast provides an endpoint
    auth_mode: str = "unset"      # e.g. oauth2 | api_key | mtls — to be confirmed with Efficast
    tenant_id: str = ""
    plant_id: str = ""
    verify_tls: bool = True
    timeout_s: float = 10.0


_MSG = ("SandboxEfficastAdapter is an interface/config boundary only — no Efficast endpoint is wired and "
        "none is assumed. Provide a sanitised dataset (ReplayEfficastAdapter) or a real, agreed endpoint "
        "with tests before use. See docs/EFFICAST_OPEN_QUESTIONS.md.")


class SandboxEfficastAdapter:
    """Stub implementation of EfficastRecoveryPort. All methods raise until a real integration is agreed."""

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()

    def __getattr__(self, name: str):
        # any port method (read or proposal) resolves to an honest "not wired" error
        if name.startswith(("get_", "request_", "propose_", "publish_", "attach_", "create_")):
            def _unwired(*_a, **_k):
                raise NotImplementedError(f"{name}: {_MSG}")
            return _unwired
        raise AttributeError(name)

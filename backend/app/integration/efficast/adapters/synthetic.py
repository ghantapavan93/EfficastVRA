"""SyntheticEfficastAdapter — the deterministic demo served as contract-v0.1 events.

It is the canned F27 scenario expressed through the same envelope a real MES would use, so the integration
path (reconcile → replay → shadow) can be exercised end-to-end with zero external dependencies. Implemented
as a ReplayEfficastAdapter over the synthetic bundle.
"""

from __future__ import annotations

from app.integration.efficast.adapters.replay import ReplayEfficastAdapter
from app.integration.efficast.fixtures import make_f27_bundle


class SyntheticEfficastAdapter(ReplayEfficastAdapter):
    def __init__(self, *, cycles: int = 30, relapse_at: int | None = None):
        super().__init__(make_f27_bundle(cycles=cycles, relapse_at=relapse_at))

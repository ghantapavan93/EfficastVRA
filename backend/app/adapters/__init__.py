"""Efficast adapter boundary.

``EfficastPort`` is the *only* contact point a future authorized Efficast integration would replace.
Everything else in the app depends on this interface, never on host-MES internals.
"""

from app.adapters.efficast_port import EfficastPort
from app.adapters.synthetic import ScenarioPhysics, SyntheticEfficastPort

__all__ = ["EfficastPort", "SyntheticEfficastPort", "ScenarioPhysics"]

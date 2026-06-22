"""ISA-95 asset hierarchy + Unified Namespace (UNS) topic mapping.

The industrial-AI field standardises on an ISA-95 hierarchy (Enterprise → Site → Area → Line → Cell)
published over a Unified Namespace on MQTT (see docs/INDUSTRY_LANDSCAPE.md). This module derives that
hierarchy from our existing entities and renders the UNS / MQTT Sparkplug-B topics a real broker would
carry — so the prototype speaks the same addressing scheme a host platform like Efficast (or a UNS in
front of it) would expose. Nothing here connects to a broker; it is the contextualisation layer the
agent reasons over.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session

from app.domain.models import Machine, Plant, ProductionLine

ISA95_LEVELS = ["enterprise", "site", "area", "line", "cell", "component"]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-") or "x"


@dataclass
class AssetPath:
    enterprise: str
    site: str
    area: str
    line: str
    cell: str                      # the machine itself
    component: Optional[str] = None

    def segments(self) -> list[str]:
        segs = [self.enterprise, self.site, self.area, self.line, self.cell]
        if self.component:
            segs.append(self.component)
        return segs


def asset_path(session: Session, machine: Machine) -> AssetPath:
    plant = session.get(Plant, machine.plant_id) if machine.plant_id else None
    line = session.get(ProductionLine, machine.line_id) if machine.line_id else None
    return AssetPath(
        enterprise=_slug(machine.tenant_id),
        site=_slug(getattr(plant, "code", None) or machine.plant_id),
        area=_slug(getattr(line, "name", "") or "production"),   # ISA-95 'area' (no dedicated entity)
        line=_slug(getattr(line, "code", None) or machine.line_id or "line"),
        cell=_slug(machine.code),
    )


def uns_topic(session: Session, machine: Machine, signal: str) -> str:
    """ISA-95 Unified-Namespace topic, e.g. northstar/plant-ns/packaging-line-4/l4/l4-conv/metrics/vibration."""
    return "/".join(asset_path(session, machine).segments()) + f"/metrics/{_slug(signal)}"


def sparkplug_topic(session: Session, machine: Machine) -> str:
    """MQTT Sparkplug-B topic using the Parris method (ISA-95 path folded into the Group_ID)."""
    p = asset_path(session, machine)
    group = ":".join([p.enterprise, p.site, p.area, p.line])
    return f"spBv1.0/{group}/NDATA/{p.cell}"

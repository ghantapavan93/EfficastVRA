"""Integration-layer tests (Phase 11): ISA-95 hierarchy, UNS topics, connector catalog.

Grounded in how real industrial-AI platforms address machinery (docs/INDUSTRY_LANDSCAPE.md): an ISA-95
asset path published over a Unified Namespace, with a connector ecosystem feeding the application seams.
"""

from __future__ import annotations

from app.domain.models import Machine
from app.integration import (
    CONNECTORS,
    asset_path,
    connectors_by_seam,
    sparkplug_topic,
    uns_topic,
)
from app.seed.northstar import IDS


def test_isa95_asset_path_has_five_levels(session):
    machine = session.get(Machine, IDS["machine"])
    path = asset_path(session, machine)
    segs = path.segments()
    assert len(segs) == 5  # enterprise / site / area / line / cell
    assert path.cell == "l4-conv"          # slug of the machine code
    assert path.enterprise == "northstar"  # the tenant


def test_uns_topic_is_isa95_addressable(session):
    machine = session.get(Machine, IDS["machine"])
    topic = uns_topic(session, machine, "vibration")
    assert topic.endswith("/metrics/vibration")
    assert topic.startswith("northstar/")
    assert "l4-conv" in topic


def test_sparkplug_topic_uses_parris_method(session):
    machine = session.get(Machine, IDS["machine"])
    topic = sparkplug_topic(session, machine)
    assert topic.startswith("spBv1.0/")
    assert "/NDATA/" in topic
    assert ":" in topic  # ISA-95 path folded into the Group_ID with the Parris delimiter


def test_connector_catalog_covers_the_seams():
    keys = {c.key for c in CONNECTORS}
    assert {"opc_ua", "mqtt_uns", "mes_rest", "pi_historian", "cmms_erp"} <= keys
    by_key = {c.key: c for c in CONNECTORS}
    assert by_key["mqtt_uns"].direction == "bidirectional"
    assert by_key["opc_ua"].direction == "inbound"
    # No connector may claim a machine-control capability — the system has no such seam.
    for c in CONNECTORS:
        assert "control" not in c.feeds.lower()
    # Connectors map onto real application seams.
    seams = " ".join(connectors_by_seam().keys())
    assert "TelemetrySource" in seams and "EfficastPort" in seams

"""Test 1: the synthetic factory graph is internally consistent."""

from __future__ import annotations

from sqlmodel import Session, select

from app.domain.enums import InterventionStatus, OutcomeType
from app.domain.models import (
    Component,
    Incident,
    Intervention,
    InventoryPart,
    Machine,
    ProductionOrder,
    Sensor,
)
from app.seed.northstar import IDS


def test_factory_graph_consistent(session: Session):
    machine = session.get(Machine, IDS["machine"])
    assert machine is not None and machine.baseline["vibration_mm_s"] == 3.1
    assert machine.machine_model == "CDX-220"

    order = session.get(ProductionOrder, IDS["order"])
    assert order.qty_remaining == 8420  # matches the brief exactly
    assert order.machine_id == machine.id

    sensors = session.exec(select(Sensor).where(Sensor.machine_id == machine.id)).all()
    assert {s.tag for s in sensors} >= {"VIB-L4-01", "TMP-L4-01", "CYC-L4-01"}

    comps = session.exec(select(Component).where(Component.machine_id == machine.id)).all()
    assert any(c.part_number == "BR-6205" for c in comps)

    inc = session.get(Incident, IDS["incident"])
    assert inc.machine_id == machine.id and inc.order_id == order.id and inc.fault_code == "F27"

    itv = session.get(Intervention, IDS["intervention_1"])
    assert itv.status == InterventionStatus.COMPLETED and itv.sequence == 1

    hist = session.get(Incident, IDS["hist_incident"])
    assert hist.historical and hist.outcome_type == OutcomeType.VERIFIED

    part = session.exec(select(InventoryPart).where(InventoryPart.part_number == "BR-6205")).first()
    assert part is not None and part.on_hand >= 1

"""The Northstar Packaging Plant scenario — deterministic, fixed IDs.

Seeds the manufacturing substrate up to the moment the agent takes over: an incident on Packaging
Line 4's conveyor-drive assembly (fault F27), production order PO-2841 with 8,420 units remaining,
and a **completed** first intervention (coupling-alignment correction). The contract, monitoring,
relapse, contingency and verification are all driven afterwards by the workflow + demo controller —
they are NOT pre-baked here.

Document corpus (RAG) is seeded separately in :mod:`app.rag.corpus`.
"""

from __future__ import annotations

from datetime import timedelta

from sqlmodel import Session, select

from app.config import get_settings
from app.domain.base import utcnow
from app.domain.enums import (
    InterventionStatus,
    LotDisposition,
    MachineState,
    OutcomeType,
    Role,
    Severity,
    WorkflowState,
)
from app.domain.models import (
    Component,
    DowntimeEvent,
    Incident,
    Intervention,
    InventoryPart,
    Machine,
    MaiaAlert,
    MaterialLot,
    Operator,
    Plant,
    ProductionLine,
    ProductionOrder,
    QualityCheck,
    ScrapEvent,
    Sensor,
    Shift,
    Technician,
    User,
    WorkOrder,
)

_settings = get_settings()

# Stable IDs referenced by tests, demo controller, and the frontend.
IDS = {
    "tenant": _settings.tenant_id,
    "plant": "PLANT-NS",
    "line": "LINE-4",
    "machine": "MCH-L4-CONV",
    "motor": "CMP-MOTOR",
    "coupling": "CMP-COUPLING",
    "bearing": "CMP-BEARING",
    "sensor_vib": "VIB-L4-01",
    "sensor_temp": "TMP-L4-01",
    "sensor_cyc": "CYC-L4-01",
    "order": "PO-2841",
    "incident": "INC-2841",
    "intervention_1": "ITV-ALIGN-1",
    "wo_motor": "WO-8701",
    "wo_align": "WO-8744",
    "bearing_part": "BR-6205",
    "hist_incident": "INC-1990",
    "alert": "ALERT-7731",
    "contract_no": "RC-1042",
    "tech_lang": "TECH-LANG",
    "tech_ortiz": "TECH-ORTIZ",
}

BASELINE = {"vibration_mm_s": 3.1, "temp_c": 63.0, "cycle_time_s": 12.2, "scrap_pct": 1.6}
DEGRADED = {"vibration": 7.4, "temperature": 84.0, "cycle_time": 14.8, "scrap_pct": 4.8, "fault_code": "F27"}


def is_seeded(session: Session) -> bool:
    return session.get(Plant, IDS["plant"]) is not None


def seed_all(session: Session) -> dict:
    """Idempotent: if the plant already exists, do nothing. Use CLI ``reset`` for a clean rebuild."""
    if is_seeded(session):
        return {"seeded": False, "reason": "already-seeded", "ids": IDS}

    now = utcnow()
    tenant = IDS["tenant"]
    plant_id = IDS["plant"]

    # ── Plant / line ──────────────────────────────────────────────────────────
    session.add(Plant(id=plant_id, tenant_id=tenant, code="NS", name="Northstar Packaging Plant",
                       timezone="America/New_York"))
    session.add(ProductionLine(id=IDS["line"], tenant_id=tenant, plant_id=plant_id, code="L4",
                               name="Packaging Line 4"))
    session.flush()  # tier: plant/line exist before children (FK ordering w/o ORM relationships)

    # ── Machine + components + sensors ────────────────────────────────────────
    session.add(Machine(
        id=IDS["machine"], tenant_id=tenant, plant_id=plant_id, line_id=IDS["line"],
        code="L4-CONV", name="Line 4 Conveyor-Drive Assembly",
        machine_model="CDX-220", manufacturer="Conveytec", state=MachineState.ALERT,
        baseline=BASELINE,
        live={**DEGRADED, "at": now.isoformat(), "freshness_s": 4},
    ))
    session.flush()  # tier: machine
    session.add(Component(id=IDS["motor"], tenant_id=tenant, plant_id=plant_id, machine_id=IDS["machine"],
                          name="Drive Motor", kind="motor", part_number="MTR-CDX-7",
                          installed_at=now - timedelta(days=9),
                          health_note="Replaced 9 days ago under WO-8701."))
    session.add(Component(id=IDS["coupling"], tenant_id=tenant, plant_id=plant_id, machine_id=IDS["machine"],
                          name="Motor-Drive Coupling", kind="coupling", part_number="CPL-22",
                          health_note="Suspected misalignment after motor replacement."))
    session.add(Component(id=IDS["bearing"], tenant_id=tenant, plant_id=plant_id, machine_id=IDS["machine"],
                          name="Drive-End Bearing", kind="bearing", part_number=IDS["bearing_part"],
                          health_note="Original bearing; degradation suspected as contingency cause."))
    session.flush()  # tier: components (sensors reference component_id)
    session.add(Sensor(id=IDS["sensor_vib"], tenant_id=tenant, plant_id=plant_id, machine_id=IDS["machine"],
                       component_id=IDS["bearing"], tag="VIB-L4-01", kind="vibration", unit="mm/s"))
    session.add(Sensor(id=IDS["sensor_temp"], tenant_id=tenant, plant_id=plant_id, machine_id=IDS["machine"],
                       component_id=IDS["motor"], tag="TMP-L4-01", kind="temperature", unit="°C"))
    session.add(Sensor(id=IDS["sensor_cyc"], tenant_id=tenant, plant_id=plant_id, machine_id=IDS["machine"],
                       tag="CYC-L4-01", kind="cycle_time", unit="s"))
    session.flush()  # tier: sensors

    # ── Production order ──────────────────────────────────────────────────────
    session.add(ProductionOrder(
        id=IDS["order"], tenant_id=tenant, plant_id=plant_id, line_id=IDS["line"], machine_id=IDS["machine"],
        product="Industrial Cap 20L (TI-20L)", qty_total=20_000, qty_done=11_580, unit="units",
        status="in_progress", due_at=now + timedelta(hours=46),
    ))
    session.flush()  # tier: production order

    # ── People ────────────────────────────────────────────────────────────────
    session.add(Operator(id="OPR-1", tenant_id=tenant, plant_id=plant_id, name="J. Okafor", shift_code="B"))
    session.add(Shift(id="SHF-B", tenant_id=tenant, plant_id=plant_id, code="B", name="Shift B (14:00–22:00)",
                      start_hour=14, end_hour=22))
    session.add(Technician(id=IDS["tech_lang"], tenant_id=tenant, plant_id=plant_id, name="A. Lang",
                           skills=["alignment", "vibration", "mechanical"]))
    session.add(Technician(id=IDS["tech_ortiz"], tenant_id=tenant, plant_id=plant_id, name="M. Ortiz",
                           skills=["bearings", "drivetrain", "mechanical"]))

    # Local identity principals (one per role) — the auth layer maps tokens → these users.
    session.add(User(id="USR-SUP", tenant_id=tenant, plant_id=plant_id, username="s.vega",
                     display_name="S. Vega", role=Role.SUPERVISOR))
    session.add(User(id="USR-TECH", tenant_id=tenant, plant_id=plant_id, username="a.lang",
                     display_name="A. Lang", role=Role.TECHNICIAN))
    session.add(User(id="USR-QUAL", tenant_id=tenant, plant_id=plant_id, username="q.idris",
                     display_name="Q. Idris", role=Role.QUALITY_ENGINEER))
    session.add(User(id="USR-ADMIN", tenant_id=tenant, plant_id=plant_id, username="p.okoro",
                     display_name="P. Okoro", role=Role.PLANT_ADMIN))

    # ── Inventory ─────────────────────────────────────────────────────────────
    session.add(InventoryPart(id="INV-BR6205", tenant_id=tenant, plant_id=plant_id,
                              part_number=IDS["bearing_part"], name="Drive-End Bearing BR-6205",
                              on_hand=4, reserved=0, location="MRO-A12"))
    session.add(InventoryPart(id="INV-CPL22", tenant_id=tenant, plant_id=plant_id,
                              part_number="CPL-22-SHIM", name="Coupling Alignment Shim Kit",
                              on_hand=12, reserved=0, location="MRO-A05"))
    session.flush()  # tier: people / technicians / inventory (work orders + lots reference them)

    # ── Material lots produced during the degraded window (on HOLD) ────────────
    session.add(MaterialLot(id="LOT-2841-07", tenant_id=tenant, plant_id=plant_id, order_id=IDS["order"],
                            machine_id=IDS["machine"], product="Industrial Cap 20L (TI-20L)", qty=420,
                            disposition=LotDisposition.HOLD,
                            produced_from=now - timedelta(hours=5), produced_to=now - timedelta(hours=3)))
    session.add(MaterialLot(id="LOT-2841-08", tenant_id=tenant, plant_id=plant_id, order_id=IDS["order"],
                            machine_id=IDS["machine"], product="Industrial Cap 20L (TI-20L)", qty=260,
                            disposition=LotDisposition.HOLD,
                            produced_from=now - timedelta(hours=3), produced_to=now - timedelta(hours=1)))

    # ── Recent fault / scrap evidence (F27 short stops, rising scrap) ──────────
    for k, mins in enumerate([240, 180, 96, 41, 12]):
        session.add(DowntimeEvent(
            id=f"DT-F27-{k}", tenant_id=tenant, plant_id=plant_id, machine_id=IDS["machine"],
            order_id=IDS["order"], started_at=now - timedelta(minutes=mins),
            ended_at=now - timedelta(minutes=mins - 2), duration_s=120,
            reason="Conveyor drive fault — short stop", fault_code="F27",
        ))
    for k, (mins, qty, reason) in enumerate([(210, 6, "Dimension out of tolerance"),
                                             (120, 9, "Seal defect"),
                                             (35, 11, "Contamination")]):
        session.add(ScrapEvent(id=f"SCR-{k}", tenant_id=tenant, plant_id=plant_id, machine_id=IDS["machine"],
                               order_id=IDS["order"], qty=qty, reason=reason, at=now - timedelta(minutes=mins)))

    # ── Pending first-piece quality check (blocks quality release) ─────────────
    session.add(QualityCheck(id="QC-FP-2841", tenant_id=tenant, plant_id=plant_id, machine_id=IDS["machine"],
                             order_id=IDS["order"], kind="first_piece", result="pending",
                             spec_ref="QS-TI20L-r3 §4.2"))

    # ── Prior work orders ─────────────────────────────────────────────────────
    session.add(WorkOrder(id=IDS["wo_motor"], tenant_id=tenant, plant_id=plant_id, machine_id=IDS["machine"],
                          kind="corrective", title="Replace drive motor", status="completed",
                          technician_id=IDS["tech_ortiz"], opened_at=now - timedelta(days=9, hours=2),
                          completed_at=now - timedelta(days=9)))
    session.add(WorkOrder(id=IDS["wo_align"], tenant_id=tenant, plant_id=plant_id, machine_id=IDS["machine"],
                          kind="corrective", title="Coupling-alignment correction", status="completed",
                          technician_id=IDS["tech_lang"], opened_at=now - timedelta(minutes=70),
                          completed_at=now - timedelta(minutes=10)))

    # ── Historical incident (powers compare_historical_interventions) ─────────
    session.add(Incident(
        id=IDS["hist_incident"], tenant_id=tenant, plant_id=plant_id, machine_id=IDS["machine"],
        correlation_id="hist-1990", dedupe_key="hist-INC-1990", title="Line 2 conveyor F27 recurrence (2025)",
        severity=Severity.S2, state=WorkflowState.VERIFIED_RECOVERY, fault_code="F27",
        opened_at=now - timedelta(days=420), closed_at=now - timedelta(days=419),
        historical=True, outcome_type=OutcomeType.VERIFIED,
        outcome_summary=("Sibling CDX-220 drive: alignment correction did NOT hold — F27 recurred within "
                         "~20 cycles; root cause was drive-end bearing degradation. Bearing replacement "
                         "(BR-6205) verified over 30 stable cycles."),
    ))

    # ── The ACTIVE incident + completed first intervention (agent starts here) ─
    session.add(Incident(
        id=IDS["incident"], tenant_id=tenant, plant_id=plant_id, machine_id=IDS["machine"], order_id=IDS["order"],
        correlation_id="cor-INC-2841", dedupe_key="evt-F27-PO2841-d0",
        title="Packaging Line 4 conveyor-drive fault F27 (PO-2841)",
        severity=Severity.S2, state=WorkflowState.INTERVENTION_RECORDED, fault_code="F27",
        current_contract_id=None, opened_at=now - timedelta(hours=5),
    ))
    session.flush()  # tier: incidents + work orders (intervention references both)
    session.add(Intervention(
        id=IDS["intervention_1"], tenant_id=tenant, plant_id=plant_id, incident_id=IDS["incident"],
        work_order_id=IDS["wo_align"], machine_id=IDS["machine"], component_id=IDS["coupling"],
        sequence=1, kind="coupling_alignment", title="Coupling-alignment correction",
        description="Corrected motor-drive coupling alignment following motor replacement (WO-8701).",
        hypothesis="Vibration/F27 caused by coupling misalignment introduced during motor replacement.",
        status=InterventionStatus.COMPLETED, technician_id=IDS["tech_lang"],
        proposed_at=now - timedelta(minutes=70), completed_at=now - timedelta(minutes=10),
    ))

    # ── Open MAIA alert (front of the loop) — the agent will triage THIS into a new incident ──
    session.add(MaiaAlert(
        id=IDS["alert"], tenant_id=tenant, plant_id=plant_id, source="MAIA",
        kind="fault_recurrence", machine_id=IDS["machine"], order_id=IDS["order"], fault_code="F27",
        severity=Severity.S2, status="open", detected_at=now - timedelta(minutes=6),
        correlation_id="cor-ALERT-7731",
        message=("MAIA: Packaging Line 4 conveyor-drive — fault F27 repeating with rising vibration "
                 "(3.1 → 7.4 mm/s), temperature 84 °C, cycle time 14.8 s and scrap 4.8%. Several short "
                 "stops in the last hour. Motor replaced 9 days ago."),
        signals={"vibration_from": 3.1, "vibration_to": 7.4, "temp_c": 84.0, "cycle_time_s": 14.8,
                 "scrap_pct": 4.8, "fault_code": "F27", "short_stops": 5, "motor_replaced_days_ago": 9},
    ))

    session.commit()
    return {"seeded": True, "ids": IDS}


def order_remaining(session: Session) -> int:
    order = session.get(ProductionOrder, IDS["order"])
    return order.qty_remaining if order else 0


def find_user_by_role(session: Session, role: Role) -> User | None:
    return session.exec(select(User).where(User.role == role)).first()

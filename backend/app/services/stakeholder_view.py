"""Stakeholder views — each role sees only the evidence, actions, and approvals relevant to it.

A declarative contract: for each persona, which mission tabs are relevant, what it may *do*, and what it may
*approve*. The frontend uses this to tailor the mission view per role; the gateway still enforces the actual
authorization (this is presentation, not a permission grant). The app's four human roles map onto the
richer persona set below.
"""

from __future__ import annotations

from typing import Optional

# all mission tab keys (kept in sync with the frontend mission page)
_ALL_TABS = [
    "overview", "diagnosis", "reasoning", "decision", "reliability", "signature", "comparability",
    "closure-risk", "disposition", "recovery-debt", "sensor-trust", "lot-at-risk", "contract", "evidence",
    "timeline", "contingency", "provenance", "outcome", "certificate", "stakeholder",
]

STAKEHOLDER_VIEWS: dict[str, dict] = {
    "operator": {
        "label": "Operator",
        "focus": "Run the line; report anything unexpected. Minimal recovery detail.",
        "tabs": ["overview", "timeline"],
        "can_act": ["report unexpected condition"],
        "can_approve": [],
    },
    "maintenance_technician": {
        "label": "Maintenance technician",
        "focus": "Do the physical work; submit measurements and completion evidence.",
        "tabs": ["overview", "reasoning", "evidence", "timeline"],
        "can_act": ["submit measurement", "complete intervention evidence", "report unexpected condition"],
        "can_approve": [],
    },
    "maintenance_supervisor": {
        "label": "Maintenance supervisor",
        "focus": "Own the recovery contract, the diagnosis, contingencies, and escalation.",
        "tabs": ["overview", "diagnosis", "reasoning", "decision", "disposition", "recovery-debt",
                 "contract", "evidence", "timeline", "contingency", "outcome", "certificate"],
        "can_act": ["review recovery contract", "accept diagnosis", "approve contingency", "escalate incident"],
        "can_approve": ["contract_review", "release_contingency", "recovery_debt"],
    },
    "production_supervisor": {
        "label": "Production supervisor",
        "focus": "Keep production moving safely; weigh conditional operation and lots at risk.",
        "tabs": ["overview", "disposition", "recovery-debt", "lot-at-risk", "timeline", "outcome"],
        "can_act": ["request conditional operation"],
        "can_approve": ["recovery_debt"],
    },
    "quality_engineer": {
        "label": "Quality engineer",
        "focus": "Protect product quality; release only when comparable + in-spec; disposition lots.",
        "tabs": ["overview", "evidence", "comparability", "lot-at-risk", "outcome", "certificate"],
        "can_act": ["submit quality result", "review affected lots"],
        "can_approve": ["quality_release"],
    },
    "plant_manager": {
        "label": "Plant manager",
        "focus": "Full oversight across the recovery and its governance.",
        "tabs": list(_ALL_TABS),
        "can_act": ["oversight"],
        "can_approve": ["contract_review", "release_contingency", "recovery_debt", "quality_release"],
    },
    "efficast_implementation_engineer": {
        "label": "Efficast implementation engineer",
        "focus": "Integration, provenance, calibration, and audit — not operational approvals.",
        "tabs": ["overview", "disposition", "comparability", "sensor-trust", "reliability", "provenance"],
        "can_act": [],
        "can_approve": [],
    },
}

# the app's four human roles → personas
ROLE_TO_PERSONA = {
    "technician": "maintenance_technician",
    "supervisor": "maintenance_supervisor",
    "quality_engineer": "quality_engineer",
    "plant_admin": "plant_manager",
}


def stakeholder_view(persona: str) -> dict:
    spec = STAKEHOLDER_VIEWS.get(persona)
    if spec is None:
        return {"available": False, "persona": persona, "reason": "unknown persona"}
    return {"available": True, "persona": persona, **spec}


def all_stakeholder_views() -> list[dict]:
    return [{"persona": k, **v} for k, v in STAKEHOLDER_VIEWS.items()]


def view_for_role(role: Optional[str]) -> dict:
    persona = ROLE_TO_PERSONA.get((role or "").lower(), "plant_manager")
    return stakeholder_view(persona)

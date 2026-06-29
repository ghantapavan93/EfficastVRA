"""The bounded Recovery Agent graph.

A neuro-symbolic, Reflexion-shaped Plan-Executor (docs/AGENT_RESEARCH.md):

    perceive → retrieve → hypothesize → draft → self_critique → decide        (contract drafting)
    observe / reflect                                                          (during monitoring)

The *neural* layer (the ReasoningProvider — deterministic or hosted) proposes; the **symbolic
verifier** (the deterministic recovery evaluator) and the **symbolic gateway** decide and act. This
graph never mutates workflow state, never grants permissions, and never judges recovery — it only
reasons, in the open, and records every step as an ``AgentReasoningTrace``.

The class is intentionally framework-light but LangGraph-compatible: each node is a pure-ish method
taking/returning a small state dict, so the orchestration can be lifted into a LangGraph ``StateGraph``
without touching node logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlmodel import Session, select

from app.adapters.efficast_port import EfficastPort
from app.agent import confidence as conf
from app.agent.trace import record_trace
from app.domain.contract import RecoveryContractSpec
from app.domain.models import (
    Component,
    Incident,
    Intervention,
    Machine,
    RecoveryContract,
)
from app.rag import detect_conflicts, search
from app.reasoning.base import ReasoningProvider
from app.services.evaluator import EvaluationResult

MAX_REFLEXION_ITERS = 2

# Maps a recommended maintenance intervention to the component it acts on (for proposal linkage).
_COMPONENT_FOR_INTERVENTION = {
    "coupling_alignment": "coupling", "bearing_replacement": "bearing",
    "seal_replacement": "seal", "filter_replacement": "filter", "lubrication": "bearing",
}


@dataclass
class DraftResult:
    spec: RecoveryContractSpec
    confidence: float
    critique_ok: bool
    checks: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class RecoveryAgentGraph:
    """Bounded agent reasoning over the existing services. Deterministic evaluator stays authoritative."""

    def __init__(self, session: Session, *, port: EfficastPort, reasoning: ReasoningProvider):
        self.session = session
        self.port = port
        self.reasoning = reasoning

    # ── small helpers ──────────────────────────────────────────────────────────
    @property
    def _mv(self) -> str:
        return self.reasoning.id

    @property
    def _pv(self) -> str:
        return self.reasoning.prompt_version

    def _rec(self, incident, node, title, rationale, **kw):
        return record_trace(
            self.session, incident=incident, node=node, title=title, rationale=rationale,
            model_version=self._mv, prompt_version=self._pv, **kw,
        )

    # ── drafting flow ───────────────────────────────────────────────────────────
    def draft(self, incident: Incident, intervention: Intervention) -> DraftResult:
        machine = self.session.get(Machine, incident.machine_id)
        model = machine.machine_model if machine else ""
        component = self.session.get(Component, intervention.component_id) if intervention.component_id else None
        comp_key = component.kind if component else None

        # 1 ── PERCEIVE: read the live machine snapshot through the Efficast port. ──
        snap = self.port.get_machine_snapshot(incident.machine_id)
        self._rec(
            incident, "perceive",
            f"Perceived {snap.code} post-intervention state",
            (f"Intervention {intervention.kind} ({intervention.status.value if hasattr(intervention.status,'value') else intervention.status}). "
             f"Live readings: vibration {snap.vibration} mm/s, temp {snap.temperature}°C, "
             f"cycle {snap.cycle_time}s, scrap {snap.scrap_pct}%, fault {snap.fault_code or 'none'}. "
             "A completed work order is not yet proof of recovery."),
            inputs={"machine_id": incident.machine_id, "intervention_id": intervention.id},
            outputs={"vibration": snap.vibration, "temperature": snap.temperature,
                     "cycle_time": snap.cycle_time, "scrap_pct": snap.scrap_pct,
                     "fault_code": snap.fault_code, "freshness_s": snap.freshness_s,
                     "source": snap.source},
        )

        # 2 ── RETRIEVE: approval/recency-filtered manuals + the conflict guardrail. ──
        req_query = ("recovery requirements vibration cycle time scrap first-piece quality "
                     "stable cycles after corrective maintenance")
        approved = search(self.session, req_query, machine_model=model, k=4)
        unfiltered = search(self.session, req_query, machine_model=model, k=10, approved_only=False)
        filtered_out = [
            {"document_id": c.document_id, "revision": c.revision,
             "approval_status": c.approval_status, "superseded_by": c.superseded_by}
            for c in unfiltered
            if c.content_hash not in {a.content_hash for a in approved}
        ]
        conflicts = detect_conflicts(self.session, "vibration limit after alignment / bearing",
                                     machine_model=model, component=comp_key)
        self._rec(
            incident, "retrieve",
            f"Retrieved {len(approved)} approved sources; suppressed {len(filtered_out)} non-authoritative",
            ("Retrieval filters by machine applicability and approval status *before* semantic "
             "similarity. Obsolete revisions and unapproved technician notes are excluded and can "
             "never override approved policy."),
            inputs={"query": req_query, "machine_model": model, "component": comp_key},
            outputs={"approved_count": len(approved), "suppressed": filtered_out,
                     "conflicts": conflicts.get("conflicts", [])},
            citations=[{"document_id": c.document_id, "section": c.section,
                        "revision": c.revision, "approval_status": c.approval_status,
                        "excerpt": c.content[:160]} for c in approved],
        )

        # 3 ── HYPOTHESIZE: compare against history; rank failure hypotheses. ──
        hist = self.reasoning.compare_historical_interventions(session=self.session, incident=incident)
        hypotheses = [
            {"hypothesis": "Coupling misalignment corrected by the current intervention",
             "stance": "being verified", "prior": "primary"},
        ]
        if hist.get("match"):
            hypotheses.append({
                "hypothesis": "Latent drive-end bearing degradation (would recur F27 mid-window)",
                "stance": "watch", "prior": "elevated",
                "basis": hist.get("similarity"), "ref": hist.get("historical_incident_id")})
        self._rec(
            incident, "hypothesize",
            "Ranked recovery hypotheses against historical precedent",
            (hist.get("similarity", "No comparable historical incident found.")
             + (f" Recommended contingency on recurrence: {hist.get('recommended_contingency')}."
                if hist.get("match") else "")),
            inputs={"fault_code": incident.fault_code},
            outputs={"hypotheses": hypotheses, "historical_match": hist.get("match", False)},
            citations=hist.get("citations", []),
        )

        # 4 ── DRAFT: structure the Recovery Contract spec. ──
        spec = self.reasoning.extract_recovery_requirements(
            incident=incident, intervention=intervention,
            retrieved=[{"document_id": c.document_id, "section": c.section} for c in approved],
        )
        self._rec(
            incident, "draft",
            f"Drafted {spec.contract_no} v{spec.version} — {len(spec.all_conditions())} conditions",
            ("Translated approved recovery requirements into a structured, deterministically-"
             "evaluable contract: machine, production and quality conditions, required human "
             "evidence, approval gates, verification window, and closure/reopening policy."),
            outputs={
                "contract_no": spec.contract_no, "version": spec.version,
                "machine_conditions": [c.key for c in spec.machine_conditions],
                "production_conditions": [c.key for c in spec.production_conditions],
                "quality_conditions": [c.key for c in spec.quality_conditions],
                "evidence": [e.key for e in spec.evidence_requirements],
                "approvals": [a.key for a in spec.approval_requirements],
                "required_stable_cycles": spec.verification_window.required_stable_cycles,
            },
        )

        # 5 ── SELF_CRITIQUE: symbolic verification of the draft (Reflexion w/ external check). ──
        # Self-reflection alone is unreliable (arXiv 2510.18254), so we critique the draft against a
        # *deterministic* policy checklist rather than trusting the model to grade itself.
        ok, checks, notes = self._critique(spec)
        revision = 0
        # (Deterministic templates already satisfy the checklist; the loop is the seam by which a
        #  hosted model's draft would be revised until it does. Bounded to MAX_REFLEXION_ITERS.)
        while not ok and revision < MAX_REFLEXION_ITERS:
            revision += 1
            ok, checks, notes = self._critique(spec)
        self._rec(
            incident, "self_critique",
            ("Draft satisfies approved recovery policy" if ok
             else "Draft is missing required policy elements"),
            ("Deterministic checklist over the draft: originating-fault non-recurrence is a reopening "
             "trigger; a full stable-cycle window is required; quality release is gated on a human; "
             "and the required approvals/evidence are present. The model cannot weaken any of these."),
            outputs={"critique_ok": ok, "checks": checks},
            revision=revision,
        )

        # 6 ── DECIDE: hand the contract to humans for review (no autonomous closure). ──
        c = 0.40 if ok else 0.20
        self._rec(
            incident, "decide",
            "Contract ready for human review",
            ("The agent proposes; it does not close. The contract now requires human review/approval "
             "before monitoring begins. Confidence in *recovery* stays deliberately low until the "
             "verification window produces evidence."),
            outputs={"next": "RECOVERY_CONTRACT_REVIEWED", "owner": "supervisor"},
            confidence=c,
        )
        return DraftResult(spec=spec, confidence=c, critique_ok=ok, checks=checks, notes=notes)

    def _critique(self, spec: RecoveryContractSpec) -> tuple[bool, list[dict], list[str]]:
        conds = spec.all_conditions()
        ops = {c.op.value for c in conds}
        checks = [
            {"check": "originating-fault non-recurrence is enforced",
             "ok": any(c.op.value == "not_recur" for c in conds)
                   and spec.reopening_policy.reopen_on_fault_recurrence},
            {"check": "a full stable-cycle window is required (>= 30)",
             "ok": any(c.op.value == "count_gte" for c in conds)
                   and spec.verification_window.required_stable_cycles >= 30},
            {"check": "quality release is present and human-gated",
             "ok": len(spec.quality_conditions) >= 1
                   and any(a.required_before == "quality_release" or "quality" in a.key
                           for a in spec.approval_requirements + [])
                   or any(e.required_before in ("quality_release", "closure")
                          for e in spec.evidence_requirements)},
            {"check": "post-intervention measurement evidence is required",
             "ok": any(e.kind.value in ("measurement", "completion") or "measure" in e.key
                       for e in spec.evidence_requirements)},
            {"check": "closure requires all conditions + stable window + quality",
             "ok": spec.closure_policy.require_all_conditions
                   and spec.closure_policy.require_stable_window
                   and spec.closure_policy.require_quality_release},
        ]
        notes = [c["check"] for c in checks if not c["ok"]]
        return (all(c["ok"] for c in checks), checks, notes)

    # ── triage flow (front of the loop: MAIA alert → diagnosis → proposal) ───────
    def triage(self, incident: Incident, alert) -> dict:
        """Diagnose a MAIA alert and propose an intervention. Pure reasoning over the alert + live
        snapshot + approved manuals + historical precedent — it proposes; a human accepts."""
        machine = self.session.get(Machine, incident.machine_id)
        model = machine.machine_model if machine else ""
        sig = dict(getattr(alert, "signals", None) or {})

        # 1 ── PERCEIVE the alert + degraded snapshot ──
        snap = self.port.get_machine_snapshot(incident.machine_id)
        self._rec(
            incident, "perceive",
            f"Received MAIA alert {getattr(alert, 'id', '')} on {snap.code}",
            (getattr(alert, "message", "") or
             f"Fault {snap.fault_code or incident.fault_code} with elevated vibration/temperature."),
            inputs={"alert_id": getattr(alert, "id", None), "kind": getattr(alert, "kind", None)},
            outputs={"vibration": snap.vibration, "temperature": snap.temperature,
                     "cycle_time": snap.cycle_time, "scrap_pct": snap.scrap_pct,
                     "fault_code": snap.fault_code, "signals": sig},
            contract_id=None,
        )

        # ── Gather grounding (approved procedures + historical precedent), then DIAGNOSE. The diagnosis
        #    is the agent's real analytical step: a hosted model reasons over the snapshot + manual
        #    excerpts + history; the deterministic provider returns the same grounded baseline. Either way
        #    it is *advisory* — a human accepts it, and the deterministic evaluator (never this graph)
        #    decides whether recovery actually holds. ──
        cites = search(self.session, "conveyor drive vibration alignment bearing fault corrective",
                       machine_model=model, k=4)
        hist = self.reasoning.compare_historical_interventions(session=self.session, incident=incident)
        retrieved = [{"document_id": c.document_id, "section": c.section, "excerpt": c.content[:160]}
                     for c in cites]
        dx = self.reasoning.diagnose_alert(
            incident=incident, snapshot=snap, signals=sig, retrieved=retrieved, history=hist)

        # 2 ── CLASSIFY the degradation (from the diagnosis) ──
        self._rec(
            incident, "classify",
            f"Classified degradation as {dx.degradation_kind.replace('_', ' ')}",
            dx.classification_rationale,
            outputs={"degradation_kind": dx.degradation_kind, "fault_code": incident.fault_code,
                     "reasoning_source": dx.source,
                     "motor_replaced_days_ago": sig.get("motor_replaced_days_ago")},
        )

        # 3 ── RETRIEVE approved procedures (with the conflict guardrail) ──
        self._rec(
            incident, "retrieve",
            f"Retrieved {len(cites)} approved drivetrain procedures",
            "Approval/recency-filtered retrieval; obsolete or unapproved notes are excluded.",
            citations=[{"document_id": c.document_id, "section": c.section, "revision": c.revision,
                        "approval_status": c.approval_status, "excerpt": c.content[:160]} for c in cites],
        )

        # 4 ── HYPOTHESIZE root causes (from the diagnosis, against history) ──
        self._rec(
            incident, "hypothesize",
            ("Ranked root causes; primary cause first, with a latent risk flagged"
             if any(r.get("likelihood") == "latent" for r in dx.root_causes)
             else "Ranked root causes from live state, manuals, and precedent"),
            hist.get("similarity") or dx.summary,
            outputs={"root_causes": dx.root_causes, "reasoning_source": dx.source},
            citations=hist.get("citations", []),
        )

        # 5 ── PROPOSE the first intervention (the agent proposes; a human accepts) ──
        comp_kind = _COMPONENT_FOR_INTERVENTION.get(dx.recommended_kind)
        component = (
            self.session.exec(
                select(Component).where(Component.machine_id == incident.machine_id)
                .where(Component.kind == comp_kind)
            ).first() if comp_kind else None
        )
        recommended = {
            "kind": dx.recommended_kind,
            "title": dx.recommended_title,
            "description": dx.recommended_description,
            "hypothesis": dx.recommended_hypothesis,
            "component_id": component.id if component else None,
        }
        diagnosis = {
            "summary": dx.summary,
            "degradation_kind": dx.degradation_kind,
            "root_causes": dx.root_causes,
            "recommended_intervention": recommended,
            "contingency": dx.contingency,
            "citations": [{"document_id": c.document_id, "section": c.section} for c in cites],
            "diagnostic_confidence": dx.diagnostic_confidence,
            "reasoning_source": dx.source,
        }
        self._rec(
            incident, "propose",
            f"Proposed: {recommended['title']} (awaiting human acceptance)",
            ("The agent proposes the intervention and the verification plan; it does not perform "
             "physical work or accept its own diagnosis. A supervisor must accept before the "
             "intervention is recorded."),
            outputs={"recommended_intervention": recommended, "contingency": dx.contingency,
                     "diagnostic_confidence": dx.diagnostic_confidence, "reasoning_source": dx.source,
                     "next": "INTERVENTION_PROPOSED", "owner": "supervisor"},
        )
        return diagnosis

    # ── monitoring flow ─────────────────────────────────────────────────────────
    def observe(
        self, incident: Incident, contract: RecoveryContract, result: EvaluationResult,
        *, cycle: Optional[int] = None, kind: str = "observe",
    ) -> float:
        """Record an observation/reflection over the deterministic evaluator's verdict and return the
        (heuristic, uncalibrated) recovery confidence. Called at salient moments during monitoring."""
        c = conf.recovery_confidence(result)
        label = conf.confidence_label(c)

        if result.verdict == "violated":
            explain = self.reasoning.explain_recovery_failure(contract=contract, result=result)
            self._rec(
                incident, "reflect",
                explain.get("headline", "Recovery contract violated"),
                explain.get("detail", "") + " " + explain.get("recommendation", ""),
                inputs={"cycle": cycle, "violated": result.violated_keys},
                outputs={"verdict": result.verdict, "human_message": explain.get("human_message"),
                         "recommendation": explain.get("recommendation")},
                confidence=c, contract_id=contract.id,
            )
        elif result.verdict == "verified":
            self._rec(
                incident, "decide",
                "Recovery verified — closure justified",
                (f"{result.stable_streak}/{result.required_stable_cycles} stable cycles completed, "
                 "every condition PASSED, and quality release is approved by a quality engineer. "
                 "Closure is now justified by evidence, not by a completed work order."),
                inputs={"cycle": cycle},
                outputs={"verdict": result.verdict, "stable_streak": result.stable_streak},
                confidence=c, contract_id=contract.id,
            )
        else:
            self._rec(
                incident, "observe",
                f"Monitoring — confidence {label} ({c:.0%})",
                (f"{result.stable_streak}/{result.required_stable_cycles} stable cycles. "
                 + ("All technical conditions met; awaiting human quality release. "
                    if result.awaiting_quality else
                    "Holding judgement: early stability is not yet proof across the full window.")),
                inputs={"cycle": cycle},
                outputs={"verdict": result.verdict, "stable_streak": result.stable_streak,
                         "awaiting_quality": result.awaiting_quality},
                confidence=c, contract_id=contract.id,
            )
        return c

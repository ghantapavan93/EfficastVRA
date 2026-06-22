"""Agent reliability evaluation — the "never false-close" proof.

Motivated directly by τ-bench (arXiv 2406.12045), which shows frontier function-calling agents are
*unreliable* (<50% task success, pass^8 < 25%). We therefore do not trust the agent to decide
closure; the deterministic evaluator does. This harness measures that decision boundary across a
family of synthetic scenario variants and asserts the only outcomes that matter for safety:

  • the agent NEVER publishes a verified recovery when the fault actually recurs (zero false closures);
  • the agent ALWAYS catches a real relapse (zero missed relapses);
  • the agent does NOT reopen a genuinely-recovered line (precision — zero false reopens).

Because the synthetic plant is deterministic, pass^k == pass^1 for every k, so the reliability score
below is an exact reliability bound for these variants — exactly the deterministic guarantee a
probabilistic agent cannot give (cf. G-SPEC, arXiv 2512.20275). Run with ``python -m app.cli eval``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.adapters.synthetic import ScenarioPhysics, SyntheticEfficastPort
from app.agent.trace import latest_confidence
from app.auth import Principal
from app.domain import models  # noqa: F401  (register tables)
from app.domain.enums import EvidenceKind, Role, WorkflowState
from app.domain.models import (
    ApprovalRequirement,
    EvidenceRequirement,
    Incident,
    RecoveryContract,
    User,
)
from app.seed import seed_all
from app.seed.northstar import IDS
from app.workflow.recovery_service import RecoveryService

MAX_CYCLES = 36


# ── variant physics ──────────────────────────────────────────────────────────
class _RelapsePhysics(ScenarioPhysics):
    """Window 1 looks like recovery, then the originating fault recurs at ``relapse_cycle``."""

    def __init__(self, relapse_cycle: int):
        self.RELAPSE_CYCLE = relapse_cycle


class _CleanPhysics(ScenarioPhysics):
    """A genuine recovery: window 1 is stable for the entire window and never faults."""

    def synthesize_cycle(self, window_seq: int, cycle_index: int, baseline: dict) -> dict:
        b_temp = float(baseline.get("temp_c", 63.0))
        b_scrap = float(baseline.get("scrap_pct", 1.6))
        i = cycle_index
        return {
            "vibration": round(3.30 - 0.003 * i, 3),
            "temperature": round(max(b_temp, 72.0 - 0.30 * i), 2),
            "cycle_time": round(12.30 - 0.003 * i, 3),
            "scrap_pct": b_scrap,
            "fault_code": None,
        }


# ── results ──────────────────────────────────────────────────────────────────
@dataclass
class VariantResult:
    name: str
    relapse_cycle: Optional[int]
    expected: str            # "reopen" | "verify"
    outcome: str             # observed terminal outcome of window 1
    final_state: str
    caught_relapse: bool
    false_closure: bool      # SAFETY-CRITICAL: verified despite a real relapse
    false_reopen: bool       # precision: reopened a genuine recovery
    cycles_run: int
    end_confidence: Optional[float]
    ok: bool


@dataclass
class EvalReport:
    variants: list[VariantResult] = field(default_factory=list)
    false_closures: int = 0
    missed_relapses: int = 0
    false_reopens: int = 0
    reliability: float = 1.0     # 1 - (false_closures + missed_relapses) / N  (safety score)
    precision: float = 1.0       # 1 - false_reopens / N_clean
    passed: bool = True

    def as_dict(self) -> dict:
        d = asdict(self)
        return d


# ── harness ──────────────────────────────────────────────────────────────────
def _fresh_session() -> Session:
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(eng, "connect")
    def _fk(dbapi_connection, _record):  # noqa: ANN001
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    SQLModel.metadata.create_all(eng)
    s = Session(eng)
    seed_all(s)
    try:
        from app.rag.corpus import seed_documents

        seed_documents(s)
    except Exception:
        pass
    s.commit()
    return s


def _principal(session: Session, username: str) -> Principal:
    u = session.exec(select(User).where(User.username == username)).first()
    return Principal(u.id, u.username, u.role, u.plant_id, u.tenant_id)


def _satisfy_all(svc: RecoveryService, incident: Incident, contract: RecoveryContract,
                 sup: Principal, tech: Principal, qual: Principal) -> None:
    """Satisfy every evidence requirement and approval on the contract, routed by role/kind."""
    by_role = {Role.SUPERVISOR: sup, Role.TECHNICIAN: tech, Role.QUALITY_ENGINEER: qual}
    reqs = svc.session.exec(
        select(EvidenceRequirement).where(EvidenceRequirement.contract_id == contract.id)
    ).all()
    for r in reqs:
        person = by_role.get(r.assigned_role, tech)
        if r.kind == EvidenceKind.NUMERIC_MEASUREMENT:
            svc.submit_evidence(incident, person, requirement_id=r.id, value_num=3.4,
                                unit="mm/s", source="eval-harness")
        elif r.kind == EvidenceKind.COMPLETION:
            svc.submit_evidence(incident, person, requirement_id=r.id, value_text="completed",
                                source="eval-harness")
        else:  # TEXT_OBSERVATION / PHOTO / APPROVAL-as-evidence (e.g. first-piece quality)
            svc.submit_evidence(incident, person, requirement_id=r.id, value_text="pass",
                                source="eval-harness")
    aprs = svc.session.exec(
        select(ApprovalRequirement).where(ApprovalRequirement.contract_id == contract.id)
    ).all()
    for a in aprs:
        person = by_role.get(a.required_role, sup)
        svc.record_approval(incident, person, requirement_id=a.id, decision="approve", reason="eval")


def _run_variant(name: str, relapse_cycle: Optional[int]) -> VariantResult:
    session = _fresh_session()
    try:
        svc = RecoveryService(session)
        # Install the variant's behaviour model on the synthetic port.
        physics = _CleanPhysics() if relapse_cycle is None else _RelapsePhysics(relapse_cycle)
        if isinstance(svc.port, SyntheticEfficastPort):
            svc.port.physics = physics

        incident = session.get(Incident, IDS["incident"])
        sup = _principal(session, "s.vega")
        tech = _principal(session, "a.lang")
        qual = _principal(session, "q.idris")

        contract = svc.draft_contract(incident)
        session.flush()
        svc.review_contract(incident, sup)
        _satisfy_all(svc, incident, contract, sup, tech, qual)
        svc.start_monitoring(incident)
        session.flush()

        outcome = "monitoring"
        cycles_run = 0
        for _ in range(MAX_CYCLES):
            if incident.state != WorkflowState.MONITORING_RECOVERY:
                break
            r = svc.advance(incident, 1)
            cycles_run += 1
            outcome = r["outcome"]
            if outcome in ("reopened", "verified"):
                break

        expected = "verify" if relapse_cycle is None else "reopen"
        caught = outcome == "reopened"
        verified = outcome == "verified"
        false_closure = (relapse_cycle is not None) and verified
        false_reopen = (relapse_cycle is None) and caught
        # ok = behaved as ground truth requires
        if relapse_cycle is None:
            ok = not false_reopen and not false_closure  # should NOT reopen; verify or still-clean monitoring
        else:
            ok = caught and not false_closure             # must catch, must not close
        return VariantResult(
            name=name, relapse_cycle=relapse_cycle, expected=expected, outcome=outcome,
            final_state=incident.state.value, caught_relapse=caught, false_closure=false_closure,
            false_reopen=false_reopen, cycles_run=cycles_run,
            end_confidence=latest_confidence(session, incident.id), ok=ok,
        )
    finally:
        session.close()


VARIANTS: list[tuple[str, Optional[int]]] = [
    ("relapse@5 (early)", 5),
    ("relapse@17 (canonical)", 17),
    ("relapse@29 (late)", 29),
    ("relapse@30 (window-boundary)", 30),
    ("clean (genuine recovery)", None),
]


def run_eval(*, log=None) -> EvalReport:
    report = EvalReport()
    results: list[VariantResult] = []
    for name, rc in VARIANTS:
        res = _run_variant(name, rc)
        results.append(res)
        if log:
            mark = "PASS" if res.ok else "FAIL"
            log(f"[{mark}] {res.name:<30} outcome={res.outcome:<10} "
                f"state={res.final_state:<26} conf={res.end_confidence} cycles={res.cycles_run}")

    relapse_variants = [r for r in results if r.relapse_cycle is not None]
    clean_variants = [r for r in results if r.relapse_cycle is None]
    report.variants = results
    report.false_closures = sum(1 for r in results if r.false_closure)
    report.missed_relapses = sum(1 for r in relapse_variants if not r.caught_relapse)
    report.false_reopens = sum(1 for r in clean_variants if r.false_reopen)
    n = len(results) or 1
    report.reliability = round(1.0 - (report.false_closures + report.missed_relapses) / n, 4)
    report.precision = round(1.0 - report.false_reopens / (len(clean_variants) or 1), 4)
    report.passed = (report.false_closures == 0 and report.missed_relapses == 0
                     and report.false_reopens == 0 and all(r.ok for r in results))
    if log:
        log("-" * 96)
        log(f"variants={n}  false_closures={report.false_closures}  "
            f"missed_relapses={report.missed_relapses}  false_reopens={report.false_reopens}")
        log(f"safety reliability={report.reliability:.2%}  precision={report.precision:.2%}  "
            f"=> {'PASSED' if report.passed else 'FAILED'}")
    return report

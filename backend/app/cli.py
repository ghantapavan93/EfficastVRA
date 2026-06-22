"""Command-line entry points: ``python -m app.cli <seed|reset|demo|info>``."""

from __future__ import annotations

import sys

from sqlmodel import Session, select

from app.db import drop_all, engine, init_db
from app.domain.models import Incident
from app.seed import seed_all


def cmd_seed() -> None:
    init_db()
    with Session(engine) as s:
        result = seed_all(s)
    print("seed:", result.get("seeded"), "-", result.get("reason", "ok"))


def cmd_reset() -> None:
    drop_all()
    init_db()
    with Session(engine) as s:
        seed_all(s)
        # Seed the RAG corpus too (revision/approval-aware documents).
        try:
            from app.rag.corpus import seed_documents

            n = seed_documents(s)
            print(f"reset: plant seeded, {n} document chunks indexed")
        except Exception as exc:  # corpus optional during early phases
            print(f"reset: plant seeded (documents skipped: {exc})")


def cmd_demo() -> None:
    try:
        from app.workflow.demo import run_demo
    except Exception as exc:
        print(f"demo unavailable: {exc}")
        return
    run_demo()


def cmd_info() -> None:
    with Session(engine) as s:
        incidents = s.exec(select(Incident)).all()
        for inc in incidents:
            print(f"{inc.id:12} {inc.state.value:28} {inc.title}")


def cmd_eval() -> None:
    """Agent reliability eval: prove the agent never false-closes a relapse (no DB needed)."""
    from app.agent.eval import run_eval

    report = run_eval(log=print)
    sys.exit(0 if report.passed else 1)


def main() -> None:
    # Windows consoles default to cp1252; the demo log uses UTF-8 glyphs.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    cmd = sys.argv[1] if len(sys.argv) > 1 else "seed"
    table = {"seed": cmd_seed, "reset": cmd_reset, "demo": cmd_demo, "info": cmd_info,
             "eval": cmd_eval}
    fn = table.get(cmd)
    if fn is None:
        print(f"unknown command '{cmd}'. use: {', '.join(table)}")
        sys.exit(2)
    fn()


if __name__ == "__main__":
    main()

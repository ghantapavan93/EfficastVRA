"""FastAPI application entry point."""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app import observability
from app.config import get_settings
from app.security_http import SecurityMiddleware
from app.db import engine, init_db
from app.domain.models import Plant
from app.gateway.gateway import GatewayError
from app.workflow.audit import drain_outbox, outbox_stats
from app.workflow.recovery_service import WorkflowError
from app.workflow.state_machine import StateError

logging.basicConfig(level=logging.INFO, format='{"level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}')
log = logging.getLogger("vra")
_settings = get_settings()


def _publish_sink(topic: str, payload: dict, correlation_id: str) -> None:
    """Where published outbox events go. A real deployment swaps this for a broker producer
    (Kafka/Redpanda/MQTT); here it is a structured log line."""
    log.info('outbox_published topic=%s correlation_id=%s', topic, correlation_id)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    with Session(engine) as s:
        if s.exec(select(Plant)).first() is None:
            from app.rag.corpus import seed_documents
            from app.seed import seed_all

            seed_all(s)
            seed_documents(s)
            log.info("seeded synthetic Northstar scenario on startup")
    yield


app = FastAPI(
    title="Verified Recovery Agent",
    version="0.1.0",
    description="Independent, Efficast-aligned manufacturing AI prototype. Synthetic data. "
                "No physical machine control.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[_settings.frontend_origin, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def observability_mw(request: Request, call_next):
    """Correlation IDs + structured access logging, and the outbox relay after mutations.

    Every request gets/propagates an ``X-Correlation-Id``. After a successful mutating request the
    transactional outbox is drained in a fresh session (sequential — never a concurrent SQLite
    writer), so committed decisions are published promptly without extra infrastructure.
    """
    cid = request.headers.get("X-Correlation-Id") or f"req-{uuid.uuid4().hex[:12]}"
    request.state.correlation_id = cid
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Correlation-Id"] = cid
    ms = (time.perf_counter() - start) * 1000
    observability.record_request(status=response.status_code, ms=ms)
    log.info('request method=%s path=%s status=%d ms=%.1f correlation_id=%s',
             request.method, request.url.path, response.status_code, ms, cid)
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and response.status_code < 400:
        try:
            with Session(engine) as s:
                if drain_outbox(s, sink=_publish_sink):
                    s.commit()
        except Exception:  # never fail a request because the relay hiccuped
            log.warning('outbox_drain_failed correlation_id=%s', cid)
    return response


# Edge security: hardening headers, body-size guard, per-identity rate limiting. Registered after the
# observability middleware so it is the OUTERMOST layer — it can reject abusive requests before any
# handler runs and stamp security headers onto every response (including short-circuited 413/429s).
app.add_middleware(SecurityMiddleware)


@app.exception_handler(GatewayError)
def _gateway_error(_req: Request, exc: GatewayError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code,
                        content={"detail": str(exc), "code": exc.code, "stage": exc.stage})


@app.exception_handler(WorkflowError)
def _workflow_error(_req: Request, exc: WorkflowError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc), "code": exc.code})


@app.exception_handler(StateError)
def _state_error(_req: Request, exc: StateError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc), "code": exc.code})


@app.get("/health")
@app.get("/healthz")
@app.get("/api/health")
def health() -> dict:
    db_ok = True
    outbox: dict = {}
    try:
        with Session(engine) as s:
            s.exec(select(Plant).limit(1)).first()   # exercises the DB connection
            outbox = outbox_stats(s)
    except Exception as exc:  # noqa: BLE001
        db_ok = False
        log.warning('health_db_check_failed err=%s', exc)
    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
        "outbox": outbox,
        "environment": _settings.environment,
        "demo_mode": _settings.demo_mode,
        "reasoning": _settings.reasoning_provider,
    }


from app.api.routes import router as api_router  # noqa: E402
from app.api.intake_routes import router as intake_router  # noqa: E402

app.include_router(api_router)
app.include_router(intake_router)

if _settings.demo_mode:
    from app.api.demo_routes import router as demo_router  # noqa: E402

    app.include_router(demo_router)

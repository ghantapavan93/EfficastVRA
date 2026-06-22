"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.config import get_settings
from app.db import engine, init_db
from app.domain.models import Plant
from app.gateway.gateway import GatewayError
from app.workflow.recovery_service import WorkflowError
from app.workflow.state_machine import StateError

logging.basicConfig(level=logging.INFO, format='{"level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}')
log = logging.getLogger("vra")
_settings = get_settings()


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
    return {"status": "ok", "environment": _settings.environment, "demo_mode": _settings.demo_mode,
            "reasoning": _settings.reasoning_provider}


from app.api.routes import router as api_router  # noqa: E402

app.include_router(api_router)

if _settings.demo_mode:
    from app.api.demo_routes import router as demo_router  # noqa: E402

    app.include_router(demo_router)

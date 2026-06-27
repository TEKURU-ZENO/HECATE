"""HECATE telemetry-service — FastAPI Application entrypoint."""

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .api.routes import router

log = structlog.get_logger()

app = FastAPI(
    title="HECATE telemetry-service",
    description="FastAPI service that accepts telemetry pushes (metrics, logs) and publishes to Kafka.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)
app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "telemetry-service", "version": "0.1.0"}


@app.on_event("startup")
async def startup_event():
    log.info("telemetry-service.started")


# HECATE Production Edition Standardized Health & Readiness Probes
@app.get("/ready")
async def ready_check_probe():
    # Standard readiness probe
    return {"status": "ready", "service": "telemetry-service"}

@app.get("/live")
async def live_check_probe():
    # Standard liveness probe
    return {"status": "live", "service": "telemetry-service"}

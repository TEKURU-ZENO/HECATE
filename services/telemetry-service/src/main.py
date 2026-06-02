"""HECATE telemetry-service — FastAPI Application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from .api.routes import router
from .config import settings
import structlog

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
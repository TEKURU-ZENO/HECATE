import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router

log = structlog.get_logger()

app = FastAPI(
    title="HECATE forecasting-service",
    description="FastAPI service running linear regression capacity and failure forecasts.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "forecasting-service", "version": "0.1.0"}


@app.on_event("startup")
async def startup_event():
    log.info("forecasting_service.started")


# HECATE Production Edition Standardized Health & Readiness Probes
@app.get("/ready")
async def ready_check_probe():
    # Standard readiness probe
    return {"status": "ready", "service": "forecasting-service"}

@app.get("/live")
async def live_check_probe():
    # Standard liveness probe
    return {"status": "live", "service": "forecasting-service"}

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app)
except Exception:
    @app.get("/metrics")
    async def metrics_endpoint_probe():
        return 'hecate_service_up{service="forecasting-service"} 1.0\n'

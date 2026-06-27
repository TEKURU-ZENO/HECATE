import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router

log = structlog.get_logger()

app = FastAPI(title="HECATE Policy Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.on_event("startup")
async def startup():
    log.info("policy_service.started")


# HECATE Production Edition Standardized Health & Readiness Probes
@app.get("/ready")
async def ready_check_probe():
    # Standard readiness probe
    return {"status": "ready", "service": "policy-service"}

@app.get("/live")
async def live_check_probe():
    # Standard liveness probe
    return {"status": "live", "service": "policy-service"}

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app)
except Exception:
    @app.get("/metrics")
    async def metrics_endpoint_probe():
        return 'hecate_service_up{service="policy-service"} 1.0\n'

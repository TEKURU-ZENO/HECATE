import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router as copilot_router
from .api.routes import vector_store_instance
from .config import Settings

log = structlog.get_logger()
settings = Settings()

app = FastAPI(
    title="HECATE copilot-service",
    description="Microservice for semantic search, vector storage, and natural language reliability chat operations.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    log.info(
        "copilot_service.startup",
        host=settings.host,
        port=settings.port,
        mode=settings.copilot_mode,
        refresh_interval=settings.index_refresh_interval,
    )
    # Seed the vector store index immediately on startup
    try:
        vector_store_instance.rebuild_index()
    except Exception as e:
        log.error("copilot_service.initial_index_build_failed", error=str(e))


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "copilot-service"}


app.include_router(copilot_router, prefix="/api/v1/copilot")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host=settings.host, port=settings.port, reload=True)


# HECATE Production Edition Standardized Health & Readiness Probes
@app.get("/ready")
async def ready_check_probe():
    # Standard readiness probe
    return {"status": "ready", "service": "copilot-service"}

@app.get("/live")
async def live_check_probe():
    # Standard liveness probe
    return {"status": "live", "service": "copilot-service"}

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app)
except Exception:
    @app.get("/metrics")
    async def metrics_endpoint_probe():
        return 'hecate_service_up{service="copilot-service"} 1.0\n'

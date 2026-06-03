from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import router, run_anomaly_listener
import structlog

log = structlog.get_logger()

app = FastAPI(title="HECATE Anomaly Service")

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
    run_anomaly_listener()
    log.info("anomaly_service.started")
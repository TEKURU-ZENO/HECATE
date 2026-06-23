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

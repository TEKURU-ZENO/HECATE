from fastapi import FastAPI
import structlog
from src.config import settings
from src.api import routes
from src.graph_client import Neo4jGraphClient, MockGraphClient

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="YYYY-MM-DD HH:mm:ss"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

log = structlog.get_logger()

app = FastAPI(title="HECATE Graph Service", version="0.1.0")


@app.on_event("startup")
async def startup_event():
    log.info("graph_service.startup", host=settings.host, port=settings.port, mode=settings.graph_mode)
    
    client = None
    if settings.graph_mode.lower() == "neo4j":
        try:
            client = Neo4jGraphClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
            log.info("graph_service.neo4j_client_initialized")
        except Exception as e:
            log.warn("graph_service.neo4j_failed_falling_back_to_mock", error=str(e))
            client = MockGraphClient()
    else:
        client = MockGraphClient()
        
    routes.graph_client = client


@app.on_event("shutdown")
async def shutdown_event():
    log.info("graph_service.shutdown")
    if routes.graph_client:
        try:
            routes.graph_client.close()
        except Exception:
            pass


# Include API routes
app.include_router(routes.router, prefix="/api/v1/graph")


@app.get("/")
async def root():
    mode = "mock"
    if routes.graph_client and hasattr(routes.graph_client, "driver"):
        mode = "neo4j"
    return {
        "service": "HECATE Graph Service",
        "status": "healthy",
        "mode": mode,
        "archive_days": settings.archive_days
    }

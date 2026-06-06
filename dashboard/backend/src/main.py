"""HECATE Dashboard API backend."""
import asyncio
import json

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

log = structlog.get_logger()

app = FastAPI(
    title="HECATE Dashboard API Backend",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/v1/incidents")
async def list_incidents():
    return [
        {
            "id": "inc-001",
            "incidentCode": "INC-2024-0001",
            "title": "High memory usage in payment-service",
            "severity": "critical",
            "status": "investigating",
            "serviceName": "payment-service",
            "detectedAt": "2026-06-02T22:34:59Z"
        }
    ]

@app.get("/api/v1/agents")
async def list_agents():
    return [
        {
            "id": "agent-001",
            "agentName": "monitoring-agent",
            "version": "1.3.2",
            "status": "active",
            "healthScore": 0.98
        }
    ]

@app.get("/api/v1/metrics/summary")
async def get_metrics_summary():
    return [
        {
            "serviceName": "payment-service",
            "availability": 94.50,
            "errorRate": 5.50,
            "responseTime": 890,
            "status": "degraded"
        }
    ]

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    log.info("ws.client_connected")
    try:
        while True:
            # Send periodic mock telemetry feed
            await asyncio.sleep(5)
            feed_data = {"type": "telemetry_ping", "uptime": 99.87, "timestamp": "2026-06-02T22:34:59Z"}
            await websocket.send_text(json.dumps(feed_data))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        log.info("ws.client_disconnected")

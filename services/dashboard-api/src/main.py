"""HECATE Dashboard API gateway."""
import asyncio
import json
import threading

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .hecate_db import get_db_connection
from .hecate_events import HecateEventBus

log = structlog.get_logger()

app = FastAPI(title="HECATE Dashboard API")

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
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                log.error("ws.broadcast_failed_removing_connection", error=str(e))
                self.disconnect(connection)

manager = ConnectionManager()

# Background stream to pipe events to dashboard websocket
def start_ws_broadcaster():
    def worker():
        bus = HecateEventBus()
        # Listen to all topics and broadcast
        for event in bus.subscribe(["metrics-topic", "anomaly-topic", "incident-topic", "decision-topic", "remediation-topic"], group_id="ws-group"):
            try:
                # Add topic mapping to make it clear on the frontend
                # Convert Event to socket payload
                asyncio.run(manager.broadcast(event))
            except Exception:
                pass

    t = threading.Thread(target=worker, daemon=True)
    t.start()

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/api/v1/incidents")
async def get_incidents():
    conn, _ = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents ORDER BY detected_at DESC")
    rows = cursor.fetchall()
    res = [dict(row) for row in rows]
    conn.close()
    return res

@app.get("/api/v1/remediations")
async def get_remediations():
    conn, _ = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM remediations ORDER BY executed_at DESC")
    rows = cursor.fetchall()
    res = [dict(row) for row in rows]
    conn.close()
    return res

@app.get("/api/v1/agents")
async def get_agents():
    # Return simulated real agents
    return [
        {"id": "agent-001", "agentName": "monitoring-agent", "version": "0.1.0", "status": "active", "healthScore": 98},
        {"id": "agent-002", "agentName": "detection-agent", "version": "0.1.0", "status": "active", "healthScore": 96},
        {"id": "agent-003", "agentName": "decision-agent", "version": "0.1.0", "status": "active", "healthScore": 94},
        {"id": "agent-004", "agentName": "remediation-agent", "version": "0.1.0", "status": "active", "healthScore": 97}
    ]

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    log.info("ws.client_connected")
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        log.info("ws.client_disconnected")

# Run background thread on startup
@app.on_event("startup")
async def startup_event():
    start_ws_broadcaster()
    log.info("dashboard_api.started")

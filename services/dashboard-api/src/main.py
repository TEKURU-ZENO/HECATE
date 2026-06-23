"""HECATE Dashboard API gateway."""

import asyncio
import json
import threading

import structlog
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class ResolveApprovalRequest(BaseModel):
    action: str
    operator: str = "operator"


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
        for event in bus.subscribe(
            [
                "metrics-topic",
                "anomaly-topic",
                "incident-topic",
                "decision-topic",
                "remediation-topic",
                "learning-topic",
                "recommendation-topic",
                "approval-topic",
            ],
            group_id="ws-group",
        ):
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
        {
            "id": "agent-001",
            "agentName": "monitoring-agent",
            "version": "0.1.0",
            "status": "active",
            "healthScore": 98,
        },
        {
            "id": "agent-002",
            "agentName": "detection-agent",
            "version": "0.1.0",
            "status": "active",
            "healthScore": 96,
        },
        {
            "id": "agent-003",
            "agentName": "rca-agent",
            "version": "0.1.0",
            "status": "active",
            "healthScore": 95,
        },
        {
            "id": "agent-004",
            "agentName": "recommendation-agent",
            "version": "0.1.0",
            "status": "active",
            "healthScore": 94,
        },
        {
            "id": "agent-005",
            "agentName": "decision-agent",
            "version": "0.1.0",
            "status": "active",
            "healthScore": 94,
        },
        {
            "id": "agent-006",
            "agentName": "remediation-agent",
            "version": "0.1.0",
            "status": "active",
            "healthScore": 97,
        },
        {
            "id": "agent-007",
            "agentName": "learning-agent",
            "version": "0.1.0",
            "status": "active",
            "healthScore": 99,
        },
    ]


@app.get("/api/v1/recommendations")
async def get_recommendations():
    conn, _ = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recommendations ORDER BY created_at DESC")
    rows = cursor.fetchall()
    res = [dict(row) for row in rows]
    conn.close()
    return res


@app.get("/api/v1/approvals")
async def get_approvals():
    conn, _ = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM approvals ORDER BY requested_at DESC")
    rows = cursor.fetchall()
    res = [dict(row) for row in rows]
    conn.close()
    return res


@app.post("/api/v1/approvals/{approval_id}/resolve")
async def resolve_approval(approval_id: str, req: ResolveApprovalRequest):
    import time

    conn, _ = get_db_connection()
    cursor = conn.cursor()

    # Query current status to prevent double-resolution/concurrency issues
    cursor.execute(
        "SELECT status, incident_id, incident_type, recommended_action, root_cause_service, risk_level, recommendation_score FROM approvals WHERE id = ?",
        (approval_id,),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Approval not found")

    approval_rec = dict(row)
    if approval_rec["status"] != "pending":
        conn.close()
        raise HTTPException(
            status_code=409,
            detail=f"Approval already resolved. Current status: {approval_rec['status']}",
        )

    # Update approval
    status_str = "approved" if req.action == "approve" else "rejected"
    cursor.execute(
        "UPDATE approvals SET status = ?, decided_at = CURRENT_TIMESTAMP, decided_by = ? WHERE id = ?",
        (status_str, req.operator, approval_id),
    )
    conn.commit()
    conn.close()

    # Publish resolved event to approval-topic
    bus = HecateEventBus()
    payload = {
        "approval_id": approval_id,
        "incident_id": approval_rec["incident_id"],
        "incident_type": approval_rec["incident_type"],
        "service": approval_rec["root_cause_service"],
        "recommended_action": approval_rec["recommended_action"],
        "risk_level": approval_rec["risk_level"],
        "recommendation_score": approval_rec["recommendation_score"],
        "status": status_str,
        "timestamp": time.time(),
    }
    bus.publish("approval-topic", payload)

    return {"status": "success", "resolved_status": status_str}


@app.get("/api/v1/learning/feedback")
async def get_learning_feedback():
    conn, _ = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM operational_memory ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    res = [dict(row) for row in rows]
    conn.close()
    return res


@app.get("/api/v1/learning/stats")
async def get_learning_stats():
    conn, _ = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*), AVG(recovery_time_seconds), AVG(effectiveness_score) FROM operational_memory"
    )
    row = cursor.fetchone()
    count = row[0] if row else 0
    avg_rec = row[1] if row and row[1] is not None else 0.0
    avg_eff = row[2] if row and row[2] is not None else 0.0

    cursor.execute("SELECT COUNT(*) FROM operational_memory WHERE success = 1")
    successful = cursor.fetchone()[0] or 0

    # Determine Top Successful Action
    cursor.execute("""
        SELECT remediation_action, COUNT(*) as successes 
        FROM operational_memory 
        WHERE success = 1 
        GROUP BY remediation_action 
        ORDER BY successes DESC LIMIT 1
    """)
    top_act_row = cursor.fetchone()
    top_action = top_act_row[0] if top_act_row else "None"
    conn.close()
    return {
        "total_incidents": count or 0,
        "avg_recovery_time": round(avg_rec, 1) if avg_rec else 0.0,
        "avg_effectiveness": round(avg_eff, 2) if avg_eff else 0.0,
        "successful_remediations": successful,
        "top_successful_action": top_action,
    }


@app.get("/api/v1/forecast/stats")
async def get_forecast_stats():
    conn, _ = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE prediction_status = 'PREVENTED'")
    prevented = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE prediction_status = 'FALSE_POSITIVE'")
    false_positives = cursor.fetchone()[0] or 0

    total = prevented + false_positives
    accuracy = 1.0
    if total > 0:
        accuracy = prevented / total

    # Retrieve active predictions (status = 'NEW' or 'AWAITING_APPROVAL' and is_predicted = 1)
    cursor.execute(
        "SELECT * FROM incidents WHERE is_predicted = 1 AND status NOT IN ('remediated', 'closed', 'REMEDIATED', 'CLOSED')"
    )
    active_rows = cursor.fetchall()
    active_predictions = [dict(row) for row in active_rows]

    conn.close()

    return {
        "incidents_prevented": prevented,
        "prediction_accuracy": round(accuracy * 100, 1),
        "active_predictions": active_predictions,
    }


@app.post("/api/v1/copilot/chat")
async def copilot_chat(req: dict):
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "http://localhost:8004/api/v1/copilot/chat", json=req, timeout=15.0
            )
            if res.status_code != 200:
                raise HTTPException(status_code=res.status_code, detail=res.text)
            return res.json()
    except httpx.RequestError as e:
        log.error("dashboard_api.copilot_proxy_failed", error=str(e))
        raise HTTPException(status_code=503, detail=f"Copilot service unreachable: {e}")


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

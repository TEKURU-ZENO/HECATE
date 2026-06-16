import time
import uuid

import structlog
from fastapi import APIRouter

from ..hecate_db import get_db_connection

router = APIRouter()
log = structlog.get_logger()


@router.get("/anomalies")
async def get_anomalies():
    conn, use_pg = get_db_connection()
    cursor = conn.cursor()
    if use_pg:
        cursor.execute("SELECT * FROM incidents ORDER BY detected_at DESC")
        rows = cursor.fetchall()
        # Convert psycopg2 Row to dict list
        res = [dict(r) for r in rows]
    else:
        cursor.execute("SELECT * FROM incidents ORDER BY detected_at DESC")
        rows = cursor.fetchall()
        res = [dict(row) for row in rows]
    conn.close()
    return res


# Trigger method runs in background of service
def run_anomaly_listener():
    import threading

    from ..hecate_events import HecateEventBus

    def worker():
        log.info("anomaly_service.listener_started")
        bus = HecateEventBus()
        for anomaly in bus.subscribe(["anomaly-topic"], group_id="anomaly-service-group"):
            try:
                # Add Incident record
                conn, use_pg = get_db_connection()
                cursor = conn.cursor()

                incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
                code = f"HEC-{uuid.uuid4().hex[:6].upper()}"
                title = f"{anomaly.get('anomaly_type').replace('_', ' ').capitalize()} in {anomaly.get('service_name')}"
                severity = "critical" if anomaly.get("anomaly_type") == "cpu_high" else "high"
                status = "open"

                # Insert incident
                if use_pg:
                    cursor.execute(
                        "INSERT INTO incidents (id, incident_code, title, severity, status, service_name, root_cause, confidence_score, detected_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())",
                        (
                            incident_id,
                            code,
                            title,
                            severity,
                            status,
                            anomaly.get("service_name"),
                            f"Value threshold exceeded: {anomaly.get('metric_name')} = {anomaly.get('current_value')}",
                            1.0,
                        ),
                    )
                else:
                    cursor.execute(
                        "INSERT INTO incidents (id, incident_code, title, severity, status, service_name, root_cause, confidence_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            incident_id,
                            code,
                            title,
                            severity,
                            status,
                            anomaly.get("service_name"),
                            f"Value threshold exceeded: {anomaly.get('metric_name')} = {anomaly.get('current_value')}",
                            1.0,
                        ),
                    )
                conn.commit()
                conn.close()

                # Publish Incident event
                incident_payload = {
                    "incident_id": incident_id,
                    "incident_code": code,
                    "title": title,
                    "severity": severity,
                    "status": status,
                    "service_name": anomaly.get("service_name"),
                    "namespace": anomaly.get("namespace"),
                    "anomaly_id": anomaly.get("id"),
                    "timestamp": time.time(),
                }
                bus.publish("incident-topic", incident_payload)

            except Exception as e:
                log.error("anomaly_service.failed_to_log_incident", error=str(e))

    t = threading.Thread(target=worker, daemon=True)
    t.start()

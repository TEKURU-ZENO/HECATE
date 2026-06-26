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

                # Deduplicate/suppress duplicate active incidents for same service and type
                is_predicted = 1 if anomaly.get("predicted") else 0
                if use_pg:
                    cursor.execute(
                        "SELECT COUNT(*) FROM incidents WHERE service_name = %s AND is_predicted = %s AND status NOT IN ('remediated', 'closed', 'failed', 'rejected', 'REMEDIATED', 'CLOSED', 'FAILED', 'REJECTED')",
                        (anomaly.get("service_name"), is_predicted)
                    )
                else:
                    cursor.execute(
                        "SELECT COUNT(*) FROM incidents WHERE service_name = ? AND is_predicted = ? AND status NOT IN ('remediated', 'closed', 'failed', 'rejected', 'REMEDIATED', 'CLOSED', 'FAILED', 'REJECTED')",
                        (anomaly.get("service_name"), is_predicted)
                    )
                active_count = cursor.fetchone()[0]
                if active_count > 0:
                    log.info("anomaly_service.duplicate_anomaly_suppressed", service=anomaly.get("service_name"), is_predicted=is_predicted)
                    conn.close()
                    continue

                incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
                code = f"HEC-{uuid.uuid4().hex[:6].upper()}"
                is_predicted = 1 if anomaly.get("predicted") else 0
                pred_conf = float(anomaly.get("confidence", 0.0))
                pred_model = anomaly.get("model", "none")
                lead_time = int(anomaly.get("lead_time_seconds", 0))
                pred_status = "PENDING" if is_predicted else "NONE"

                prefix = "Predicted: " if is_predicted else ""
                title = f"{prefix}{anomaly.get('anomaly_type').replace('_', ' ').capitalize()} in {anomaly.get('service_name')}"
                severity = "critical" if anomaly.get("anomaly_type") == "cpu_high" else "high"
                status = "NEW"

                # Insert incident
                if use_pg:
                    cursor.execute(
                        """
                        INSERT INTO incidents (
                            id, incident_code, title, severity, status, service_name, root_cause, 
                            confidence_score, is_predicted, prediction_confidence, 
                            prediction_model, lead_time_seconds, prediction_status, detected_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        """,
                        (
                            incident_id,
                            code,
                            title,
                            severity,
                            status,
                            anomaly.get("service_name"),
                            f"Value threshold exceeded: {anomaly.get('metric_name')} = {anomaly.get('current_value')}"
                            if not is_predicted
                            else f"Predicted threshold breach: {anomaly.get('metric_name')} = {anomaly.get('current_value')}",
                            1.0,
                            is_predicted,
                            pred_conf,
                            pred_model,
                            lead_time,
                            pred_status,
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO incidents (
                            id, incident_code, title, severity, status, service_name, root_cause, 
                            confidence_score, is_predicted, prediction_confidence, 
                            prediction_model, lead_time_seconds, prediction_status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            incident_id,
                            code,
                            title,
                            severity,
                            status,
                            anomaly.get("service_name"),
                            f"Value threshold exceeded: {anomaly.get('metric_name')} = {anomaly.get('current_value')}"
                            if not is_predicted
                            else f"Predicted threshold breach: {anomaly.get('metric_name')} = {anomaly.get('current_value')}",
                            1.0,
                            is_predicted,
                            pred_conf,
                            pred_model,
                            lead_time,
                            pred_status,
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
                    "is_predicted": is_predicted,
                    "prediction_confidence": pred_conf,
                    "prediction_model": pred_model,
                    "lead_time_seconds": lead_time,
                    "prediction_status": pred_status,
                    "timestamp": time.time(),
                }
                bus.publish("incident-topic", incident_payload)

            except Exception as e:
                log.error("anomaly_service.failed_to_log_incident", error=str(e))

    t = threading.Thread(target=worker, daemon=True)
    t.start()

import os
import time
import math
import uuid
import yaml
import structlog
from datetime import datetime

from .config import Settings
from .hecate_events import HecateEventBus
from .hecate_db import get_db_connection

log = structlog.get_logger()

class LearningAgent:
    """HECATE Learning Agent — Evaluates remediation outcomes to optimize policy accuracy core logic class."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._running = False
        self.event_bus = HecateEventBus(kafka_servers=settings.kafka_bootstrap_servers)
        
        # State stores to track incidents across distributed events
        self.anomaly_types = {}    # anomaly_id -> anomaly_type
        self.active_incidents = {}  # incident_id -> incident details

    def _load_decay_lambda(self) -> float:
        ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        rules_path = os.path.join(ROOT_DIR, "policies", "default-rules.yaml")
        if os.path.exists(rules_path):
            try:
                with open(rules_path, "r") as f:
                    data = yaml.safe_load(f)
                return data.get("learning", {}).get("decay_lambda", 0.02)
            except Exception as e:
                log.error("learning_agent.decay_lambda_load_failed_using_default", error=str(e))
        return 0.02

    async def run(self) -> None:
        self._running = True
        log.info("learning_agent.started")

        topics = [
            "anomaly-topic",
            "incident-topic",
            "rca-topic",
            "decision-topic",
            "remediation-topic"
        ]

        # Consume from the event bus
        for event in self.event_bus.subscribe(topics, group_id="learning-group"):
            if not self._running:
                break
            try:
                await self.process_event(event)
            except Exception as e:
                log.error("learning_agent.event_processing_failed", error=str(e))

    async def process_event(self, event: dict) -> None:
        topic = event.get("event_type") or event.get("anomaly_type")
        
        # 1. Anomaly Event
        if "anomaly_type" in event:
            anomaly_id = event.get("id")
            anomaly_type = event.get("anomaly_type")
            self.anomaly_types[anomaly_id] = anomaly_type
            log.info("learning_agent.recorded_anomaly_type", anomaly_id=anomaly_id, anomaly_type=anomaly_type)

        # 2. Incident Event
        elif event.get("event_type") is None and "incident_id" in event and "anomaly_id" in event:
            # anomaly-service publishes incident event without explicit event_type key
            incident_id = event.get("incident_id")
            anomaly_id = event.get("anomaly_id")
            title = event.get("title")
            
            # Map anomaly_id to anomaly_type
            inc_type = self.anomaly_types.get(anomaly_id)
            if not inc_type:
                # Fallback to title parsing if anomaly event was missed
                title_lower = title.lower()
                if "cpu" in title_lower:
                    inc_type = "cpu_high"
                elif "memory" in title_lower:
                    inc_type = "memory_high"
                elif "restart" in title_lower:
                    inc_type = "restart_high"
                else:
                    inc_type = "unknown"

            self.active_incidents[incident_id] = {
                "incident_id": incident_id,
                "detected_at": event.get("timestamp") or time.time(),
                "incident_type": inc_type,
                "incident_title": title,
                "root_cause_service": event.get("service_name"), # Default to target service
                "remediation_action": None,
                "confidence_score": 1.0, # Default confidence
                "risk_score": 0.0 # Default risk
            }
            log.info("learning_agent.incident_tracked", incident_id=incident_id, type=inc_type)

        # 3. RCA Event
        elif event.get("event_type") == "rca.completed":
            incident_id = event.get("incident_id")
            if incident_id in self.active_incidents:
                rca_res = event.get("rca_result", {})
                self.active_incidents[incident_id]["root_cause_service"] = rca_res.get("root_cause_service")
                self.active_incidents[incident_id]["confidence_score"] = rca_res.get("confidence_score", 1.0)
                self.active_incidents[incident_id]["risk_score"] = rca_res.get("risk_score", 0.0)
                log.info("learning_agent.rca_correlated", incident_id=incident_id, root_cause=rca_res.get("root_cause_service"))

        # 4. Decision Event
        elif "action" in event and "target" in event and "incident_id" in event:
            # decision-agent payload has action, target, incident_id
            incident_id = event.get("incident_id")
            if incident_id in self.active_incidents:
                self.active_incidents[incident_id]["remediation_action"] = event.get("action")
                log.info("learning_agent.decision_correlated", incident_id=incident_id, action=event.get("action"))

        # 5. Remediation Event
        elif "execution_status" in event and "success" in event and "incident_id" in event:
            # remediation-agent outcome payload
            incident_id = event.get("incident_id")
            if incident_id in self.active_incidents:
                await self.evaluate_outcome(incident_id, event)

    async def evaluate_outcome(self, incident_id: str, rem_event: dict) -> None:
        incident_info = self.active_incidents[incident_id]
        
        success = bool(rem_event.get("success", False))
        remediation_action = rem_event.get("action_type") or incident_info["remediation_action"] or "unknown"
        completion_time = rem_event.get("timestamp") or time.time()
        
        # Calculate recovery time in seconds
        recovery_time_seconds = max(1, int(completion_time - incident_info["detected_at"]))
        
        # Calculate effectiveness score using exponential decay
        if not success:
            effectiveness_score = 0.0
        else:
            decay_lambda = self._load_decay_lambda()
            effectiveness_score = round(math.exp(-decay_lambda * recovery_time_seconds), 4)

        log.info(
            "learning_agent.evaluating_remediation_performance",
            incident_id=incident_id,
            action=remediation_action,
            success=success,
            recovery_time=recovery_time_seconds,
            effectiveness=effectiveness_score
        )

        # 1. Store operational memory in Database
        try:
            conn, use_pg = get_db_connection()
            cursor = conn.cursor()
            
            memory_id = str(uuid.uuid4())
            if use_pg:
                cursor.execute(
                    """
                    INSERT INTO operational_memory (
                        id, incident_id, incident_type, incident_title, root_cause_service, 
                        remediation_action, success, recovery_time_seconds, confidence_score, 
                        effectiveness_score, timestamp
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        memory_id, incident_id, incident_info["incident_type"], incident_info["incident_title"],
                        incident_info["root_cause_service"], remediation_action, success, recovery_time_seconds,
                        incident_info["confidence_score"], effectiveness_score
                    )
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO operational_memory (
                        id, incident_id, incident_type, incident_title, root_cause_service, 
                        remediation_action, success, recovery_time_seconds, confidence_score, 
                        effectiveness_score, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        memory_id, incident_id, incident_info["incident_type"], incident_info["incident_title"],
                        incident_info["root_cause_service"], remediation_action, 1 if success else 0, recovery_time_seconds,
                        incident_info["confidence_score"], effectiveness_score
                    )
                )
            conn.commit()
            conn.close()
            log.info("learning_agent.operational_memory_saved", incident_id=incident_id)
        except Exception as e:
            log.error("learning_agent.db_insert_failed", error=str(e))

        # 2. Update Incident status and recovery time in Database
        try:
            conn, use_pg = get_db_connection()
            cursor = conn.cursor()
            status = "remediated" if success else "failed"
            if use_pg:
                cursor.execute(
                    "UPDATE incidents SET status = %s, resolved_at = NOW(), recovery_time_seconds = %s WHERE id = %s",
                    (status, recovery_time_seconds, incident_id)
                )
            else:
                cursor.execute(
                    "UPDATE incidents SET status = ?, resolved_at = datetime('now'), recovery_time_seconds = ? WHERE id = ?",
                    (status, recovery_time_seconds, incident_id)
                )
            conn.commit()
            conn.close()
            log.info("learning_agent.incident_updated_in_db", incident_id=incident_id)
        except Exception as e:
            log.error("learning_agent.incident_update_failed", error=str(e))

        # 3. Publish learning feedback to event bus
        feedback_payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "learning.feedback",
            "schema_version": "1.0.0",
            "incident_id": incident_id,
            "incident_type": incident_info["incident_type"],
            "incident_title": incident_info["incident_title"],
            "root_cause_service": incident_info["root_cause_service"],
            "remediation_action": remediation_action,
            "success": success,
            "recovery_time_seconds": recovery_time_seconds,
            "confidence_score": incident_info["confidence_score"],
            "effectiveness_score": effectiveness_score,
            "timestamp": completion_time
        }
        self.event_bus.publish("learning-topic", feedback_payload)
        
        # Remove from tracking memory
        del self.active_incidents[incident_id]

    async def stop(self) -> None:
        self._running = False
        log.info("learning_agent.stopped")

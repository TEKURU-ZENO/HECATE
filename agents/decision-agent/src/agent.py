import time
import uuid

import httpx
import structlog

from .hecate_events import HecateEventBus

log = structlog.get_logger()

class DecisionAgent:
    def __init__(self, settings) -> None:
        self.settings = settings
        self._running = False
        self.event_bus = HecateEventBus(kafka_servers=settings.kafka_bootstrap_servers)

    async def run(self) -> None:
        self._running = True
        log.info("decision_agent.started")

        for rca_event in self.event_bus.subscribe(["rca-topic"], group_id="decision-group"):
            if not self._running:
                break
            try:
                await self.process_rca_event(rca_event)
            except Exception as e:
                log.error("decision_agent.rca_processing_failed", error=str(e))

    async def process_rca_event(self, rca_event: dict) -> None:
        incident_id = rca_event.get("incident_id")
        rca_result = rca_event.get("rca_result", {})
        root_cause_service = rca_result.get("root_cause_service")
        confidence_score = rca_result.get("confidence_score", 1.0)
        risk_score = rca_result.get("risk_score", 0.0)
        
        # Default fallback namespace
        namespace = rca_event.get("namespace") or "hecate-system"

        log.info("decision_agent.resolving_policy_for_rca", incident_id=incident_id, root_cause=root_cause_service)

        # Query Policy Service API to fetch action mapping based on root cause service
        action = "restart_pod"
        policy_id = "pol-001"
        try:
            async with httpx.AsyncClient() as client:
                # Query local Policy Service running on port 8002
                res = await client.get(
                    "http://localhost:8002/api/v1/policies/match",
                    params={"incident_title": root_cause_service},
                    timeout=2.0
                )
                if res.status_code == 200:
                    data = res.json()
                    action = data.get("action", action)
                    policy_id = data.get("policy_id", policy_id)
        except Exception as e:
            log.warn("decision_agent.policy_service_unreachable_using_local_sqlite_fallback", error=str(e))
            # Fallback to direct SQLite match if Policy service API is down
            from .hecate_db import get_db_connection
            try:
                conn, _ = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT action_definition, id FROM policies WHERE enabled = 1")
                rows = cursor.fetchall()
                conn.close()
                for row in rows:
                    p = dict(row)
                    if "cpu" in p.get("action_definition") and "cpu" in root_cause_service.lower():
                        action = p.get("action_definition")
                        policy_id = p.get("id")
            except Exception as dbe:
                log.error("decision_agent.local_sqlite_query_failed", error=str(dbe))

        # Build precise explicit Decision event payload targeting the root cause service
        decision_payload = {
            "id": str(uuid.uuid4()),
            "event_id": str(uuid.uuid4()),
            "incident_id": incident_id,
            "action": action,
            "target": root_cause_service,
            "namespace": namespace,
            "confidence": confidence_score,
            "risk_score": risk_score,
            "policy_id": policy_id,
            "reason": f"Policy {policy_id} matched RCA root cause: {root_cause_service}",
            "timestamp": time.time()
        }

        log.info("decision_agent.remediation_decision_made", action=action, target=root_cause_service, risk=risk_score)
        self.event_bus.publish("decision-topic", decision_payload)

    async def stop(self) -> None:
        self._running = False
        log.info("decision_agent.stopped")

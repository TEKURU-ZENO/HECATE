import asyncio
import structlog
import uuid
import time
import httpx
from .config import settings
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
        
        for incident in self.event_bus.subscribe(["incident-topic"], group_id="decision-group"):
            if not self._running:
                break
            try:
                await self.process_incident(incident)
            except Exception as e:
                log.error("decision_agent.incident_failed", error=str(e))

    async def process_incident(self, incident: dict) -> None:
        incident_id = incident.get("incident_id")
        title = incident.get("title")
        service_name = incident.get("service_name")
        namespace = incident.get("namespace")
        
        log.info("decision_agent.resolving_policy", incident_id=incident_id, title=title)
        
        # Query Policy Service API to fetch action mapping
        action = "restart_pod"
        policy_id = "pol-001"
        try:
            async with httpx.AsyncClient() as client:
                # Query local Policy Service running on port 8002 (we will run services on consecutive ports locally)
                res = await client.get(
                    "http://localhost:8002/api/v1/policies/match", 
                    params={"incident_title": title},
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
                    if "cpu" in p.get("action_definition") and "cpu" in title.lower():
                        action = p.get("action_definition")
                        policy_id = p.get("id")
            except Exception as dbe:
                log.error("decision_agent.local_sqlite_query_failed", error=str(dbe))
        
        # Build precise explicit Decision event payload
        decision_payload = {
            "id": str(uuid.uuid4()),
            "event_id": str(uuid.uuid4()),
            "incident_id": incident_id,
            "action": action,
            "target": service_name,
            "namespace": namespace,
            "confidence": 1.0,
            "policy_id": policy_id,
            "reason": f"Policy {policy_id} matched alert: {title}",
            "timestamp": time.time()
        }
        
        log.info("decision_agent.remediation_decision_made", action=action, target=service_name)
        self.event_bus.publish("decision-topic", decision_payload)

    async def stop(self) -> None:
        self._running = False
        log.info("decision_agent.stopped")
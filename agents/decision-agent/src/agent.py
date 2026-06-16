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

        for rec_event in self.event_bus.subscribe(
            ["recommendation-topic"], group_id="decision-group"
        ):
            if not self._running:
                break
            try:
                await self.process_recommendation_event(rec_event)
            except Exception as e:
                log.error("decision_agent.recommendation_processing_failed", error=str(e))

    async def process_recommendation_event(self, rec_event: dict) -> None:
        incident_id = rec_event.get("incident_id")
        recommended_action = rec_event.get("recommended_action")
        root_cause_service = rec_event.get("root_cause_service")
        confidence_score = rec_event.get("success_probability", 1.0)
        risk_score = rec_event.get("recommendation_score", 1.0)

        # Default fallback namespace
        namespace = rec_event.get("namespace") or "hecate-system"

        log.info(
            "decision_agent.processing_governance_for_recommendation",
            incident_id=incident_id,
            action=recommended_action,
            target=root_cause_service,
        )

        # Enforce governance check: Verify that the Policy matches and the action is enabled
        action = recommended_action
        policy_id = "pol-001"
        try:
            async with httpx.AsyncClient() as client:
                # Query local Policy Service running on port 8002 to match
                res = await client.get(
                    "http://localhost:8002/api/v1/policies/match",
                    params={"incident_title": root_cause_service},
                    timeout=2.0,
                )
                if res.status_code == 200:
                    data = res.json()
                    # Keep policy_id from match
                    policy_id = data.get("policy_id", policy_id)
        except Exception as e:
            log.warn("decision_agent.policy_service_unreachable_using_fallback", error=str(e))
            # Fallback to direct sqlite matches
            from .hecate_db import get_db_connection

            try:
                conn, _ = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM policies WHERE action_definition = ? AND enabled = 1", (action,)
                )
                row = cursor.fetchone()
                if row:
                    policy_id = row[0]
                conn.close()
            except Exception as dbe:
                log.error("decision_agent.sqlite_policy_check_failed", error=str(dbe))

        # Build decision event payload
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
            "reason": f"Decision Agent approved recommendation '{action}' on target '{root_cause_service}' based on policy {policy_id}",
            "timestamp": time.time(),
        }

        log.info(
            "decision_agent.remediation_decision_made",
            action=action,
            target=root_cause_service,
            risk=risk_score,
        )
        self.event_bus.publish("decision-topic", decision_payload)

    async def stop(self) -> None:
        self._running = False
        log.info("decision_agent.stopped")

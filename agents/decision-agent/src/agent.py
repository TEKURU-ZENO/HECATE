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

        for event in self.event_bus.subscribe(
            ["recommendation-topic", "approval-topic"], group_id="decision-group"
        ):
            if not self._running:
                break
            try:
                if "approval_id" in event:
                    await self.process_approval_event(event)
                else:
                    await self.process_recommendation_event(event)
            except Exception as e:
                log.error("decision_agent.event_processing_failed", error=str(e))

    def calculate_risk(
        self, service_name: str, recommendation_score: float, policy_risk_level: str
    ) -> tuple[float, str]:
        # Policy weight: 0.5 for high, 0.3 for medium, 0.1 for low
        policy_weight = 0.1
        if policy_risk_level.lower() == "high":
            policy_weight = 0.5
        elif policy_risk_level.lower() == "medium":
            policy_weight = 0.3

        # Criticality weight: 0.2 for db nodes, 0.1 for services
        criticality_weight = 0.1
        if "db" in service_name.lower():
            criticality_weight = 0.2

        # Blast radius weight: 0.2 for gateway, 0.1 for core services
        blast_radius_weight = 0.05
        if service_name == "gateway":
            blast_radius_weight = 0.2
        elif service_name in ["order-service", "payment-service"]:
            blast_radius_weight = 0.1

        # Uncertainty factor based on recommendation score
        recommendation_uncertainty = (1.0 - recommendation_score) * 0.2

        risk_score = (
            policy_weight + criticality_weight + blast_radius_weight + recommendation_uncertainty
        )
        risk_score = round(risk_score, 2)

        risk_level = "LOW"
        if risk_score >= 0.6:
            risk_level = "HIGH"
        elif risk_score >= 0.4:
            risk_level = "MEDIUM"

        return risk_score, risk_level

    async def process_recommendation_event(self, rec_event: dict) -> None:
        incident_id = rec_event.get("incident_id")
        recommended_action = rec_event.get("recommended_action")
        root_cause_service = rec_event.get("root_cause_service")
        confidence_score = rec_event.get("success_probability", 1.0)
        recommendation_score = rec_event.get("recommendation_score", 1.0)
        namespace = rec_event.get("namespace") or "hecate-system"

        log.info(
            "decision_agent.processing_governance_for_recommendation",
            incident_id=incident_id,
            action=recommended_action,
            target=root_cause_service,
        )

        # Enforce governance check: Match Policy
        action = recommended_action
        policy_id = "pol-001"
        policy_risk_level = "low"
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    "http://localhost:8002/api/v1/policies/match",
                    params={"incident_title": root_cause_service},
                    timeout=2.0,
                )
                if res.status_code == 200:
                    data = res.json()
                    policy_id = data.get("policy_id", policy_id)
        except Exception as e:
            log.warn("decision_agent.policy_service_unreachable_using_fallback", error=str(e))

        # Query local database directly to get policy_id and its risk_level
        from .hecate_db import get_db_connection

        try:
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, risk_level FROM policies WHERE action_definition = ? AND enabled = 1",
                (action,),
            )
            row = cursor.fetchone()
            if row:
                policy_id = row[0]
                policy_risk_level = row[1]
            conn.close()
        except Exception as dbe:
            log.error("decision_agent.sqlite_policy_check_failed", error=str(dbe))

        # Calculate risk using Risk Engine
        risk_score, risk_level = self.calculate_risk(
            root_cause_service, recommendation_score, policy_risk_level
        )
        log.info(
            "decision_agent.risk_evaluation",
            service=root_cause_service,
            score=risk_score,
            level=risk_level,
        )

        if risk_level == "HIGH":
            # PAUSE execution and create an Approval Request
            approval_id = f"APR-{uuid.uuid4().hex[:8].upper()}"
            approval_reason = (
                f"High risk policy action '{action}' on target '{root_cause_service}'."
            )
            if confidence_score < 0.7:
                approval_reason += " Low recommendation confidence."

            try:
                conn, _ = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO approvals (
                        id, incident_id, incident_type, recommended_action, root_cause_service,
                        risk_level, recommendation_score, status, approval_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        approval_id,
                        incident_id,
                        rec_event.get("incident_type", "unknown"),
                        action,
                        root_cause_service,
                        risk_level,
                        recommendation_score,
                        "pending",
                        approval_reason,
                    ),
                )
                cursor.execute(
                    "UPDATE incidents SET status = 'AWAITING_APPROVAL' WHERE id = ?", (incident_id,)
                )
                conn.commit()
                conn.close()
                log.info(
                    "decision_agent.approval_created",
                    approval_id=approval_id,
                    incident_id=incident_id,
                )
            except Exception as ae:
                log.error("decision_agent.failed_to_persist_approval", error=str(ae))
                return

            # Publish approval request to approval-topic
            approval_payload = {
                "approval_id": approval_id,
                "incident_id": incident_id,
                "incident_type": rec_event.get("incident_type", "unknown"),
                "service": root_cause_service,
                "recommended_action": action,
                "risk_level": risk_level,
                "recommendation_score": recommendation_score,
                "status": "pending",
                "approval_reason": approval_reason,
                "timestamp": time.time(),
            }
            self.event_bus.publish("approval-topic", approval_payload)

        else:
            # Auto-approve (LOW/MEDIUM risk) -> transition to REMEDIATING and execute
            try:
                conn, _ = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE incidents SET status = 'REMEDIATING' WHERE id = ?", (incident_id,)
                )
                conn.commit()
                conn.close()
            except Exception as se:
                log.error("decision_agent.status_remediating_update_failed", error=str(se))

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
                "reason": f"Decision Agent auto-approved recommendation '{action}' on target '{root_cause_service}' based on policy {policy_id}",
                "timestamp": time.time(),
            }

            log.info(
                "decision_agent.remediation_decision_made",
                action=action,
                target=root_cause_service,
                risk=risk_score,
            )
            self.event_bus.publish("decision-topic", decision_payload)

    async def process_approval_event(self, approval_event: dict) -> None:
        approval_id = approval_event.get("approval_id")
        incident_id = approval_event.get("incident_id")
        status = approval_event.get("status")
        recommended_action = approval_event.get("recommended_action")
        root_cause_service = approval_event.get("service")
        risk_score = approval_event.get("recommendation_score", 1.0)

        log.info(
            "decision_agent.received_approval_resolution",
            approval_id=approval_id,
            incident_id=incident_id,
            status=status,
        )

        if status == "approved":
            # Transition status to APPROVED then REMEDIATING
            from .hecate_db import get_db_connection

            try:
                conn, _ = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE incidents SET status = 'APPROVED' WHERE id = ?", (incident_id,)
                )
                conn.commit()
                cursor.execute(
                    "UPDATE incidents SET status = 'REMEDIATING' WHERE id = ?", (incident_id,)
                )
                conn.commit()
                conn.close()
            except Exception as e:
                log.error("decision_agent.status_remediating_update_failed", error=str(e))

            decision_payload = {
                "id": str(uuid.uuid4()),
                "event_id": str(uuid.uuid4()),
                "incident_id": incident_id,
                "action": recommended_action,
                "target": root_cause_service,
                "namespace": "hecate-system",
                "confidence": 1.0,
                "risk_score": risk_score,
                "policy_id": "pol-001",
                "reason": f"Decision Agent approved action '{recommended_action}' based on human approval {approval_id}",
                "timestamp": time.time(),
            }
            self.event_bus.publish("decision-topic", decision_payload)

        elif status == "rejected":
            # Transition status to REJECTED then CLOSED
            from .hecate_db import get_db_connection

            try:
                conn, _ = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE incidents SET status = 'REJECTED' WHERE id = ?", (incident_id,)
                )
                conn.commit()
                cursor.execute(
                    "UPDATE incidents SET status = 'CLOSED' WHERE id = ?", (incident_id,)
                )
                conn.commit()
                conn.close()
            except Exception as e:
                log.error("decision_agent.status_closed_update_failed", error=str(e))

    async def stop(self) -> None:
        self._running = False
        log.info("decision_agent.stopped")

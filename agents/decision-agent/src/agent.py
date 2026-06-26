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

        # Subscribe to simulation-topic and approval-topic
        for event in self.event_bus.subscribe(
            ["simulation-topic", "approval-topic"], group_id="decision-group"
        ):
            if not self._running:
                break
            try:
                if "approval_id" in event:
                    await self.process_approval_event(event)
                else:
                    await self.process_simulation_event(event)
            except Exception as e:
                log.error("decision_agent.event_processing_failed", error=str(e))

    async def validate_execution(self, service_name: str, incident_id: str, topology_freshness: float) -> tuple[bool, str]:
        # 1. Query local database directly to check incident status
        from .hecate_db import get_db_connection
        try:
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM incidents WHERE id = ?", (incident_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                status = row[0]
                # If incident is already remediating, remediated, or closed/rejected, skip execution
                if status in ["remediated", "REMEDIATED", "CLOSED", "closed", "REMEDIATING", "remediating", "APPROVED", "approved"]:
                    return False, f"Incident already in state '{status}'"
        except Exception as e:
            log.error("decision_agent.validator.db_check_failed", error=str(e))

        # 2. Check topology freshness limit
        if topology_freshness < 0.7:
            return False, f"Topology freshness is too low ({topology_freshness:.2f})"

        # 3. Check if target service exists in virtual cluster twin
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get("http://localhost:8006/api/v1/twin/data", timeout=2.0)
                if res.status_code == 200:
                    twin_data = res.json()
                    clusters = twin_data.get("state", {}).get("clusters", {})
                    service_exists = False
                    for cls_name, cls_val in clusters.items():
                        if service_name in cls_val.get("services", {}):
                            service_exists = True
                            break
                    if not service_exists:
                        return False, f"Target service '{service_name}' not found in cluster twin topology"
                else:
                    log.warn("decision_agent.validator.twin_service_error", status=res.status_code)
        except Exception as e:
            log.error("decision_agent.validator.twin_check_failed", error=str(e))

        return True, "Validation successful"

    async def process_simulation_event(self, sim_event: dict) -> None:
        incident_id = sim_event.get("incident_id")
        root_cause_service = sim_event.get("root_cause_service")
        recommended_action = sim_event.get("recommended_action")
        namespace = sim_event.get("namespace") or "hecate-system"
        best_sim = sim_event.get("best_simulation", {})
        playbook_sequence = best_sim.get("playbook_sequence", recommended_action)
        topology_freshness = sim_event.get("topology_freshness", 1.0)

        log.info(
            "decision_agent.processing_governance_for_simulation",
            incident_id=incident_id,
            sequence=playbook_sequence,
            target=root_cause_service,
        )

        # 1. Execution Validator check
        is_valid, validation_msg = await self.validate_execution(root_cause_service, incident_id, topology_freshness)
        if not is_valid:
            log.info(
                "decision_agent.execution_validation_failed",
                incident_id=incident_id,
                reason=validation_msg
            )
            # update status to aborted in db
            from .hecate_db import get_db_connection
            try:
                conn, _ = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE incidents SET status = 'ABORTED' WHERE id = ?", (incident_id,)
                )
                conn.commit()
                conn.close()
            except Exception as e:
                log.error("decision_agent.validator.update_status_aborted_failed", error=str(e))
            return

        # 2. Gather cluster metadata for Policy Evaluation
        cluster = "cluster-aws-primary"
        replicas = 1
        traffic = "normal"
        service_type = "service"
        if "db" in root_cause_service.lower():
            service_type = "database"

        try:
            async with httpx.AsyncClient() as client:
                res = await client.get("http://localhost:8006/api/v1/twin/data", timeout=2.0)
                if res.status_code == 200:
                    twin_data = res.json()
                    state = twin_data.get("state", {})
                    if state.get("traffic_peak"):
                        traffic = "peak"
                    
                    clusters = state.get("clusters", {})
                    for cls_name, cls_val in clusters.items():
                        if root_cause_service in cls_val.get("services", {}):
                            cluster = cls_name
                            replicas = cls_val["services"][root_cause_service].get("replicas", 1)
                            break
        except Exception as e:
            log.error("decision_agent.failed_to_get_twin_metadata_for_policy", error=str(e))

        # 3. OPA-like Policy Evaluation for each action in the sequence
        actions = [act.strip() for act in playbook_sequence.split("->")]
        final_policy_effect = "approve"
        triggered_policy_id = "none"

        async with httpx.AsyncClient() as client:
            for action_name in actions:
                try:
                    payload = {
                        "action": action_name,
                        "service_name": root_cause_service,
                        "service_type": service_type,
                        "cluster": cluster,
                        "traffic": traffic,
                        "replicas": replicas
                    }
                    res = await client.post(
                        "http://localhost:8002/api/v1/policies/evaluate",
                        json=payload,
                        timeout=2.0
                    )
                    if res.status_code == 200:
                        pdata = res.json()
                        effect = pdata.get("effect", "approve")
                        pol_id = pdata.get("policy_id", "none")
                        
                        if effect == "reject":
                            final_policy_effect = "reject"
                            triggered_policy_id = pol_id
                            break
                        elif effect == "escalate":
                            final_policy_effect = "escalate"
                            triggered_policy_id = pol_id
                except Exception as pe:
                    log.error("decision_agent.policy_evaluation_failed", action=action_name, error=str(pe))

        # 4. Calculate Risk based on simulated parameters and database policy weights
        policy_risk_level = "low"
        from .hecate_db import get_db_connection
        try:
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            for action_name in actions:
                cursor.execute(
                    "SELECT risk_level FROM policies WHERE action_definition = ? AND enabled = 1",
                    (action_name,),
                )
                rows = cursor.fetchall()
                for r in rows:
                    rl = r[0].lower()
                    if rl == "high":
                        policy_risk_level = "high"
                    elif rl == "medium":
                        if policy_risk_level != "high":
                            policy_risk_level = "medium"
            conn.close()
        except Exception as dbe:
            log.error("decision_agent.sqlite_policy_check_failed", error=str(dbe))

        predicted_mttr = best_sim.get("predicted_mttr", 15.0)
        predicted_blast = best_sim.get("predicted_blast_radius", 0.1)
        predicted_cost = best_sim.get("predicted_cost", 0.0)

        # Normalize MTTR (max 50s) and Cost (max 30s)
        mttr_factor = min(1.0, predicted_mttr / 50.0)
        cost_factor = min(1.0, predicted_cost / 30.0)

        sim_risk = 0.4 * mttr_factor + 0.3 * predicted_blast + 0.3 * cost_factor
        
        policy_weight = 0.1
        if policy_risk_level.lower() == "high":
            policy_weight = 0.5
        elif policy_risk_level.lower() == "medium":
            policy_weight = 0.3

        risk_score = sim_risk + policy_weight
        risk_score = float(round(risk_score, 2))

        # Adjust risk for predictive incidents
        is_predicted = sim_event.get("is_predicted", 0)
        pred_conf = sim_event.get("prediction_confidence", 0.0)
        if is_predicted:
            discount = round(pred_conf * 0.15, 3)
            risk_score = max(0.0, risk_score - discount)
            risk_score = float(round(risk_score, 2))

        risk_level = "LOW"
        if risk_score >= 0.6:
            risk_level = "HIGH"
        elif risk_score >= 0.4:
            risk_level = "MEDIUM"

        log.info(
            "decision_agent.risk_evaluation",
            service=root_cause_service,
            score=risk_score,
            level=risk_level,
            policy_effect=final_policy_effect,
            policy_id=triggered_policy_id
        )

        # 5. Take action based on policy evaluation and risk level
        if final_policy_effect == "reject":
            # Update incident to rejected
            from .hecate_db import get_db_connection
            try:
                conn, _ = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE incidents SET status = 'REJECTED' WHERE id = ?", (incident_id,)
                )
                conn.commit()
                conn.close()
            except Exception as se:
                log.error("decision_agent.status_rejected_update_failed", error=str(se))

            decision_payload = {
                "id": str(uuid.uuid4()),
                "event_id": str(uuid.uuid4()),
                "incident_id": incident_id,
                "action": playbook_sequence,
                "target": root_cause_service,
                "namespace": namespace,
                "confidence": best_sim.get("confidence", 1.0),
                "risk_score": risk_score,
                "policy_id": triggered_policy_id,
                "status": "rejected",
                "reason": f"Decision Agent rejected plan '{playbook_sequence}' because policy '{triggered_policy_id}' returned reject",
                "timestamp": time.time(),
            }
            self.event_bus.publish("decision-topic", decision_payload)
            log.info("decision_agent.remediation_rejected_by_policy", policy_id=triggered_policy_id)
            return

        elif risk_level == "HIGH" or final_policy_effect == "escalate":
            # PAUSE execution and create an Approval Request
            approval_id = f"APR-{uuid.uuid4().hex[:8].upper()}"
            approval_reason = f"Policy effect '{final_policy_effect}' or high risk score {risk_score}."
            if final_policy_effect == "escalate":
                approval_reason = f"Declarative policy '{triggered_policy_id}' required escalation."

            from .hecate_db import get_db_connection
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
                        sim_event.get("incident_type", "unknown"),
                        playbook_sequence,
                        root_cause_service,
                        risk_level,
                        best_sim.get("score", 1.0),
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

                # Sync Approval node and GOVERNS edge to graph-service
                try:
                    httpx.post("http://localhost:8005/api/v1/graph/node", json={
                        "label": "Approval",
                        "id": approval_id,
                        "properties": {
                            "status": "pending",
                            "risk_level": risk_level,
                            "approval_reason": approval_reason,
                            "created_at": time.time()
                        }
                    }, timeout=2.0)
                    
                    httpx.post("http://localhost:8005/api/v1/graph/relationship", json={
                        "from_label": "Approval",
                        "from_key": approval_id,
                        "to_label": "Incident",
                        "to_key": incident_id,
                        "rel_type": "GOVERNS"
                    }, timeout=2.0)
                    
                    # Update Incident status node
                    httpx.post("http://localhost:8005/api/v1/graph/node", json={
                        "label": "Incident",
                        "id": incident_id,
                        "properties": {"status": "awaiting_approval"}
                    }, timeout=2.0)
                except Exception as ge:
                    log.warn("decision_agent.approval_graph_sync_failed", error=str(ge))
            except Exception as ae:
                log.error("decision_agent.failed_to_persist_approval", error=str(ae))
                return

            approval_payload = {
                "approval_id": approval_id,
                "incident_id": incident_id,
                "incident_type": sim_event.get("incident_type", "unknown"),
                "service": root_cause_service,
                "recommended_action": playbook_sequence,
                "risk_level": risk_level,
                "recommendation_score": best_sim.get("score", 1.0),
                "status": "pending",
                "approval_reason": approval_reason,
                "timestamp": time.time(),
            }
            self.event_bus.publish("approval-topic", approval_payload)

        else:
            # Auto-approve (LOW/MEDIUM risk)
            from .hecate_db import get_db_connection
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
                "action": playbook_sequence,
                "target": root_cause_service,
                "namespace": namespace,
                "confidence": best_sim.get("confidence", 1.0),
                "risk_score": risk_score,
                "policy_id": triggered_policy_id,
                "status": "approved",
                "reason": f"Decision Agent auto-approved sequence '{playbook_sequence}' on target '{root_cause_service}' based on policy {triggered_policy_id}",
                "timestamp": time.time(),
            }

            log.info(
                "decision_agent.remediation_decision_made",
                action=playbook_sequence,
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

            try:
                httpx.post("http://localhost:8005/api/v1/graph/node", json={
                    "label": "Approval",
                    "id": approval_id,
                    "properties": {
                        "status": "approved",
                        "resolved_at": time.time()
                    }
                }, timeout=2.0)
                httpx.post("http://localhost:8005/api/v1/graph/node", json={
                    "label": "Incident",
                    "id": incident_id,
                    "properties": {
                        "status": "remediating"
                    }
                }, timeout=2.0)
            except Exception as ge:
                log.warn("decision_agent.approval_resolution_graph_sync_failed", error=str(ge))

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
                "status": "approved",
                "reason": f"Decision Agent approved sequence '{recommended_action}' based on human approval {approval_id}",
                "timestamp": time.time(),
            }
            self.event_bus.publish("decision-topic", decision_payload)

        elif status == "rejected":
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

            try:
                httpx.post("http://localhost:8005/api/v1/graph/node", json={
                    "label": "Approval",
                    "id": approval_id,
                    "properties": {
                        "status": "rejected",
                        "resolved_at": time.time()
                    }
                }, timeout=2.0)
                httpx.post("http://localhost:8005/api/v1/graph/node", json={
                    "label": "Incident",
                    "id": incident_id,
                    "properties": {
                        "status": "rejected"
                    }
                }, timeout=2.0)
            except Exception as ge:
                log.warn("decision_agent.approval_resolution_graph_sync_failed", error=str(ge))

    async def stop(self) -> None:
        self._running = False
        log.info("decision_agent.stopped")

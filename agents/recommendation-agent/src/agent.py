import time
import uuid

import httpx
import structlog

from .config import Settings
from .hecate_db import get_db_connection
from .hecate_events import HecateEventBus

log = structlog.get_logger()


class RecommendationAgent:
    """HECATE Recommendation Agent — Uses historical Operational Memory to recommend optimal actions."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._running = False
        self.event_bus = HecateEventBus(kafka_servers=settings.kafka_bootstrap_servers)

    async def run(self) -> None:
        self._running = True
        log.info("recommendation_agent.started")

        # Subscribe to rca-topic and learning-topic
        for event in self.event_bus.subscribe(["rca-topic", "learning-topic"], group_id="recommendation-group"):
            if not self._running:
                break
            try:
                if event.get("event_type") == "learning.feedback":
                    await self.process_learning_feedback(event)
                else:
                    await self.process_rca_event(event)
            except Exception as e:
                log.error("recommendation_agent.processing_failed", error=str(e))

    def get_q_value(self, state_key: str, action_name: str) -> float:
        try:
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT q_value FROM playbook_q_values WHERE state_key = ? AND action_name = ?",
                (state_key, action_name)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return float(row[0])
        except Exception as e:
            log.error("recommendation_agent.get_q_value_failed", error=str(e))
        return 0.0

    def update_q_value(self, state_key: str, action_name: str, reward: float):
        alpha = 0.1
        current_q = self.get_q_value(state_key, action_name)
        new_q = current_q + alpha * (reward - current_q)
        
        try:
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO playbook_q_values (state_key, action_name, q_value) 
                VALUES (?, ?, ?)
                ON CONFLICT(state_key, action_name) DO UPDATE SET q_value = excluded.q_value
                """,
                (state_key, action_name, float(new_q))
            )
            conn.commit()
            conn.close()
            log.info("recommendation_agent.q_value_updated", state_key=state_key, action=action_name, old_q=current_q, new_q=new_q)
        except Exception as e:
            log.error("recommendation_agent.update_q_value_failed", error=str(e))

    async def process_learning_feedback(self, event: dict) -> None:
        incident_type = event.get("incident_type")
        remediation_action = event.get("remediation_action")
        effectiveness_score = event.get("effectiveness_score", 0.0)

        log.info(
            "recommendation_agent.processing_learning_feedback",
            incident_type=incident_type,
            action=remediation_action,
            reward=effectiveness_score
        )

        # Update Q-value
        self.update_q_value(incident_type, remediation_action, effectiveness_score)

    async def process_rca_event(self, rca_event: dict) -> None:
        incident_id = rca_event.get("incident_id")
        anomaly_id = rca_event.get("anomaly_id")
        rca_result = rca_event.get("rca_result", {})
        root_cause_service = rca_result.get("root_cause_service")

        # 1. Fetch incident details from database to resolve incident_type
        incident_type = "unknown"
        incident_title = "Unknown Incident"
        is_predicted = 0
        prediction_confidence = 0.0
        try:
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT title, is_predicted, prediction_confidence FROM incidents WHERE id = ?",
                (incident_id,),
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                incident_title = row[0]
                is_predicted = row[1] if row[1] is not None else 0
                prediction_confidence = row[2] if row[2] is not None else 0.0
                title_lower = incident_title.lower()
                if "cpu" in title_lower:
                    incident_type = "cpu_high"
                elif "memory" in title_lower:
                    incident_type = "memory_high"
                elif "restart" in title_lower:
                    incident_type = "restart_high"
        except Exception as dbe:
            log.error("recommendation_agent.incident_lookup_failed", error=str(dbe))

        log.info(
            "recommendation_agent.resolving_recommendation",
            incident_id=incident_id,
            root_cause=root_cause_service,
            type=incident_type,
        )

        # 2. Multi-tiered search on operational_memory & Graph Service neighbors
        match_tier = 4
        similar_cases = []
        resolved_tier = None

        try:
            conn, _ = get_db_connection()
            cursor = conn.cursor()

            # Tier 1: Exact Match (type & root cause in DB)
            cursor.execute(
                """
                SELECT remediation_action, success, recovery_time_seconds, effectiveness_score 
                FROM operational_memory 
                WHERE incident_type = ? AND root_cause_service = ?
                """,
                (incident_type, root_cause_service),
            )
            rows = cursor.fetchall()
            if rows:
                resolved_tier = 1
                similar_cases = [dict(r) for r in rows]
                log.info(
                    "recommendation_agent.similarity_match_found", tier=1, count=len(similar_cases)
                )
            conn.close()
        except Exception as e:
            log.error("recommendation_agent.db_query_failed", error=str(e))

        # Tier 2: Graph-Aware Neighbor Match / Dependency Match
        if not resolved_tier:
            try:
                res = httpx.get(
                    "http://localhost:8005/api/v1/graph/recommendations",
                    params={"service": root_cause_service, "incident_type": incident_type},
                    timeout=2.0
                )
                if res.status_code == 200:
                    neighbor_recs = res.json()
                    if neighbor_recs:
                        resolved_tier = 2
                        similar_cases = [
                            {
                                "remediation_action": r["playbook"],
                                "success": 1,
                                "recovery_time_seconds": 10,
                                "effectiveness_score": r.get("success_rate", 0.9)
                            }
                            for r in neighbor_recs
                        ]
                        log.info(
                            "recommendation_agent.similarity_match_found",
                            tier=2,
                            count=len(similar_cases)
                        )
            except Exception as ge:
                log.warn("recommendation_agent.graph_recommendations_failed", error=str(ge))

        # Tier 3: Partial Match (type only in DB)
        if not resolved_tier:
            try:
                conn, _ = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT remediation_action, success, recovery_time_seconds, effectiveness_score 
                    FROM operational_memory 
                    WHERE incident_type = ?
                    """,
                    (incident_type,),
                )
                rows = cursor.fetchall()
                if rows:
                    resolved_tier = 3
                    similar_cases = [dict(r) for r in rows]
                    log.info(
                        "recommendation_agent.similarity_match_found",
                        tier=3,
                        count=len(similar_cases),
                    )
                conn.close()
            except Exception as e:
                log.error("recommendation_agent.db_query_failed", error=str(e))

        match_tier = resolved_tier if resolved_tier else 4

        # 3. Evaluate candidate actions
        recommended_action = "restart_pod"  # Baseline default
        success_probability = 1.0
        avg_effectiveness = 1.0
        recommendation_score = 1.0
        actions_evaluated = []

        if match_tier in [1, 2] and similar_cases:
            # Group by action
            grouped = {}
            for case in similar_cases:
                act = case["remediation_action"]
                if act not in grouped:
                    grouped[act] = {"successes": 0, "total": 0, "sum_eff": 0.0}

                grouped[act]["total"] += 1
                if bool(case["success"]):
                    grouped[act]["successes"] += 1
                grouped[act]["sum_eff"] += float(case["effectiveness_score"] or 0.0)

            # Score each action
            scored_actions = []
            for act, stats in grouped.items():
                p = stats["successes"] / stats["total"]
                e = stats["sum_eff"] / stats["total"]
                q_val = self.get_q_value(incident_type, act)
                
                # Combined score: R = 0.5*P + 0.2*E + 0.3*Q
                r = round(0.5 * p + 0.2 * e + 0.3 * q_val, 4)

                scored_actions.append(
                    {
                        "action": act,
                        "success_rate": round(p, 4),
                        "avg_effectiveness": round(e, 4),
                        "score": r,
                        "count": stats["total"],
                    }
                )

            # Sort by score descending
            scored_actions.sort(key=lambda x: x["score"], reverse=True)
            actions_evaluated = scored_actions

            if scored_actions:
                best = scored_actions[0]
                recommended_action = best["action"]
                success_probability = best["success_rate"]
                avg_effectiveness = best["avg_effectiveness"]
                recommendation_score = best["score"]
        else:
            # Tier 3 Fallback: Query Policy Service match
            match_tier = 3
            try:
                async with httpx.AsyncClient() as client:
                    res = await client.get(
                        "http://localhost:8002/api/v1/policies/match",
                        params={"incident_title": root_cause_service},
                        timeout=1.5,
                    )
                    if res.status_code == 200:
                        policy_match = res.json()
                        recommended_action = policy_match.get("action", recommended_action)
                        log.info(
                            "recommendation_agent.policy_fallback_success",
                            action=recommended_action,
                        )
            except Exception as pe:
                log.warn(
                    "recommendation_agent.policy_service_unreachable_using_hardcoded_defaults",
                    error=str(pe),
                )
                try:
                    conn, _ = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT action_definition FROM policies WHERE enabled = 1")
                    p_rows = cursor.fetchall()
                    conn.close()
                    for p in p_rows:
                        if "cpu" in p[0] and "cpu" in incident_type:
                            recommended_action = p[0]
                except Exception:
                    pass

            q_val = self.get_q_value(incident_type, recommended_action)
            recommendation_score = round(0.7 * 1.0 + 0.3 * q_val, 4)
            actions_evaluated = [
                {
                    "action": recommended_action,
                    "success_rate": 1.0,
                    "avg_effectiveness": 1.0,
                    "score": recommendation_score,
                    "count": 0,
                }
            ]

        log.info(
            "recommendation_agent.recommendation_decided",
            action=recommended_action,
            score=recommendation_score,
            tier=match_tier,
            cases=len(similar_cases),
        )

        # 4. Persist recommendation record in database
        try:
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            rec_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT OR REPLACE INTO recommendations (
                    id, incident_id, incident_type, root_cause_service, recommended_action, 
                    success_probability, avg_effectiveness, recommendation_score, match_tier, 
                    similar_cases_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rec_id,
                    incident_id,
                    incident_type,
                    root_cause_service,
                    recommended_action,
                    success_probability,
                    avg_effectiveness,
                    recommendation_score,
                    match_tier,
                    len(similar_cases),
                ),
            )
            conn.commit()
            conn.close()
            log.info("recommendation_agent.persisted_to_db", incident_id=incident_id)

            # Sync Recommendation, Playbook, and edges to graph-service
            try:
                httpx.post("http://localhost:8005/api/v1/graph/node", json={
                    "label": "Recommendation",
                    "id": rec_id,
                    "properties": {
                        "action": recommended_action,
                        "score": recommendation_score,
                        "match_tier": match_tier,
                        "created_at": time.time()
                    }
                }, timeout=2.0)
                
                httpx.post("http://localhost:8005/api/v1/graph/relationship", json={
                    "from_label": "Recommendation",
                    "from_key": rec_id,
                    "to_label": "Incident",
                    "to_key": incident_id,
                    "rel_type": "RECOMMENDED_FOR"
                }, timeout=2.0)
                
                httpx.post("http://localhost:8005/api/v1/graph/node", json={
                    "label": "Playbook",
                    "id": recommended_action,
                    "properties": {
                        "name": recommended_action
                    }
                }, timeout=2.0)
                
                httpx.post("http://localhost:8005/api/v1/graph/relationship", json={
                    "from_label": "Playbook",
                    "from_key": recommended_action,
                    "to_label": "Service",
                    "to_key": root_cause_service,
                    "rel_type": "EXECUTED_ON"
                }, timeout=2.0)
            except Exception as ge:
                log.warn("recommendation_agent.graph_sync_failed", error=str(ge))
        except Exception as dbe:
            log.error("recommendation_agent.persisting_failed", error=str(dbe))

        # 5. Publish event to recommendation-topic
        rec_payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "recommendation.made",
            "schema_version": "1.0.0",
            "incident_id": incident_id,
            "anomaly_id": anomaly_id,
            "incident_type": incident_type,
            "incident_title": incident_title,
            "root_cause_service": root_cause_service,
            "recommended_action": recommended_action,
            "success_probability": success_probability,
            "avg_effectiveness": avg_effectiveness,
            "recommendation_score": recommendation_score,
            "match_tier": match_tier,
            "is_predicted": is_predicted,
            "prediction_confidence": prediction_confidence,
            "evidence": {
                "similar_incidents_count": len(similar_cases),
                "actions_evaluated": actions_evaluated,
            },
            "timestamp": time.time(),
        }
        self.event_bus.publish("recommendation-topic", rec_payload)

    async def stop(self) -> None:
        self._running = False
        log.info("recommendation_agent.stopped")

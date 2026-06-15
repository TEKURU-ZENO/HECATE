import os
import time
import uuid
import httpx
import structlog
from datetime import datetime

from .config import Settings
from .hecate_events import HecateEventBus
from .hecate_db import get_db_connection

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

        # Subscribe to rca-topic
        for rca_event in self.event_bus.subscribe(["rca-topic"], group_id="recommendation-group"):
            if not self._running:
                break
            try:
                await self.process_rca_event(rca_event)
            except Exception as e:
                log.error("recommendation_agent.rca_processing_failed", error=str(e))

    async def process_rca_event(self, rca_event: dict) -> None:
        incident_id = rca_event.get("incident_id")
        anomaly_id = rca_event.get("anomaly_id")
        rca_result = rca_event.get("rca_result", {})
        root_cause_service = rca_result.get("root_cause_service")
        
        # 1. Fetch incident details from database to resolve incident_type
        incident_type = "unknown"
        incident_title = "Unknown Incident"
        try:
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT title FROM incidents WHERE id = ?", (incident_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                incident_title = row[0]
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
            type=incident_type
        )

        # 2. Multi-tiered search on operational_memory
        match_tier = 3
        similar_cases = []

        try:
            conn, _ = get_db_connection()
            cursor = conn.cursor()

            # Tier 1: Exact Match (type & root cause)
            cursor.execute(
                """
                SELECT remediation_action, success, recovery_time_seconds, effectiveness_score 
                FROM operational_memory 
                WHERE incident_type = ? AND root_cause_service = ?
                """,
                (incident_type, root_cause_service)
            )
            rows = cursor.fetchall()
            if rows:
                match_tier = 1
                similar_cases = [dict(r) for r in rows]
                log.info("recommendation_agent.similarity_match_found", tier=1, count=len(similar_cases))
            else:
                # Tier 2: Partial Match (type only)
                cursor.execute(
                    """
                    SELECT remediation_action, success, recovery_time_seconds, effectiveness_score 
                    FROM operational_memory 
                    WHERE incident_type = ?
                    """,
                    (incident_type,)
                )
                rows = cursor.fetchall()
                if rows:
                    match_tier = 2
                    similar_cases = [dict(r) for r in rows]
                    log.info("recommendation_agent.similarity_match_found", tier=2, count=len(similar_cases))
            
            conn.close()
        except Exception as e:
            log.error("recommendation_agent.db_query_failed", error=str(e))

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
                # Weighted score formula: R = 0.7*P + 0.3*E
                r = round(0.7 * p + 0.3 * e, 4)
                
                scored_actions.append({
                    "action": act,
                    "success_rate": round(p, 4),
                    "avg_effectiveness": round(e, 4),
                    "score": r,
                    "count": stats["total"]
                })

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
                        timeout=1.5
                    )
                    if res.status_code == 200:
                        policy_match = res.json()
                        recommended_action = policy_match.get("action", recommended_action)
                        log.info("recommendation_agent.policy_fallback_success", action=recommended_action)
            except Exception as pe:
                log.warn("recommendation_agent.policy_service_unreachable_using_hardcoded_defaults", error=str(pe))
                # Fallback to sqlite policies directly
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

            actions_evaluated = [{
                "action": recommended_action,
                "success_rate": 1.0,
                "avg_effectiveness": 1.0,
                "score": 1.0,
                "count": 0
            }]

        log.info(
            "recommendation_agent.recommendation_decided",
            action=recommended_action,
            score=recommendation_score,
            tier=match_tier,
            cases=len(similar_cases)
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
                    rec_id, incident_id, incident_type, root_cause_service, recommended_action,
                    success_probability, avg_effectiveness, recommendation_score, match_tier,
                    len(similar_cases)
                )
            )
            conn.commit()
            conn.close()
            log.info("recommendation_agent.persisted_to_db", incident_id=incident_id)
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
            "evidence": {
                "similar_incidents_count": len(similar_cases),
                "actions_evaluated": actions_evaluated
            },
            "timestamp": time.time()
        }
        self.event_bus.publish("recommendation-topic", rec_payload)

    async def stop(self) -> None:
        self._running = False
        log.info("recommendation_agent.stopped")

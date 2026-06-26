import time
import uuid
import httpx
import structlog

from .hecate_events import HecateEventBus

log = structlog.get_logger()


class SimulationAgent:
    def __init__(self, settings) -> None:
        self.settings = settings
        self._running = False
        self.event_bus = HecateEventBus(kafka_servers=settings.kafka_bootstrap_servers)

    async def run(self) -> None:
        self._running = True
        log.info("simulation_agent.started")

        # Subscribe to recommendation-topic
        for rec_event in self.event_bus.subscribe(["recommendation-topic"], group_id="simulation-group"):
            if not self._running:
                break
            try:
                await self.process_recommendation_event(rec_event)
            except Exception as e:
                log.error("simulation_agent.processing_failed", error=str(e))

    async def process_recommendation_event(self, rec_event: dict) -> None:
        incident_id = rec_event.get("incident_id")
        root_cause_service = rec_event.get("root_cause_service")
        incident_type = rec_event.get("incident_type")
        recommended_action = rec_event.get("recommended_action")

        log.info(
            "simulation_agent.querying_twin_simulation",
            incident_id=incident_id,
            service=root_cause_service,
            type=incident_type
        )

        # Call digital twin service to simulate actions
        metrics = {"cpu_usage": 95.0, "memory_usage": 90.0}

        simulations = []
        confidence = 0.95
        telemetry_completeness = 1.0
        topology_freshness = 1.0
        calibration_accuracy = 0.95

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    self.settings.digital_twin_service_url,
                    json={
                        "service": root_cause_service,
                        "incident_id": incident_id,
                        "incident_type": incident_type,
                        "metrics": metrics
                    },
                    timeout=5.0
                )
                if res.status_code == 200:
                    data = res.json()
                    simulations = data.get("simulations", [])
                    confidence = data.get("confidence", confidence)
                    telemetry_completeness = data.get("telemetry_completeness", telemetry_completeness)
                    topology_freshness = data.get("topology_freshness", topology_freshness)
                    calibration_accuracy = data.get("calibration_accuracy", calibration_accuracy)
                    log.info("simulation_agent.twin_simulation_response_received", simulations_count=len(simulations))
                else:
                    log.error("simulation_agent.twin_service_returned_error", status=res.status_code)
        except Exception as e:
            log.error("simulation_agent.twin_service_query_failed_using_mock_fallback", error=str(e))

        # If digital twin service call failed or returned empty simulations, build mock defaults
        if not simulations:
            playbook_specs = {
                "restart_pod": (0.75, 12.0, 0.0, 0.1),
                "scale_deployment": (0.90, 15.0, 10.0, 0.0),
                "migrate_service": (0.60, 25.0, 5.0, 0.4),
                "rollback_release": (0.85, 18.0, 0.0, 0.2)
            }
            candidates = [
                ["restart_pod"],
                ["scale_deployment"],
                ["migrate_service"],
                ["rollback_release"],
                ["scale_deployment", "restart_pod"],
                ["restart_pod", "scale_deployment"],
                ["migrate_service", "restart_pod"],
                ["rollback_release", "scale_deployment"]
            ]
            confidence = calibration_accuracy * telemetry_completeness * topology_freshness
            for seq in candidates:
                p_success = 0.0
                projected_mttr = 0.0
                projected_cost = 0.0
                projected_blast = 0.0
                
                for i, act in enumerate(seq):
                    spec = playbook_specs[act]
                    act_p, act_mttr, act_cost, act_blast = spec
                    if i == 0:
                        p_success = act_p
                        projected_mttr = act_mttr
                        projected_cost = act_cost
                        projected_blast = act_blast
                    else:
                        prev_fail = 1.0 - p_success
                        p_success = p_success + prev_fail * act_p
                        projected_mttr = projected_mttr + prev_fail * act_mttr
                        projected_cost = projected_cost + act_cost
                        projected_blast = max(projected_blast, act_blast)
                
                outage_factor = max(0.0, min(1.0, projected_mttr / 50.0))
                cost_factor = max(0.0, min(1.0, projected_cost / 30.0))
                
                score = (
                    0.35 * p_success +
                    0.20 * (1.0 - outage_factor) +
                    0.15 * (1.0 - cost_factor) -
                    0.10 * projected_blast +
                    0.20 * confidence
                )
                simulations.append({
                    "playbook_sequence": " -> ".join(seq),
                    "predicted_mttr": float(round(projected_mttr, 2)),
                    "predicted_cost": float(round(projected_cost, 2)),
                    "predicted_blast_radius": float(round(projected_blast, 2)),
                    "success_probability": float(round(p_success, 2)),
                    "confidence": float(round(confidence, 2)),
                    "score": float(round(score, 3))
                })
            simulations.sort(key=lambda x: x["score"], reverse=True)

        best_sim = simulations[0] if simulations else {}

        simulation_payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "simulation.completed",
            "schema_version": "1.0.0",
            "incident_id": incident_id,
            "anomaly_id": rec_event.get("anomaly_id"),
            "incident_type": incident_type,
            "incident_title": rec_event.get("incident_title"),
            "root_cause_service": root_cause_service,
            "recommended_action": recommended_action,
            "success_probability": rec_event.get("success_probability", 1.0),
            "avg_effectiveness": rec_event.get("avg_effectiveness", 1.0),
            "recommendation_score": rec_event.get("recommendation_score", 1.0),
            "match_tier": rec_event.get("match_tier"),
            "is_predicted": rec_event.get("is_predicted", 0),
            "prediction_confidence": rec_event.get("prediction_confidence", 0.0),
            "simulations": simulations,
            "best_simulation": best_sim,
            "confidence": confidence,
            "telemetry_completeness": telemetry_completeness,
            "topology_freshness": topology_freshness,
            "calibration_accuracy": calibration_accuracy,
            "timestamp": time.time(),
        }

        log.info(
            "simulation_agent.publishing_simulation_completed",
            incident_id=incident_id,
            best_sequence=best_sim.get("playbook_sequence"),
            best_score=best_sim.get("score")
        )

        self.event_bus.publish("simulation-topic", simulation_payload)

    async def stop(self) -> None:
        self._running = False
        log.info("simulation_agent.stopped")

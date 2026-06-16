import os
import time
import uuid

import structlog
import yaml

from .hecate_events import HecateEventBus

log = structlog.get_logger()


class DetectionAgent:
    def __init__(self, settings) -> None:
        self.settings = settings
        self._running = False
        self.event_bus = HecateEventBus(kafka_servers=settings.kafka_bootstrap_servers)
        self.rules = self._load_rules()
        self.ml_model = None
        self._load_ml_model()

    def _load_ml_model(self):
        try:
            import joblib

            ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            model_path = os.path.join(ROOT_DIR, "ml", "models", "isolation_forest.pkl")
            if os.path.exists(model_path):
                self.ml_model = joblib.load(model_path)
                log.info("detection_agent.ml_model_loaded", path=model_path)
            else:
                log.warn("detection_agent.ml_model_not_found_using_rules_only", path=model_path)
        except Exception as e:
            log.error("detection_agent.ml_model_load_failed", error=str(e))

    def _load_rules(self) -> dict:
        ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        rules_path = os.path.join(ROOT_DIR, "policies", "default-rules.yaml")
        if os.path.exists(rules_path):
            try:
                with open(rules_path, "r") as f:
                    data = yaml.safe_load(f)
                log.info("detection_agent.rules_loaded", path=rules_path, rules=data.get("rules"))
                return data.get("rules", {})
            except Exception as e:
                log.error("detection_agent.rules_load_failed", error=str(e))

        # Safe fallback
        log.warn("detection_agent.using_fallback_rules")
        return {
            "cpu_high": {"metric": "cpu_usage", "threshold": 90},
            "memory_high": {"metric": "memory_usage", "threshold": 85},
            "restart_high": {"metric": "restart_count", "threshold": 5},
        }

    async def run(self) -> None:
        self._running = True
        log.info("detection_agent.started")

        # Subscribe to metrics-topic
        for event in self.event_bus.subscribe(["metrics-topic"], group_id="detection-group"):
            if not self._running:
                break
            try:
                await self.process_metrics_event(event)
            except Exception as e:
                log.error("detection_agent.process_failed", error=str(e))

    async def process_metrics_event(self, event: dict) -> None:
        metrics = event.get("metrics", {})
        service_name = event.get("service_name")
        namespace = event.get("namespace")

        # 1. Rule-Based Threshold Evaluation
        for rule_name, rule in self.rules.items():
            metric_name = rule.get("metric")
            threshold = rule.get("threshold")
            current_value = metrics.get(metric_name, 0.0)

            if current_value > threshold:
                anomaly_id = str(uuid.uuid4())
                anomaly_payload = {
                    "id": anomaly_id,
                    "event_id": str(uuid.uuid4()),
                    "anomaly_type": rule_name,
                    "metric_name": metric_name,
                    "current_value": current_value,
                    "threshold_value": threshold,
                    "service_name": service_name,
                    "namespace": namespace,
                    "timestamp": time.time(),
                    "triggered_by_event": event.get("event_id"),
                }
                log.info(
                    "detection_agent.rule_anomaly_detected",
                    anomaly_type=rule_name,
                    value=current_value,
                )
                self.event_bus.publish("anomaly-topic", anomaly_payload)

        # 2. Machine Learning Unsupervised Isolation Forest Evaluation
        if self.ml_model is not None:
            try:
                import numpy as np

                cpu = float(metrics.get("cpu_usage", 0.0))
                mem = float(metrics.get("memory_usage", 0.0))
                restarts = float(metrics.get("restart_count", 0.0))

                prediction = self.ml_model.predict(np.array([[cpu, mem, restarts]]))[0]
                if prediction == -1:
                    anomaly_id = str(uuid.uuid4())
                    anomaly_payload = {
                        "id": anomaly_id,
                        "event_id": str(uuid.uuid4()),
                        "anomaly_type": "ml_isolation_forest",
                        "metric_name": "multi_dimensional_features",
                        "current_value": f"cpu={cpu},mem={mem},restarts={restarts}",
                        "threshold_value": 0.0,  # anomaly score boundary
                        "service_name": service_name,
                        "namespace": namespace,
                        "timestamp": time.time(),
                        "triggered_by_event": event.get("event_id"),
                    }
                    log.info(
                        "detection_agent.ml_anomaly_detected", cpu=cpu, mem=mem, restarts=restarts
                    )
                    self.event_bus.publish("anomaly-topic", anomaly_payload)
            except Exception as ex:
                log.error("detection_agent.ml_inference_failed", error=str(ex))

    async def stop(self) -> None:
        self._running = False
        log.info("detection_agent.stopped")

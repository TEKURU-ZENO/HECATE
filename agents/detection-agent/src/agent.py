import asyncio
import structlog
import uuid
import time
import os
import yaml
from .config import settings
from .hecate_events import HecateEventBus

log = structlog.get_logger()

class DetectionAgent:
    def __init__(self, settings) -> None:
        self.settings = settings
        self._running = False
        self.event_bus = HecateEventBus(kafka_servers=settings.kafka_bootstrap_servers)
        self.rules = self._load_rules()
        
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
            "restart_high": {"metric": "restart_count", "threshold": 5}
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
                    "triggered_by_event": event.get("event_id")
                }
                log.info("detection_agent.anomaly_detected", anomaly_type=rule_name, value=current_value)
                self.event_bus.publish("anomaly-topic", anomaly_payload)

    async def stop(self) -> None:
        self._running = False
        log.info("detection_agent.stopped")
import time
import uuid
from collections import defaultdict

import httpx
import structlog

from .hecate_events import HecateEventBus

log = structlog.get_logger()


class PredictionAgent:
    def __init__(self, settings) -> None:
        self.settings = settings
        self._running = False
        self.event_bus = HecateEventBus(kafka_servers=settings.kafka_bootstrap_servers)

        # rolling buffers for each service and metric: self.buffers[service][metric] = list of values
        self.buffers = defaultdict(lambda: defaultdict(list))

        # rate limiter to prevent flooding: self.last_triggered[(service, metric)] = timestamp
        self.last_triggered = {}

    async def run(self) -> None:
        self._running = True
        log.info("prediction_agent.started")

        # Subscribe to metrics-topic
        for event in self.event_bus.subscribe(["metrics-topic"], group_id="prediction-group"):
            if not self._running:
                break
            try:
                await self.process_metrics_event(event)
            except Exception as e:
                log.error("prediction_agent.event_processing_failed", error=str(e))

    async def process_metrics_event(self, event: dict) -> None:
        service_name = event.get("service_name")
        namespace = event.get("namespace") or "hecate-system"
        metrics = event.get("metrics", {})

        if not service_name:
            return

        # Check cpu_usage and memory_usage
        for metric_name in ["cpu_usage", "memory_usage"]:
            if metric_name not in metrics:
                continue

            val = float(metrics[metric_name])
            buffer = self.buffers[service_name][metric_name]
            buffer.append(val)

            # keep sliding window of size 15
            if len(buffer) > 15:
                buffer.pop(0)

            if len(buffer) >= 15:
                # Call forecasting service
                await self.evaluate_forecast(service_name, namespace, metric_name, buffer, val)

    async def evaluate_forecast(
        self,
        service_name: str,
        namespace: str,
        metric_name: str,
        values: list[float],
        current_value: float,
    ) -> None:
        # Check if rate-limited (cooldown of 60 seconds)
        key = (service_name, metric_name)
        now = time.time()
        if key in self.last_triggered:
            if now - self.last_triggered[key] < 60.0:
                return

        # Call forecasting-service
        try:
            payload = {"service": service_name, "metric": metric_name, "values": values}
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    self.settings.forecasting_service_url, json=payload, timeout=2.0
                )

                if res.status_code == 200:
                    data = res.json()
                    predicted_value = data.get("predicted_value", 0.0)
                    lower_bound = data.get("lower_bound", 0.0)
                    upper_bound = data.get("upper_bound", 0.0)
                    confidence = data.get("confidence", 0.0)
                    lead_time_seconds = data.get("lead_time_seconds", 0)

                    log.info(
                        "prediction_agent.forecast_received",
                        service=service_name,
                        metric=metric_name,
                        predicted=predicted_value,
                        lower_bound=lower_bound,
                        upper_bound=upper_bound,
                        confidence=confidence,
                        lead_time=lead_time_seconds,
                    )

                    # Trigger a predicted anomaly if breach is predicted and confidence is >= 0.5
                    if lead_time_seconds > 0 and confidence >= 0.5:
                        self.last_triggered[key] = now
                        anomaly_id = f"PRD-ANM-{uuid.uuid4().hex[:6].upper()}"

                        anomaly_payload = {
                            "id": anomaly_id,
                            "event_id": str(uuid.uuid4()),
                            "anomaly_type": "cpu_high" if "cpu" in metric_name else "memory_high",
                            "metric_name": metric_name,
                            "current_value": current_value,
                            "threshold_value": 90.0 if "cpu" in metric_name else 85.0,
                            "service_name": service_name,
                            "namespace": namespace,
                            "timestamp": now,
                            "predicted": True,
                            "confidence": confidence,
                            "model": "capacity_forecast",
                            "lead_time_seconds": lead_time_seconds,
                        }

                        log.warn(
                            "prediction_agent.proactive_breach_predicted",
                            service=service_name,
                            metric=metric_name,
                            lead_time=lead_time_seconds,
                            confidence=confidence,
                        )

                        self.event_bus.publish("anomaly-topic", anomaly_payload)
        except Exception as e:
            log.error(
                "prediction_agent.forecasting_service_call_failed",
                service=service_name,
                metric=metric_name,
                error=str(e),
            )

    async def stop(self) -> None:
        self._running = False
        log.info("prediction_agent.stopped")

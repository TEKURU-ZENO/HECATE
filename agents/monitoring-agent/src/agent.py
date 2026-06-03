import asyncio
import structlog
import uuid
import time
import os
import json
from .config import settings
from .hecate_events import HecateEventBus

log = structlog.get_logger()

class MonitoringAgent:
    def __init__(self, settings) -> None:
        self.settings = settings
        self._running = False
        self.event_bus = HecateEventBus(kafka_servers=settings.kafka_bootstrap_servers)
        
    async def run(self) -> None:
        self._running = True
        log.info("monitoring_agent.running", target_service=self.settings.target_service)
        
        # Simulation cycle counter
        cycle = 0
        
        while self._running:
            try:
                cycle += 1
                metrics = await self.scrape_metrics(cycle)
                
                # Publish raw metric event
                event_payload = {
                    "event_id": str(uuid.uuid4()),
                    "event_type": "telemetry.metric",
                    "timestamp": time.time(),
                    "service_name": self.settings.target_service,
                    "namespace": self.settings.target_namespace,
                    "metrics": metrics
                }
                
                self.event_bus.publish("metrics-topic", event_payload)
            except Exception as e:
                log.error("monitoring_agent.cycle_failed", error=str(e))
                
            await asyncio.sleep(self.settings.scrape_interval_seconds)

    async def stop(self) -> None:
        self._running = False
        log.info("monitoring_agent.stopped")

    async def scrape_metrics(self, cycle: int) -> dict:
        # Check for user-driven simulation triggers in the workspace root
        sim_trigger_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "simulation_trigger.json"))
        cpu = 45.0
        memory = 60.0
        restarts = 0
        
        if os.path.exists(sim_trigger_path):
            try:
                with open(sim_trigger_path, "r") as f:
                    trigger = json.load(f)
                cpu = trigger.get("cpu_usage", cpu)
                memory = trigger.get("memory_usage", memory)
                restarts = trigger.get("restart_count", restarts)
                log.info("monitoring_agent.simulation_trigger_detected", cpu=cpu, memory=memory, restarts=restarts)
            except Exception as e:
                log.error("monitoring_agent.simulation_trigger_read_failed", error=str(e))
        else:
            # Automatic scenario simulation if no file trigger exists
            # Scenario 1: CPU spike every 15 cycles
            if cycle % 15 == 0:
                cpu = 95.0
                log.info("monitoring_agent.simulating_cpu_spike")
            # Scenario 2: Memory OOM and Restarts every 20 cycles
            elif cycle % 20 == 0:
                memory = 88.0
                restarts = 6
                log.info("monitoring_agent.simulating_oom_crash")
                
        return {
            "cpu_usage": cpu,
            "memory_usage": memory,
            "restart_count": restarts
        }
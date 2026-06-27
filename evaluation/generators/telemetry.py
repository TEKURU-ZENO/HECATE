import numpy as np
from typing import Dict, List, Any

class SyntheticTelemetryGenerator:
    def __init__(self, seed: int = 42, noise_level: float = 0.10):
        self.seed = seed
        self.noise_level = noise_level
        self.rng = np.random.default_rng(seed)
        self.services = ["gateway", "order-service", "payment-service", "payment-db", "payment-cache"]

    def generate_baseline(self, length: int = 100) -> Dict[str, Dict[str, np.ndarray]]:
        """Generates standard, healthy baseline telemetry with Gaussian noise."""
        telemetry = {}
        for svc in self.services:
            telemetry[svc] = {
                "cpu": np.clip(self.rng.normal(30.0, 5.0, length), 0, 100),
                "memory": np.clip(self.rng.normal(50.0, 3.0, length) + np.arange(length) * 0.05, 0, 100), # slight trend
                "restarts": np.zeros(length),
                "latency_ms": np.clip(self.rng.normal(20.0, 2.0, length), 5, 200),
                "error_rate": np.clip(self.rng.normal(0.01, 0.002, length), 0, 1.0)
            }
        return telemetry

    def inject_cpu_spike(self, telemetry: Dict[str, Dict[str, np.ndarray]], service: str, start_idx: int = 50) -> None:
        length = len(telemetry[service]["cpu"])
        for i in range(start_idx, length):
            # Sigmoid/Ramp increase in CPU
            multiplier = 1.0 / (1.0 + np.exp(-(i - start_idx - 5) / 2))
            telemetry[service]["cpu"][i] = np.clip(
                telemetry[service]["cpu"][i] + multiplier * 60.0 + self.rng.normal(0, 2.0), 0, 100
            )
            # Latency spikes along with CPU
            telemetry[service]["latency_ms"][i] = telemetry[service]["latency_ms"][i] * (1.0 + multiplier * 4.0)
            # Gateway latency propagates
            if service in ["order-service", "payment-service"]:
                telemetry["gateway"]["latency_ms"][i] = telemetry["gateway"]["latency_ms"][i] * (1.0 + multiplier * 2.0)

    def inject_memory_leak(self, telemetry: Dict[str, Dict[str, np.ndarray]], service: str, start_idx: int = 40) -> None:
        length = len(telemetry[service]["memory"])
        for i in range(start_idx, length):
            leak = (i - start_idx) * 1.5
            telemetry[service]["memory"][i] = np.clip(
                telemetry[service]["memory"][i] + leak, 0, 100
            )
            if telemetry[service]["memory"][i] > 95.0 and i % 15 == 0:
                telemetry[service]["restarts"][i] += 1
                # Drop memory on crash restart
                telemetry[service]["memory"][i] = 40.0

    def inject_traffic_surge(self, telemetry: Dict[str, Dict[str, np.ndarray]], start_idx: int = 30) -> None:
        length = len(telemetry["gateway"]["cpu"])
        for svc in self.services:
            for i in range(start_idx, length):
                surge = 25.0 * np.sin((i - start_idx) / 10.0)
                telemetry[svc]["cpu"][i] = np.clip(telemetry[svc]["cpu"][i] + max(0.0, surge), 0, 100)
                telemetry[svc]["latency_ms"][i] = np.clip(telemetry[svc]["latency_ms"][i] * (1.0 + max(0.0, surge) / 50.0), 5, 500)

from evaluation.scenarios import Scenario
from evaluation.core.registry import EvaluationRegistry
from evaluation.core.context import EvaluationContext
from evaluation.generators.telemetry import SyntheticTelemetryGenerator
import numpy as np

@EvaluationRegistry.register_scenario("dns_failure")
class DNSFailureScenario(Scenario):
    def __init__(self):
        super().__init__(name="DNS Failure", tags=["chaos", "rca", "governance"])

    def run(self, context: EvaluationContext) -> None:
        generator = SyntheticTelemetryGenerator(seed=context.experiment.seed)
        telemetry = generator.generate_baseline()
        # In dns failure, latency spike and high error rate starting at 50
        service = "payment-db"
        length = len(telemetry[service]["latency_ms"])
        for i in range(50, length):
            telemetry[service]["latency_ms"][i] = 2000.0 + generator.rng.normal(0.0, 50.0)
            telemetry[service]["error_rate"][i] = 0.95 + generator.rng.normal(0.0, 0.02)
            # Propagates downstream to order-service
            telemetry["order-service"]["latency_ms"][i] = 1500.0 + generator.rng.normal(0.0, 50.0)
            telemetry["order-service"]["error_rate"][i] = 0.70 + generator.rng.normal(0.0, 0.05)
            
        context.telemetry = telemetry
        context.services = generator.services
        context.ground_truth["target_service"] = "payment-db"

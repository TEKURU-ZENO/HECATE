from evaluation.scenarios import Scenario
from evaluation.core.registry import EvaluationRegistry
from evaluation.core.context import EvaluationContext
from evaluation.generators.telemetry import SyntheticTelemetryGenerator

@EvaluationRegistry.register_scenario("api_timeout")
class APITimeoutScenario(Scenario):
    def __init__(self):
        super().__init__(name="API Timeout", tags=["chaos", "governance"])

    def run(self, context: EvaluationContext) -> None:
        generator = SyntheticTelemetryGenerator(seed=context.experiment.seed)
        telemetry = generator.generate_baseline()
        service = "order-service"
        length = len(telemetry[service]["latency_ms"])
        for i in range(40, length):
            telemetry[service]["latency_ms"][i] = 5000.0 # 5s timeout
            telemetry[service]["error_rate"][i] = 0.80 + generator.rng.normal(0.0, 0.02)
            
        context.telemetry = telemetry
        context.services = generator.services
        context.ground_truth["target_service"] = "order-service"

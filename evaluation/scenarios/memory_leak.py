from evaluation.scenarios import Scenario
from evaluation.core.registry import EvaluationRegistry
from evaluation.core.context import EvaluationContext
from evaluation.generators.telemetry import SyntheticTelemetryGenerator

@EvaluationRegistry.register_scenario("memory_leak")
class MemoryLeakScenario(Scenario):
    def __init__(self):
        super().__init__(name="Memory Leak", tags=["prediction", "remediation", "chaos"])

    def run(self, context: EvaluationContext) -> None:
        generator = SyntheticTelemetryGenerator(seed=context.experiment.seed)
        telemetry = generator.generate_baseline()
        generator.inject_memory_leak(telemetry, "payment-service", start_idx=35)
        context.telemetry = telemetry
        context.services = generator.services
        context.ground_truth["target_service"] = "payment-service"

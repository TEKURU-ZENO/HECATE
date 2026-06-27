from evaluation.scenarios import Scenario
from evaluation.core.registry import EvaluationRegistry
from evaluation.core.context import EvaluationContext
from evaluation.generators.telemetry import SyntheticTelemetryGenerator

@EvaluationRegistry.register_scenario("cpu_spike")
class CPUSpikeScenario(Scenario):
    def __init__(self):
        super().__init__(name="CPU Spike", tags=["prediction", "recommendation", "chaos"])

    def run(self, context: EvaluationContext) -> None:
        generator = SyntheticTelemetryGenerator(seed=context.experiment.seed)
        # Generate baseline
        telemetry = generator.generate_baseline()
        # Inject CPU spike on payment-service
        generator.inject_cpu_spike(telemetry, "payment-service", start_idx=45)
        context.telemetry = telemetry
        context.services = generator.services
        # Set ground truth target service
        context.ground_truth["target_service"] = "payment-service"

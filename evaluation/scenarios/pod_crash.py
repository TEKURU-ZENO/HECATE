from evaluation.scenarios import Scenario
from evaluation.core.registry import EvaluationRegistry
from evaluation.core.context import EvaluationContext
from evaluation.generators.telemetry import SyntheticTelemetryGenerator

@EvaluationRegistry.register_scenario("pod_crash")
class PodCrashScenario(Scenario):
    def __init__(self):
        super().__init__(name="Pod Crash", tags=["chaos", "remediation", "reliability"])

    def run(self, context: EvaluationContext) -> None:
        generator = SyntheticTelemetryGenerator(seed=context.experiment.seed)
        telemetry = generator.generate_baseline()
        service = "payment-service"
        # Immediate crash at 50, restarts incremented
        telemetry[service]["restarts"][50] = 1
        # Set telemetry metrics to abnormal levels briefly
        telemetry[service]["cpu"][50] = 0.0
        telemetry[service]["latency_ms"][50] = 500.0
        telemetry[service]["error_rate"][50] = 1.0
        
        context.telemetry = telemetry
        context.services = generator.services
        context.ground_truth["target_service"] = "payment-service"

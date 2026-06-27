from evaluation.scenarios import Scenario
from evaluation.core.registry import EvaluationRegistry
from evaluation.core.context import EvaluationContext
from evaluation.generators.telemetry import SyntheticTelemetryGenerator

@EvaluationRegistry.register_scenario("kafka_outage")
class KafkaOutageScenario(Scenario):
    def __init__(self):
        super().__init__(name="Kafka Outage", tags=["chaos", "prediction", "rca"])

    def run(self, context: EvaluationContext) -> None:
        generator = SyntheticTelemetryGenerator(seed=context.experiment.seed)
        telemetry = generator.generate_baseline()
        service = "gateway"
        length = len(telemetry[service]["latency_ms"])
        for i in range(45, length):
            telemetry[service]["latency_ms"][i] = telemetry[service]["latency_ms"][i] * 3.5
            telemetry[service]["error_rate"][i] = 0.40 + generator.rng.normal(0.0, 0.05)
            
        context.telemetry = telemetry
        context.services = generator.services
        context.ground_truth["target_service"] = "gateway"

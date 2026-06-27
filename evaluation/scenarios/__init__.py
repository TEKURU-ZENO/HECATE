from typing import List
from evaluation.core.context import EvaluationContext

class Scenario:
    def __init__(self, name: str, tags: List[str]):
        self.name = name
        self.tags = tags

    def run(self, context: EvaluationContext) -> None:
        raise NotImplementedError("Scenarios must implement the run() method.")

# Import scenario modules to trigger registry decorators
from evaluation.scenarios.cpu_spike import CPUSpikeScenario
from evaluation.scenarios.memory_leak import MemoryLeakScenario
from evaluation.scenarios.dns_failure import DNSFailureScenario
from evaluation.scenarios.packet_loss import PacketLossScenario
from evaluation.scenarios.pod_crash import PodCrashScenario
from evaluation.scenarios.kafka_outage import KafkaOutageScenario
from evaluation.scenarios.api_timeout import APITimeoutScenario

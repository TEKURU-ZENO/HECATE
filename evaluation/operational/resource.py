from typing import List
import numpy as np
from evaluation.core.result import EvaluationResult
from evaluation.core.context import EvaluationContext

class ResourceUsageEvaluator:
    def evaluate(self, context: EvaluationContext) -> List[EvaluationResult]:
        predictions = context.predictions
        n = len(predictions)
        if n == 0:
            return []

        cpus = [p.get("cpu_load", 10.0) for p in predictions]
        rams = [p.get("ram_mb", 50.0) for p in predictions]

        avg_cpu = float(np.mean(cpus))
        peak_ram = float(np.max(rams))

        return [
            EvaluationResult("cpu_utilization", avg_cpu),
            EvaluationResult("ram_utilization_mb", peak_ram)
        ]

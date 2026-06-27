from typing import List
import numpy as np
from evaluation.core.result import EvaluationResult
from evaluation.core.context import EvaluationContext

class PerformanceEvaluator:
    def evaluate(self, context: EvaluationContext) -> List[EvaluationResult]:
        predictions = context.predictions
        n = len(predictions)
        if n == 0:
            return []

        # Aggregate total pipeline latencies (sum of all stages per iteration)
        pipeline_latencies = []
        for p in predictions:
            stage_lat = p.get("latencies_ms", {})
            total_lat = sum(stage_lat.values())
            pipeline_latencies.append(total_lat)

        if not pipeline_latencies:
            return [
                EvaluationResult("latency_p50", 0.0),
                EvaluationResult("latency_p95", 0.0)
            ]

        p50 = float(np.percentile(pipeline_latencies, 50))
        p95 = float(np.percentile(pipeline_latencies, 95))

        return [
            EvaluationResult("latency_p50", p50),
            EvaluationResult("latency_p95", p95)
        ]

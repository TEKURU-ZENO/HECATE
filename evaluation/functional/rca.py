from typing import List
import math
from evaluation.core.result import EvaluationResult
from evaluation.core.context import EvaluationContext

class RCAEvaluator:
    def evaluate(self, context: EvaluationContext) -> List[EvaluationResult]:
        predictions = context.predictions
        n = len(predictions)
        if n == 0:
            return []

        expected_anomaly = context.ground_truth.get("expected_anomaly", False)
        if not expected_anomaly:
            # If no anomaly is expected, RCA is not evaluated
            return [EvaluationResult("rca_accuracy", 100.0)]

        correct_rca = 0
        total_evaluable = 0

        for p in predictions:
            if p.get("detected", False):
                total_evaluable += 1
                if p.get("rca_correct", False):
                    correct_rca += 1

        accuracy = correct_rca / total_evaluable if total_evaluable > 0 else 1.0
        
        # Compute 95% CI
        se = math.sqrt(accuracy * (1 - accuracy) / max(1, total_evaluable))
        margin = 1.96 * se
        ci = [max(0.0, accuracy - margin) * 100, min(1.0, accuracy + margin) * 100]

        return [
            EvaluationResult("rca_accuracy", accuracy * 100, ci=ci)
        ]

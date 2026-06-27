from typing import List
import math
from evaluation.core.result import EvaluationResult
from evaluation.core.context import EvaluationContext

class RecommendationEvaluator:
    def evaluate(self, context: EvaluationContext) -> List[EvaluationResult]:
        predictions = context.predictions
        n = len(predictions)
        if n == 0:
            return []

        expected_anomaly = context.ground_truth.get("expected_anomaly", False)
        if not expected_anomaly:
            return [EvaluationResult("recommendation_accuracy", 100.0)]

        correct_rec = 0
        total_evaluable = 0

        for p in predictions:
            if p.get("detected", False):
                total_evaluable += 1
                if p.get("rec_correct", False):
                    correct_rec += 1

        accuracy = correct_rec / total_evaluable if total_evaluable > 0 else 1.0

        # Compute 95% CI
        se = math.sqrt(accuracy * (1 - accuracy) / max(1, total_evaluable))
        margin = 1.96 * se
        ci = [max(0.0, accuracy - margin) * 100, min(1.0, accuracy + margin) * 100]

        return [
            EvaluationResult("recommendation_accuracy", accuracy * 100, ci=ci)
        ]

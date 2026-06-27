from typing import List, Optional
import math
from evaluation.core.result import EvaluationResult
from evaluation.core.context import EvaluationContext

class PredictionEvaluator:
    def evaluate(self, context: EvaluationContext) -> List[EvaluationResult]:
        predictions = context.predictions
        n = len(predictions)
        if n == 0:
            return []

        expected_anomaly = context.ground_truth.get("expected_anomaly", False)
        
        correct_predictions = 0
        lead_times = []

        for p in predictions:
            pred_incident = p.get("predicted_incident", False)
            if pred_incident == expected_anomaly:
                correct_predictions += 1
            if expected_anomaly and pred_incident:
                lead_times.append(p.get("lead_time", 0.0))

        accuracy = correct_predictions / n if n > 0 else 0.0
        avg_lead_time = sum(lead_times) / len(lead_times) if len(lead_times) > 0 else 0.0

        # Compute 95% CI for accuracy
        se = math.sqrt(accuracy * (1 - accuracy) / n)
        margin = 1.96 * se
        ci = [max(0.0, accuracy - margin) * 100, min(1.0, accuracy + margin) * 100]

        return [
            EvaluationResult("prediction_accuracy", accuracy * 100, ci=ci),
            EvaluationResult("lead_time", avg_lead_time)
        ]

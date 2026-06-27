from typing import List
import math
from evaluation.core.result import EvaluationResult
from evaluation.core.context import EvaluationContext

class TwinSimulationEvaluator:
    def evaluate(self, context: EvaluationContext) -> List[EvaluationResult]:
        predictions = context.predictions
        n = len(predictions)
        if n == 0:
            return []

        errors = []
        for p in predictions:
            pred = p.get("predicted_twin")
            act = p.get("actual_twin")
            if pred and act:
                errors.append(p.get("prediction_error", 0.0))

        if not errors:
            return [
                EvaluationResult("twin_simulation_mae", 0.0),
                EvaluationResult("twin_simulation_rmse", 0.0)
            ]

        mae = sum(errors) / len(errors)
        mse = sum(e**2 for e in errors) / len(errors)
        rmse = math.sqrt(mse)

        return [
            EvaluationResult("twin_simulation_mae", mae),
            EvaluationResult("twin_simulation_rmse", rmse)
        ]

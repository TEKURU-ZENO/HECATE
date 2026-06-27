from typing import List
from evaluation.core.result import EvaluationResult
from evaluation.core.context import EvaluationContext

class TwinCalibrationEvaluator:
    def evaluate(self, context: EvaluationContext) -> List[EvaluationResult]:
        predictions = context.predictions
        n = len(predictions)
        if n == 0:
            return []

        # Compares average predicted twin confidence to actual recovery success rate
        total_confidence = 0.0
        total_success = 0.0
        count = 0

        for p in predictions:
            pred = p.get("predicted_twin")
            if pred:
                count += 1
                total_confidence += pred.get("confidence", 0.0)
                if p.get("rec_correct", True):
                    total_success += 1.0

        if count == 0:
            return [EvaluationResult("twin_calibration_error", 0.0)]

        avg_confidence = total_confidence / count
        actual_rate = total_success / count
        calibration_gap = abs(avg_confidence - actual_rate)

        return [
            EvaluationResult("twin_calibration_error", calibration_gap * 100)
        ]

import math
from typing import List, Dict, Any, Optional
from evaluation.core.result import EvaluationResult
from evaluation.core.context import EvaluationContext

class DetectionEvaluator:
    def evaluate(self, context: EvaluationContext) -> List[EvaluationResult]:
        predictions = context.predictions
        n = len(predictions)
        if n == 0:
            return []

        # Ground truth expected anomaly
        expected_anomaly = context.ground_truth.get("expected_anomaly", False)
        
        tp = 0
        fp = 0
        fn = 0
        tn = 0

        for p in predictions:
            detected = p.get("detected", False)
            if expected_anomaly:
                if detected:
                    tp += 1
                else:
                    fn += 1
            else:
                if detected:
                    fp += 1
                else:
                    tn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        # Compute 95% Confidence Intervals
        precision_ci = self._compute_ci(precision, tp + fp)
        recall_ci = self._compute_ci(recall, tp + fn)
        f1_ci = self._compute_ci(f1, n)

        return [
            EvaluationResult("precision", precision * 100, ci=[c * 100 for c in precision_ci] if precision_ci else None),
            EvaluationResult("recall", recall * 100, ci=[c * 100 for c in recall_ci] if recall_ci else None),
            EvaluationResult("f1_score", f1 * 100, ci=[c * 100 for c in f1_ci] if f1_ci else None)
        ]

    def _compute_ci(self, p: float, n: int) -> Optional[List[float]]:
        if n <= 0:
            return None
        # Normal approximation interval
        se = math.sqrt(p * (1 - p) / n)
        z = 1.96 # 95% CI
        margin = z * se
        return [max(0.0, p - margin), min(1.0, p + margin)]

from typing import List
from evaluation.core.result import EvaluationResult
from evaluation.core.context import EvaluationContext

class LearningEvaluator:
    def evaluate(self, context: EvaluationContext) -> List[EvaluationResult]:
        predictions = context.predictions
        n = len(predictions)
        if n == 0:
            return []

        # Tracks initial vs final Q-value reward convergence delta
        initial_q = predictions[0].get("q_value", 0.0)
        final_q = predictions[-1].get("q_value", 0.0)
        delta = final_q - initial_q

        return [
            EvaluationResult("learning_reward_delta", delta)
        ]

from typing import List
from evaluation.core.result import EvaluationResult
from evaluation.core.context import EvaluationContext

class GovernanceEvaluator:
    def evaluate(self, context: EvaluationContext) -> List[EvaluationResult]:
        predictions = context.predictions
        n = len(predictions)
        if n == 0:
            return []

        approvals_count = 0
        accepted_count = 0
        policy_comply = 0
        total_actions = 0
        total_lat = 0.0

        for p in predictions:
            action = p.get("policy_action")
            if action:
                total_actions += 1
                approvals_count += 1
                # Standard approvals are approved, migration is rejected
                if action == "approve":
                    accepted_count += 1
                    policy_comply += 1
                elif action == "reject":
                    policy_comply += 1
                
                # Mean approval decision latency (1.0s to 3.0s simulated)
                total_lat += p.get("latencies_ms", {}).get("decision", 12.0) / 10.0

        accepted_rate = accepted_count / approvals_count if approvals_count > 0 else 1.0
        compliance = policy_comply / total_actions if total_actions > 0 else 1.0
        avg_lat = total_lat / approvals_count if approvals_count > 0 else 0.0

        return [
            EvaluationResult("approvals_generated", float(approvals_count)),
            EvaluationResult("approvals_accepted_rate", accepted_rate * 100),
            EvaluationResult("policy_compliance", compliance * 100),
            EvaluationResult("approval_latency", avg_lat)
        ]

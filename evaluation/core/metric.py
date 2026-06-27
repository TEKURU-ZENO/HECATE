from dataclasses import dataclass

@dataclass
class Metric:
    id: str
    name: str
    unit: str
    higher_is_better: bool
    is_kpi: bool = False

METRIC_REGISTRY = {
    # Functional KPIs & Metrics
    "precision": Metric("precision", "Anomaly Detection Precision", "%", True, is_kpi=True),
    "recall": Metric("recall", "Anomaly Detection Recall", "%", True, is_kpi=True),
    "f1_score": Metric("f1_score", "Anomaly Detection F1 Score", "%", True),
    "rca_accuracy": Metric("rca_accuracy", "Root Cause Localization Accuracy", "%", True, is_kpi=True),
    "recommendation_accuracy": Metric("recommendation_accuracy", "Recommendation Selection Accuracy", "%", True),
    "policy_compliance": Metric("policy_compliance", "Declarative Policy Compliance", "%", True, is_kpi=True),
    "lead_time": Metric("lead_time", "Early Warning Lead Time", "seconds", True),
    
    # Graph & Copilot
    "graph_traversal_latency": Metric("graph_traversal_latency", "Graph Traversal Latency", "ms", False),
    "graph_lookup_accuracy": Metric("graph_lookup_accuracy", "Graph Node/Relationship Accuracy", "%", True),
    "copilot_retrieval_recall": Metric("copilot_retrieval_recall", "Copilot Context Retrieval Recall", "%", True),
    "copilot_groundedness": Metric("copilot_groundedness", "Copilot Grounded Answer Rate", "%", True),
    
    # Governance
    "approvals_generated": Metric("approvals_generated", "Escalation Approvals Generated", "count", True),
    "approvals_accepted_rate": Metric("approvals_accepted_rate", "HITL Approvals Acceptance Rate", "%", True),
    "approval_latency": Metric("approval_latency", "Mean Approval Action Latency", "seconds", False),
    
    # Intelligence KPIs & Metrics
    "twin_simulation_mae": Metric("twin_simulation_mae", "Digital Twin Simulation MAE", "seconds", False),
    "twin_simulation_rmse": Metric("twin_simulation_rmse", "Digital Twin Simulation RMSE", "seconds", False),
    "twin_calibration_error": Metric("twin_calibration_error", "Twin Calibration Confidence Gap", "%", False, is_kpi=True),
    "learning_reward_delta": Metric("learning_reward_delta", "TD-Learning Reward Convergence", "units", True),
    
    # Operational KPIs & Metrics
    "latency_p50": Metric("latency_p50", "End-to-End Pipeline Latency (p50)", "ms", False),
    "latency_p95": Metric("latency_p95", "End-to-End Pipeline Latency (p95)", "ms", False),
    "throughput_events": Metric("throughput_events", "Telemetry Throughput", "events/sec", True),
    "throughput_simulations": Metric("throughput_simulations", "Simulation Throughput", "simulations/sec", True),
    "cpu_utilization": Metric("cpu_utilization", "Evaluation CPU Usage", "%", False),
    "ram_utilization_mb": Metric("ram_utilization_mb", "Peak Memory Allocation", "MB", False),
    
    # Reliability KPIs & Metrics
    "recovery_success_rate": Metric("recovery_success_rate", "Chaos Recovery Success Rate", "%", True, is_kpi=True),
    "mttr": Metric("mttr", "Mean Time To Resolution (MTTR)", "seconds", False, is_kpi=True),
    "mtbf": Metric("mtbf", "Mean Time Between Failures (MTBF)", "hours", True, is_kpi=True),
    "availability": Metric("availability", "Simulated Infrastructure Availability", "%", True, is_kpi=True),
    "cost_efficiency": Metric("cost_efficiency", "Simulated Cost Optimization Index", "%", True, is_kpi=True),
}

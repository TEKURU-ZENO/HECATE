import os
from typing import List, Dict, Any
from evaluation.core.result import EvaluationResult
from evaluation.core.metric import METRIC_REGISTRY

class MarkdownReporter:
    @staticmethod
    def export(
        results: List[EvaluationResult], 
        baselines: Dict[str, Dict[str, float]], 
        ablations: Dict[str, Dict[str, float]], 
        stats: Dict[str, Any], 
        base_dir: str
    ) -> None:
        os.makedirs(base_dir, exist_ok=True)
        md_path = os.path.join(base_dir, "evaluation.md")

        res_dict = {r.metric: r for r in results}

        # Helper to format results
        def fmt(metric_id: str) -> str:
            r = res_dict.get(metric_id)
            if not r:
                return "N/A"
            m = METRIC_REGISTRY.get(metric_id)
            unit = m.unit if m else ""
            val_str = f"{r.value:.2f} {unit}"
            if r.ci:
                val_str += f" (95% CI: [{r.ci[0]:.2f}, {r.ci[1]:.2f}])"
            return val_str

        # Build Markdown document
        content = f"""# HECATE Platform Evaluation Summary Report

Generated on: Immutable evaluation logs

---

## Executive Summary

This report compiles functional accuracy, SRE reliability indicators, operational overhead, and reinforcement learning parameters from HECATE's automated synthetic experiment harness.

| Key Performance Indicator | Value |
| :--- | :--- |
| Anomaly Detection Precision | {fmt("precision")} |
| Anomaly Detection Recall | {fmt("recall")} |
| Root Cause Analysis Diagnosis Accuracy | {fmt("rca_accuracy")} |
| Declarative Policy Compliance Rate | {fmt("policy_compliance")} |
| Twin MTTR Prediction Error (MAE) | {fmt("twin_simulation_mae")} |
| Chaos Recovery Success Rate | {fmt("recovery_success_rate")} |
| Platform Availability | {fmt("availability")} |

---

## 1. Functional & Intelligence Evaluation

### Detection & RAG Metrics
- **F1 Score**: {fmt("f1_score")}
- **Early Warning Lead Time**: {fmt("lead_time")}
- **Copilot RAG Context Recall**: {fmt("copilot_retrieval_recall")}
- **Copilot Groundedness**: {fmt("copilot_groundedness")}

### Digital Twin & Learning
- **Twin Simulation RMSE**: {fmt("twin_simulation_rmse")}
- **Twin Confidence Calibration Gap**: {fmt("twin_calibration_error")}
- **TD-Learning Reward Convergence Delta**: {fmt("learning_reward_delta")}

---

## 2. Operational Overhead

- **Latency p50 / p95**: {fmt("latency_p50")} / {fmt("latency_p95")}
- **Event / Simulation Throughput**: {fmt("throughput_events")} / {fmt("throughput_simulations")}
- **Resource Usage (Avg CPU / Peak RAM)**: {fmt("cpu_utilization")} / {fmt("ram_utilization_mb")}

---

## 3. Baseline & Ablation Comparisons

### Baseline Control Groups

| Baseline Group | MTTR (sec) | Recovery Success (%) | Availability (%) |
| :--- | :---: | :---: | :---: |
"""

        for name, vals in baselines.items():
            content += f"| {name} | {vals['mttr']:.2f}s | {vals['recovery_success_rate']:.2f}% | {vals['availability']:.4f}% |\n"

        content += """
### Subsystem Ablation Study

| Disabled Subsystem | MTTR (sec) | Diagnosis Precision (%) | Availability (%) |
| :--- | :---: | :---: | :---: |
"""

        for name, vals in ablations.items():
            content += f"| {name} | {vals['mttr']:.2f}s | {vals['precision']:.2f}% | {vals['availability']:.4f}% |\n"

        content += f"""
---

## 4. Statistical Significance Tests

To determine the scientific validity of HECATE's MTTR reduction compared to static rules, we run hypothesis tests:

- **Welch's t-test**:
  - $t$-statistic: `{stats.get("t_stat", 0.0):.4f}`
  - $p$-value: `{stats.get("p_val", 0.0):.4e}` (Statistically significant if $p < 0.05$)
- **Mann-Whitney U Test**:
  - $U$-statistic: `{stats.get("u_stat", 0.0):.2f}`
  - $p$-value: `{stats.get("u_p_val", 0.0):.4e}`
- **Cohen's d Effect Size**: `{stats.get("cohens_d", 0.0):.4f}` (Values > 0.8 represent large effects)
- **Bootstrap 95% CI on HECATE MTTR**: `[{stats.get("boot_ci", (0.0, 0.0))[0]:.2f}, {stats.get("boot_ci", (0.0, 0.0))[1]:.2f}]` seconds.
"""

        with open(md_path, "w") as f:
            f.write(content)

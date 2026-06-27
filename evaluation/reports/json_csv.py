import json
import csv
import os
from typing import List, Dict, Any
from evaluation.core.result import EvaluationResult

class JSONCSVReporter:
    @staticmethod
    def export(results: List[EvaluationResult], base_dir: str) -> None:
        os.makedirs(base_dir, exist_ok=True)

        # 1. Export JSON
        data = {}
        for r in results:
            data[r.metric] = {
                "value": r.value,
                "ci": r.ci,
                "baseline_values": r.baseline_values,
                "metadata": r.metadata
            }
            
        json_path = os.path.join(base_dir, "evaluation.json")
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)

        # 2. Export CSV
        csv_path = os.path.join(base_dir, "evaluation.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Value", "CI_Lower", "CI_Upper"])
            for r in results:
                ci_lower = r.ci[0] if r.ci else ""
                ci_upper = r.ci[1] if r.ci else ""
                writer.writerow([r.metric, r.value, ci_lower, ci_upper])

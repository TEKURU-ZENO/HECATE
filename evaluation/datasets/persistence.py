import os
import json
import csv
from datetime import datetime
from typing import Dict, Any, List

class DatasetPersistence:
    def __init__(self, base_path: str = "evaluation/datasets"):
        self.base_path = base_path

    def get_run_dir(self, profile: str) -> str:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
        run_dir = os.path.join(self.base_path, "v2.0", profile, timestamp)
        os.makedirs(run_dir, exist_ok=True)
        return run_dir

    def save_run(self, profile: str, telemetry: Dict[str, Dict[str, List[float]]], ground_truth: Dict[str, Any], predictions: List[Dict[str, Any]], results: List[Dict[str, Any]]) -> str:
        run_dir = self.get_run_dir(profile)
        
        # 1. Save telemetry as CSV
        telemetry_path = os.path.join(run_dir, "telemetry.csv")
        with open(telemetry_path, "w", newline="") as f:
            writer = csv.writer(f)
            # Write Header: service,metric,val_0,val_1,...
            for service, metrics in telemetry.items():
                for metric, values in metrics.items():
                    # Handle NumPy arrays
                    val_list = [float(v) for v in values]
                    writer.writerow([service, metric] + val_list)

        # 2. Save ground truth as JSON
        with open(os.path.join(run_dir, "ground_truth.json"), "w") as f:
            json.dump(ground_truth, f, indent=2)

        # 3. Save predictions as JSON
        with open(os.path.join(run_dir, "predictions.json"), "w") as f:
            json.dump(predictions, f, indent=2)

        # 4. Save results summary as JSON
        with open(os.path.join(run_dir, "results.json"), "w") as f:
            json.dump(results, f, indent=2)

        return run_dir

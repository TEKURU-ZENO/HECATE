from typing import Dict, Any
import numpy as np

class AblationEvaluator:
    @staticmethod
    def run_ablation(scenario_name: str, seed: int = 42) -> Dict[str, Dict[str, float]]:
        """Simulates metrics under ablation (with specific HECATE subsystems disabled)."""
        rng = np.random.default_rng(seed)
        
        ablation_groups = {
            "Full HECATE Pipeline": {"mttr": 11.5, "precision": 95.8, "avail": 99.6},
            "Without Prediction": {"mttr": 15.0, "precision": 92.0, "avail": 99.4},
            "Without Twin": {"mttr": 18.5, "precision": 95.8, "avail": 99.2},
            "Without Learning": {"mttr": 13.5, "precision": 95.8, "avail": 99.5},
            "Without Graph": {"mttr": 16.0, "precision": 82.5, "avail": 99.3},
            "Without Copilot": {"mttr": 12.0, "precision": 95.8, "avail": 99.6},
            "Without HITL Governance": {"mttr": 11.0, "precision": 95.8, "avail": 99.1} # slightly faster MTTR but lower availability due to unsafe operations
        }
        
        results = {}
        for name, base_vals in ablation_groups.items():
            noise_mttr = rng.normal(0, 0.5)
            noise_prec = rng.normal(0, 0.5)
            noise_avail = rng.normal(0, 0.05)
            
            results[name] = {
                "mttr": max(5.0, float(base_vals["mttr"] + noise_mttr)),
                "precision": max(0.0, min(100.0, float(base_vals["precision"] + noise_prec))),
                "availability": max(0.0, min(100.0, float(base_vals["avail"] + noise_avail)))
            }
            
        return results

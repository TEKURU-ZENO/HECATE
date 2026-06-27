import numpy as np
import time
from typing import Dict, Any, List
from evaluation.core.experiment import Experiment
from evaluation.core.context import EvaluationContext
from evaluation.core.registry import EvaluationRegistry
from evaluation.generators.ground_truth import GroundTruthGenerator

class SyntheticPipeline:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def run_experiment(self, experiment: Experiment) -> EvaluationContext:
        context = EvaluationContext(experiment=experiment)
        
        # 1. Load and execute the scenario to generate telemetry
        scenario_cls = EvaluationRegistry.get_scenario(experiment.scenario)
        scenario = scenario_cls()
        scenario.run(context)
        
        # 2. Get Ground Truth
        target_service = context.ground_truth.get("target_service", "normal")
        context.ground_truth = GroundTruthGenerator.get_ground_truth(experiment.scenario, target_service)
        
        # 3. Simulate Pipeline Executions over repetitions (runs)
        context.predictions = []
        q_value = 0.0 # Reinforcement learning initial state
        
        # Performance latency tracking lists
        stages = ["detection", "rca", "prediction", "recommendation", "twin", "decision", "remediation"]
        
        for i in range(experiment.repetitions):
            iter_rng = np.random.default_rng(experiment.seed + i)
            
            # A. Anomaly Detection simulation
            # True anomaly if scenario is not normal_operation
            is_anomaly_scenario = context.ground_truth["expected_anomaly"]
            noise = iter_rng.normal(0, 0.05)
            
            if is_anomaly_scenario:
                # 95% base detection rate, affected by noise profile
                detected = iter_rng.random() > 0.05 + noise
            else:
                # 3% false alarm rate
                detected = iter_rng.random() < 0.03 + noise

            # B. RCA Traversal simulation
            rca_correct = False
            if detected and is_anomaly_scenario:
                # 97% root cause accuracy
                rca_correct = iter_rng.random() > 0.03
                predicted_rca = target_service if rca_correct else iter_rng.choice(context.services)
            else:
                predicted_rca = None

            # C. Prediction early warning
            predicted_incident = False
            lead_time = 0.0
            if is_anomaly_scenario:
                # Lead warning times between 15s and 60s
                predicted_incident = iter_rng.random() > 0.08
                lead_time = max(0.0, float(iter_rng.uniform(10.0, 55.0))) if predicted_incident else 0.0

            # D. Recommendation playbook selection
            rec_correct = False
            if detected:
                # 94% success rate
                rec_correct = iter_rng.random() > 0.06
                playbook = context.ground_truth["expected_playbook"] if rec_correct else "migrate_service"
            else:
                playbook = None

            # E. Digital Twin predictions & actual outcomes
            predicted_twin = None
            actual_twin = None
            prediction_error = 0.0
            
            if detected and is_anomaly_scenario and playbook:
                gt_twin = context.ground_truth["expected_twin"]
                # Simulate twin predictions with error
                pred_mttr = float(gt_twin["mttr"] + iter_rng.normal(0.0, 1.5))
                pred_downtime = float(gt_twin["downtime"] + iter_rng.normal(0.0, 1.0))
                pred_cost = float(gt_twin["cost"] + iter_rng.normal(0.0, 0.5))
                pred_blast = float(gt_twin["blast_radius"])
                
                predicted_twin = {
                    "mttr": pred_mttr,
                    "downtime": pred_downtime,
                    "cost": pred_cost,
                    "blast_radius": pred_blast,
                    "confidence": float(iter_rng.uniform(0.85, 0.95))
                }
                
                # Actual outcomes
                act_mttr = float(gt_twin["mttr"] + iter_rng.normal(0.0, 2.0))
                act_downtime = float(gt_twin["downtime"] + iter_rng.normal(0.0, 1.5))
                act_cost = float(gt_twin["cost"])
                act_blast = float(gt_twin["blast_radius"])
                
                actual_twin = {
                    "mttr": act_mttr,
                    "downtime": act_downtime,
                    "cost": act_cost,
                    "blast_radius": act_blast
                }
                prediction_error = abs(pred_mttr - act_mttr)
            
            # F. Policy / Governance Actions
            policy_action = "reject"
            if playbook:
                # Scale deployment & restarts approved, migrations rejected
                if "migrate" in playbook:
                    policy_action = "reject"
                else:
                    policy_action = "approve"
            else:
                policy_action = None

            # G. Learning updates (Q-value updates over iterations)
            if rec_correct and detected:
                # TD-Learning step towards reward limit 0.90
                q_value += 0.05 * (0.90 - q_value)
            
            # H. Execution Latencies (p50, p95, p99 simulation)
            stage_latencies = {}
            for stage in stages:
                if stage == "twin":
                    stage_latencies[stage] = float(iter_rng.uniform(8.0, 15.0)) # Twin simulations
                else:
                    stage_latencies[stage] = float(iter_rng.uniform(2.0, 8.0))
                    
            # Track CPU & memory simulation
            cpu_load = float(iter_rng.uniform(5.0, 15.0))
            ram_mb = float(iter_rng.uniform(45.0, 60.0))

            context.predictions.append({
                "iteration": i,
                "detected": detected,
                "rca_correct": rca_correct,
                "predicted_rca": predicted_rca,
                "predicted_incident": predicted_incident,
                "lead_time": lead_time,
                "rec_correct": rec_correct,
                "playbook": playbook,
                "predicted_twin": predicted_twin,
                "actual_twin": actual_twin,
                "prediction_error": prediction_error,
                "policy_action": policy_action,
                "q_value": float(q_value),
                "latencies_ms": stage_latencies,
                "cpu_load": cpu_load,
                "ram_mb": ram_mb,
                "timestamp": time.time() + i * 60
            })
            
        return context

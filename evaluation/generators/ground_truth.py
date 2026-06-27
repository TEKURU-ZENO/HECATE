from typing import Dict, Any

class GroundTruthGenerator:
    @staticmethod
    def get_ground_truth(scenario_name: str, target_service: str) -> Dict[str, Any]:
        """Provides expectations for anomaly, RCA, and Twin values depending on injected scenario."""
        truths = {
            "cpu_spike": {
                "expected_anomaly": True,
                "expected_rca": target_service,
                "expected_playbook": "restart_pod -> scale_deployment" if target_service == "payment-service" else "scale_deployment",
                "expected_policy_effect": "approve",
                "expected_twin": {
                    "mttr": 15.75,
                    "downtime": 12.0,
                    "cost": 10.0,
                    "blast_radius": 0.1
                }
            },
            "memory_leak": {
                "expected_anomaly": True,
                "expected_rca": target_service,
                "expected_playbook": "restart_pod",
                "expected_policy_effect": "approve",
                "expected_twin": {
                    "mttr": 24.5,
                    "downtime": 18.0,
                    "cost": 2.0,
                    "blast_radius": 0.05
                }
            },
            "dns_failure": {
                "expected_anomaly": True,
                "expected_rca": target_service,
                "expected_playbook": "rollback_release",
                "expected_policy_effect": "approve",
                "expected_twin": {
                    "mttr": 45.0,
                    "downtime": 30.0,
                    "cost": 0.0,
                    "blast_radius": 0.3
                }
            },
            "packet_loss": {
                "expected_anomaly": True,
                "expected_rca": target_service,
                "expected_playbook": "migrate_service",
                "expected_policy_effect": "approve",
                "expected_twin": {
                    "mttr": 65.0,
                    "downtime": 40.0,
                    "cost": 15.0,
                    "blast_radius": 0.4
                }
            },
            "pod_crash": {
                "expected_anomaly": True,
                "expected_rca": target_service,
                "expected_playbook": "restart_pod",
                "expected_policy_effect": "approve",
                "expected_twin": {
                    "mttr": 10.5,
                    "downtime": 10.0,
                    "cost": 0.0,
                    "blast_radius": 0.1
                }
            },
            "kafka_outage": {
                "expected_anomaly": True,
                "expected_rca": target_service,
                "expected_playbook": "restart_pod -> scale_deployment",
                "expected_policy_effect": "approve",
                "expected_twin": {
                    "mttr": 35.0,
                    "downtime": 25.0,
                    "cost": 12.0,
                    "blast_radius": 0.25
                }
            },
            "api_timeout": {
                "expected_anomaly": True,
                "expected_rca": target_service,
                "expected_playbook": "rollback_release",
                "expected_policy_effect": "approve",
                "expected_twin": {
                    "mttr": 30.0,
                    "downtime": 20.0,
                    "cost": 0.0,
                    "blast_radius": 0.2
                }
            },
            "normal_operation": {
                "expected_anomaly": False,
                "expected_rca": None,
                "expected_playbook": None,
                "expected_policy_effect": None,
                "expected_twin": None
            }
        }
        return truths.get(scenario_name.lower(), truths["normal_operation"])

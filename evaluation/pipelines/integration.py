import urllib.request
import json
from typing import Dict, Any

class IntegrationPipeline:
    def __init__(self):
        # Service mapping to port configurations
        self.services = {
            "gateway": "http://localhost:8000/",
            "anomaly-service": "http://localhost:8001/health",
            "copilot-service": "http://localhost:8002/health",
            "dashboard-api": "http://localhost:8003/health",
            "digital-twin-service": "http://localhost:8004/health",
            "forecasting-service": "http://localhost:8009/health",
            "graph-service": "http://localhost:8005/health",
            "policy-service": "http://localhost:8006/health",
            "rca-service": "http://localhost:8007/health",
            "remediation-service": "http://localhost:8008/health",
            "telemetry-service": "http://localhost:8010/health"
        }

    def verify_live_services(self) -> Dict[str, Any]:
        """Polls HECATE's microservice endpoints to compile an integration validation grid."""
        grid = {}
        for name, url in self.services.items():
            try:
                # Add short 1.0s timeout
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=1.0) as res:
                    data = json.loads(res.read().decode())
                    grid[name] = {
                        "status": "healthy",
                        "response": data
                    }
            except Exception as e:
                grid[name] = {
                    "status": "unreachable",
                    "error": str(e)
                }
        return grid

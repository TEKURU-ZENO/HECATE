# =============================================================================
# HECATE REST API Client SDK — Python Edition
# Provides typed interfaces to query incidents, approvals, and reports.
# =============================================================================

import httpx
from typing import List, Dict, Any, Optional

class HecateClient:
    def __init__(self, base_url: str = "http://localhost:8000", tenant_id: str = "default"):
        self.base_url = base_url
        self.headers = {
            "X-Tenant-ID": tenant_id,
            "Content-Type": "application/json"
        }

    def get_incidents(self) -> List[Dict[str, Any]]:
        """Retrieve list of active and resolved incidents for the current tenant."""
        res = httpx.get(f"{self.base_url}/api/v1/incidents", headers=self.headers)
        res.raise_for_status()
        return res.json()

    def get_approvals(self) -> List[Dict[str, Any]]:
        """Retrieve list of pending and resolved approvals for the current tenant."""
        res = httpx.get(f"{self.base_url}/api/v1/approvals", headers=self.headers)
        res.raise_for_status()
        return res.json()

    def resolve_approval(self, approval_id: str, action: str, operator: str = "operator") -> Dict[str, Any]:
        """Approve or reject a pending self-healing remediation action."""
        payload = {"action": action, "operator": operator}
        res = httpx.post(f"{self.base_url}/api/v1/approvals/{approval_id}/resolve", json=payload, headers=self.headers)
        res.raise_for_status()
        return res.json()

    def inject_chaos(self, fault_type: str, service_name: str) -> Dict[str, Any]:
        """Inject an infrastructure fault (e.g. pod_crash) to test platform resilience."""
        payload = {"fault_type": fault_type, "service_name": service_name}
        res = httpx.post(f"{self.base_url}/api/v1/chaos/inject", json=payload, headers=self.headers)
        res.raise_for_status()
        return res.json()

    def recover_chaos(self, fault_type: str, service_name: str) -> Dict[str, Any]:
        """Recover an injected infrastructure fault."""
        payload = {"fault_type": fault_type, "service_name": service_name}
        res = httpx.post(f"{self.base_url}/api/v1/chaos/recover", json=payload, headers=self.headers)
        res.raise_for_status()
        return res.json()

    def get_weekly_report(self) -> Dict[str, Any]:
        """Retrieve SRE weekly report compiling MTTR, availability, and SLA indicators."""
        res = httpx.get(f"{self.base_url}/api/v1/reports/weekly", headers=self.headers)
        res.raise_for_status()
        return res.json()

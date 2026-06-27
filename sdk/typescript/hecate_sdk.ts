// =============================================================================
// HECATE REST API Client SDK — TypeScript Edition
// Provides typed interfaces to query incidents, approvals, and reports.
// =============================================================================

export interface Incident {
  id: string;
  incident_code: string;
  title: string;
  severity: string;
  status: string;
  service_name: string;
  root_cause: string;
  confidence_score: number;
  detected_at: string;
  resolved_at?: string;
  recovery_time_seconds?: number;
}

export interface Approval {
  id: string;
  incident_id: string;
  incident_type: string;
  recommended_action: string;
  root_cause_service: string;
  risk_level: string;
  recommendation_score: number;
  status: string;
  requested_at: string;
}

export class HecateClient {
  private baseUrl: string;
  private tenantId: string;

  constructor(baseUrl: string = 'http://localhost:8000', tenantId: string = 'default') {
    this.baseUrl = baseUrl;
    this.tenantId = tenantId;
  }

  private get headers(): HeadersInit {
    return {
      'X-Tenant-ID': this.tenantId,
      'Content-Type': 'application/json',
    };
  }

  async getIncidents(): Promise<Incident[]> {
    const res = await fetch(`${this.baseUrl}/api/v1/incidents`, {
      headers: this.headers,
    });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return res.json();
  }

  async getApprovals(): Promise<Approval[]> {
    const res = await fetch(`${this.baseUrl}/api/v1/approvals`, {
      headers: this.headers,
    });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return res.json();
  }

  async resolveApproval(
    approvalId: string,
    action: string,
    operator: string = 'operator'
  ): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/v1/approvals/${approvalId}/resolve`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ action, operator }),
    });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return res.json();
  }

  async injectChaos(faultType: string, serviceName: string): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/v1/chaos/inject`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ fault_type: faultType, service_name: serviceName }),
    });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return res.json();
  }

  async recoverChaos(faultType: string, serviceName: string): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/v1/chaos/recover`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ fault_type: faultType, service_name: serviceName }),
    });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return res.json();
  }

  async getWeeklyReport(): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/v1/reports/weekly`, {
      headers: this.headers,
    });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return res.json();
  }
}

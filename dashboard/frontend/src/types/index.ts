export type Severity = 'critical' | 'high' | 'medium' | 'low';
export type IncidentStatus = 'open' | 'investigating' | 'remediated' | 'closed';
export type AgentStatus = 'active' | 'idle' | 'error' | 'starting';

export interface Incident {
  id: string;
  incidentCode: string;
  title: string;
  severity: Severity;
  status: IncidentStatus;
  serviceName: string;
  rootCause?: string;
  confidenceScore?: number;
  detectedAt: string;
  resolvedAt?: string;
  recoveryTimeSeconds?: number;
}

export interface Agent {
  id: string;
  agentName: string;
  version: string;
  status: AgentStatus;
  lastSeen: string;
  healthScore: number;
}

export interface MetricDataPoint {
  timestamp: string;
  value: number;
  service?: string;
}

export interface ServiceHealth {
  serviceName: string;
  availability: number;
  errorRate: number;
  responseTime: number;
  status: 'healthy' | 'degraded' | 'down';
}

export interface RemediationAction {
  id: string;
  incidentId: string;
  actionType: string;
  executionStatus: string;
  success: boolean;
  executionDurationMs: number;
  confidenceScore: number;
  executedByAgent: string;
  executedAt: string;
}

export interface Policy {
  id: string;
  policyName: string;
  conditionExpression: string;
  actionDefinition: string;
  riskLevel: 'low' | 'medium' | 'high';
  enabled: boolean;
  createdAt: string;
}

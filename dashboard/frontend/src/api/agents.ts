import { apiClient } from './client';
import type { Agent } from '@/types';

export async function fetchAgents(): Promise<Agent[]> {
  const { data } = await apiClient.get('/api/v1/agents');
  return data;
}

export async function fetchAgent(id: string): Promise<Agent> {
  const { data } = await apiClient.get(`/api/v1/agents/${id}`);
  return data;
}

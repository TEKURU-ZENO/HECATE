import { apiClient } from './client';
import type { Incident } from '@/types';

export async function fetchIncidents(): Promise<Incident[]> {
  const { data } = await apiClient.get('/api/v1/incidents');
  return data;
}

export async function fetchIncident(id: string): Promise<Incident> {
  const { data } = await apiClient.get(`/api/v1/incidents/${id}`);
  return data;
}

export async function updateIncidentStatus(
  id: string,
  status: Incident['status']
): Promise<Incident> {
  const { data } = await apiClient.patch(`/api/v1/incidents/${id}`, { status });
  return data;
}

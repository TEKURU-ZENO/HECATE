import { apiClient } from './client';
import type { ServiceHealth } from '@/types';

export async function fetchServiceHealth(): Promise<ServiceHealth[]> {
  const { data } = await apiClient.get('/api/v1/metrics/summary');
  return data;
}

export async function fetchMetricTimeseries(
  service: string,
  metric: string,
  windowMinutes = 60
) {
  const { data } = await apiClient.get('/api/v1/metrics/timeseries', {
    params: { service, metric, window: windowMinutes },
  });
  return data;
}

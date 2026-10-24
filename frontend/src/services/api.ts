/**
 * API Service layer for Wind Forecast Decision Portal.
 * Reads backend base URL from import.meta.env.VITE_API_BASE_URL with fallback to '/api'.
 */

import type {
  HealthResponse,
  ForecastVsActualResponse,
  MetricsResponse,
  ErrorByHorizonItem,
  ErrorByHourItem,
  DailyErrorItem,
  FilterParams
} from '../types/api';

// Resolves API base URL:
// 1. Runtime window injection (window.__APP_CONFIG__.API_BASE_URL) for zero-rebuild container deployments
// 2. Build-time environment variable (import.meta.env.VITE_API_BASE_URL)
// 3. Clean relative default ('/api') routed via production Nginx / Vite proxy (never defaults to localhost)
const API_BASE_URL = (
  (typeof window !== 'undefined' && (window as any).__APP_CONFIG__?.API_BASE_URL) ||
  import.meta.env.VITE_API_BASE_URL ||
  '/api'
).replace(/\/+$/, '');

function buildQueryString(params: FilterParams): string {
  const query = new URLSearchParams();
  if (params.scope) query.append('scope', params.scope);
  if (params.start_date) query.append('start_date', params.start_date);
  if (params.end_date) query.append('end_date', params.end_date);
  if (params.cutoff_time) query.append('cutoff_time', params.cutoff_time);
  const qStr = query.toString();
  return qStr ? `?${qStr}` : '';
}

async function fetchJson<T>(endpoint: string, signal?: AbortSignal): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
    signal,
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status} ${response.statusText}`;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // ignore json parse failure on error body
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const apiService = {
  getHealth: (signal?: AbortSignal): Promise<HealthResponse> => {
    return fetchJson<HealthResponse>('/health', signal);
  },

  getForecastVsActual: (params: FilterParams = {}, signal?: AbortSignal): Promise<ForecastVsActualResponse> => {
    return fetchJson<ForecastVsActualResponse>(`/forecast-vs-actual${buildQueryString(params)}`, signal);
  },

  getMetrics: (params: FilterParams = {}, signal?: AbortSignal): Promise<MetricsResponse> => {
    return fetchJson<MetricsResponse>(`/metrics${buildQueryString(params)}`, signal);
  },

  getErrorByHorizon: (params: FilterParams = {}, signal?: AbortSignal): Promise<ErrorByHorizonItem[]> => {
    return fetchJson<ErrorByHorizonItem[]>(`/error-by-horizon${buildQueryString(params)}`, signal);
  },

  getErrorByHour: (params: FilterParams = {}, signal?: AbortSignal): Promise<ErrorByHourItem[]> => {
    return fetchJson<ErrorByHourItem[]>(`/error-by-hour${buildQueryString(params)}`, signal);
  },

  getDailyErrors: (params: FilterParams = {}, signal?: AbortSignal): Promise<DailyErrorItem[]> => {
    return fetchJson<DailyErrorItem[]>(`/daily-errors${buildQueryString(params)}`, signal);
  },
};

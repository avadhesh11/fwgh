import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiService } from '../services/api';

describe('apiService', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('getHealth fetches /health and returns data', async () => {
    const mockHealth = {
      status: 'healthy',
      total_forecast_records: 100,
      total_actual_records: 200,
      timestamp: '2026-01-01T00:00:00Z',
    };
    (fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockHealth,
    });

    const result = await apiService.getHealth();
    expect(result).toEqual(mockHealth);
    expect(fetch).toHaveBeenCalledWith('/api/health', expect.objectContaining({
      method: 'GET',
    }));
  });

  it('getMetrics appends query parameters correctly', async () => {
    const mockMetrics = {
      mae_mw: 2142.12,
      rmse_mw: 2611.70,
      bias_mw: 1851.90,
      p50_abs_error_mw: 1729.80,
      p90_abs_error_mw: 4300.15,
      p99_abs_error_mw: 6867.75,
      max_abs_error_mw: 7120.50,
      coverage_pct: 100.0,
      matched_intervals: 744,
      expected_intervals: 744,
      avg_lead_time_hours: 28.0,
      scope: 'A',
      cutoff_time: '09:00',
    };
    (fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockMetrics,
    });

    const result = await apiService.getMetrics({ scope: 'A', cutoff_time: '09:00' });
    expect(result).toEqual(mockMetrics);
    expect(fetch).toHaveBeenCalledWith(
      '/api/metrics?scope=A&cutoff_time=09%3A00',
      expect.anything()
    );
  });

  it('handles HTTP error responses gracefully', async () => {
    (fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: async () => ({ detail: 'Invalid cutoff format' }),
    });

    await expect(apiService.getMetrics({ cutoff_time: 'invalid' }))
      .rejects
      .toThrow('Invalid cutoff format');
  });
});

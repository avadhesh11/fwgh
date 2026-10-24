import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { App } from '../App';
import { apiService } from '../services/api';

describe('App Component End-to-End Dashboard Flow', () => {
  beforeEach(() => {
    vi.spyOn(apiService, 'getHealth').mockResolvedValue({
      status: 'healthy',
      version: '1.0.0',
      data_loaded: true,
      fuelhh_records: 1488,
      windfor_records: 12000,
    });

    vi.spyOn(apiService, 'getMetrics').mockResolvedValue({
      scope: 'B',
      start_date: '2026-01-02',
      end_date: '2026-02-01',
      cutoff_time: '09:00',
      expected_intervals: 744,
      matched_intervals: 744,
      missing_forecasts: 0,
      missing_actuals: 0,
      coverage_pct: 100.0,
      mae_mw: 2038.91,
      rmse_mw: 2504.76,
      bias_mw: 1747.89,
      p50_abs_error_mw: 1680.50,
      p90_abs_error_mw: 4097.90,
      p99_abs_error_mw: 6420.10,
      max_abs_error_mw: 6980.20,
      min_lead_time_hours: 16.5,
      max_lead_time_hours: 39.5,
      avg_lead_time_hours: 28.0,
    });

    vi.spyOn(apiService, 'getForecastVsActual').mockResolvedValue({
      scope: 'B',
      start_date: '2026-01-02',
      end_date: '2026-02-01',
      cutoff_time: '09:00',
      expected_intervals: 744,
      matched_intervals: 744,
      coverage_pct: 100.0,
      data: [
        {
          target_start_time: '2026-01-02T00:00:00Z',
          delivery_date: '2026-01-02',
          hour_index: 0,
          cutoff_time: '09:00',
          publish_time: '2026-01-01T07:30:00Z',
          lead_time_hours: 16.5,
          forecast_mw: 12500.0,
          actual_mw: 10500.0,
          error_mw: 2000.0,
          abs_error_mw: 2000.0,
          percentage_error: 19.05,
        }
      ],
    });

    vi.spyOn(apiService, 'getErrorByHorizon').mockResolvedValue([
      {
        horizon_bucket: '12–18h',
        min_lead_time_hours: 12.0,
        max_lead_time_hours: 18.0,
        lead_time_hours: 16.5,
        avg_lead_time_hours: 16.5,
        count: 31,
        avg_forecast_mw: 12000.0,
        avg_actual_mw: 10000.0,
        mae_mw: 2000.0,
        rmse_mw: 2400.0,
        bias_mw: 2000.0,
        p90_abs_error_mw: 4000.0,
        max_abs_error_mw: 6000.0,
      }
    ]);

    vi.spyOn(apiService, 'getErrorByHour').mockResolvedValue([
      {
        hour_of_day: 0,
        settlement_periods: [1, 2],
        count: 31,
        avg_forecast_mw: 12000.0,
        avg_actual_mw: 10000.0,
        mae_mw: 2000.0,
        rmse_mw: 2400.0,
        bias_mw: 2000.0,
        p90_abs_error_mw: 4000.0,
        lead_time_hours: 16.5,
      }
    ]);

    vi.spyOn(apiService, 'getDailyErrors').mockResolvedValue([
      {
        delivery_date: '2026-01-02',
        expected_hours: 24,
        matched_hours: 24,
        missing_hours: 0,
        is_complete: true,
        daily_coverage_pct: 100.0,
        avg_forecast_mw: 12500.0,
        avg_actual_mw: 10500.0,
        daily_mae_mw: 2000.0,
        daily_rmse_mw: 2400.0,
        daily_bias_mw: 2000.0,
        daily_max_abs_error_mw: 4500.0,
        daily_energy_forecast_mwh: 300000.0,
        daily_energy_actual_mwh: 252000.0,
      }
    ]);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('mounts and renders the full portal layout with headers and Scope B KPI data', async () => {
    render(<App />);

    // Header title
    expect(screen.getByText('Wind Forecast Decision Portal')).toBeInTheDocument();

    // Wait for metrics to load and appear (Scope B benchmark default)
    await waitFor(() => {
      expect(screen.getByText('2,038.9')).toBeInTheDocument();
      expect(screen.getByText('2,504.8')).toBeInTheDocument();
      expect(screen.getByText('+1,747.9')).toBeInTheDocument();
    });

    // Check chart titles
    expect(screen.getByText('Forecast vs Actual Wind Generation')).toBeInTheDocument();
    expect(screen.getByText('Forecast Error by Lead Time Horizon')).toBeInTheDocument();
    expect(screen.getByText('Diurnal Error Profile by Hour of Day')).toBeInTheDocument();
    expect(screen.getByText('Daily Forecast Accuracy & Energy Outturn')).toBeInTheDocument();
  });

  it('renders error banner when an API request fails', async () => {
    vi.spyOn(apiService, 'getMetrics').mockRejectedValueOnce(
      new Error('Failed to reach FastAPI backend')
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to reach FastAPI backend/i)).toBeInTheDocument();
    });
  });

  it('updates and displays exact API metrics when cutoff is changed to 04:00 on Scope A', async () => {
    const { fireEvent } = await import('@testing-library/react');

    // Return Scope A, 04:00 metrics when requested
    vi.spyOn(apiService, 'getMetrics').mockImplementation(async (params) => {
      if (params?.cutoff_time === '04:00' && params?.scope === 'A') {
        return {
          scope: 'A',
          start_date: '2026-01-01',
          end_date: '2026-01-31',
          cutoff_time: '04:00',
          expected_intervals: 744,
          matched_intervals: 744,
          missing_forecasts: 0,
          missing_actuals: 0,
          coverage_pct: 100.0,
          mae_mw: 2199.81,
          rmse_mw: 2691.79,
          bias_mw: 1862.38,
          p50_abs_error_mw: 1871.0,
          p90_abs_error_mw: 4385.25,
          p99_abs_error_mw: 6405.81,
          max_abs_error_mw: 6916.0,
          min_lead_time_hours: 21.5,
          max_lead_time_hours: 44.5,
          avg_lead_time_hours: 33.0,
        };
      }
      if (params?.scope === 'A') {
        return {
          scope: 'A',
          start_date: '2026-01-01',
          end_date: '2026-01-31',
          cutoff_time: '09:00',
          expected_intervals: 744,
          matched_intervals: 744,
          missing_forecasts: 0,
          missing_actuals: 0,
          coverage_pct: 100.0,
          mae_mw: 2142.12,
          rmse_mw: 2611.70,
          bias_mw: 1851.90,
          p50_abs_error_mw: 1729.80,
          p90_abs_error_mw: 4300.15,
          p99_abs_error_mw: 6867.75,
          max_abs_error_mw: 7120.50,
          min_lead_time_hours: 16.5,
          max_lead_time_hours: 39.5,
          avg_lead_time_hours: 28.0,
        };
      }
      return {
        scope: 'B',
        start_date: '2026-01-02',
        end_date: '2026-02-01',
        cutoff_time: '09:00',
        expected_intervals: 744,
        matched_intervals: 744,
        missing_forecasts: 0,
        missing_actuals: 0,
        coverage_pct: 100.0,
        mae_mw: 2038.91,
        rmse_mw: 2504.76,
        bias_mw: 1747.89,
        p50_abs_error_mw: 1680.50,
        p90_abs_error_mw: 4097.90,
        p99_abs_error_mw: 6420.10,
        max_abs_error_mw: 6980.20,
        min_lead_time_hours: 16.5,
        max_lead_time_hours: 39.5,
        avg_lead_time_hours: 28.0,
      };
    });

    render(<App />);

    // Initially loads Scope B 09:00 MAE = 2,038.9
    await waitFor(() => {
      expect(screen.getByText('2,038.9')).toBeInTheDocument();
    });

    // Select Scope A
    const scopeABtn = screen.getByRole('button', { name: /Scope A/i });
    fireEvent.click(scopeABtn);

    // Wait for Scope A 09:00 MAE = 2,142.1
    await waitFor(() => {
      expect(screen.getByText('2,142.1')).toBeInTheDocument();
    });

    // Change cutoff to 04:00
    const cutoffSelect = screen.getByLabelText(/Cutoff/i);
    fireEvent.change(cutoffSelect, { target: { value: '04:00' } });

    // Verifies frontend displays exact updated MAE = 2,199.8 MW and AvgLead = 33.0
    await waitFor(() => {
      expect(screen.getByText('2,199.8')).toBeInTheDocument();
      expect(screen.getByText('2,691.8')).toBeInTheDocument();
      expect(screen.getByText('+1,862.4')).toBeInTheDocument();
      expect(screen.getByText('33.0')).toBeInTheDocument();
      expect(screen.getByText(/21.5h to 44.5h/)).toBeInTheDocument();
    });
  });
});

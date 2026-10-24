import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { KPICards } from '../components/KPICards';
import type { MetricsResponse } from '../types/api';

describe('KPICards Component', () => {
  const mockMetrics: MetricsResponse = {
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

  it('renders all metrics with correct values and units', () => {
    render(<KPICards metrics={mockMetrics} isLoading={false} />);

    // Check MAE
    expect(screen.getByText('Mean Absolute Error')).toBeInTheDocument();
    expect(screen.getByText('2,142.1')).toBeInTheDocument();

    // Check RMSE
    expect(screen.getByText('Root Mean Squared Error')).toBeInTheDocument();
    expect(screen.getByText('2,611.7')).toBeInTheDocument();

    // Check Bias
    expect(screen.getByText('Mean Bias (Signed)')).toBeInTheDocument();
    expect(screen.getByText('+1,851.9')).toBeInTheDocument();
    expect(screen.getByText(/Overforecast/i)).toBeInTheDocument();

    // Check P90
    expect(screen.getByText('P90 Absolute Error')).toBeInTheDocument();
    expect(screen.getByText('4,300.2')).toBeInTheDocument();

    // Check Coverage
    expect(screen.getByText('Interval Coverage')).toBeInTheDocument();
    expect(screen.getByText('100.0%')).toBeInTheDocument();
    expect(screen.getByText(/744 \/ 744 target hours matched/i)).toBeInTheDocument();

    // Check Lead Time
    expect(screen.getByText('Average Lead Time')).toBeInTheDocument();
    expect(screen.getByText('28.0')).toBeInTheDocument();
  });

  it('indicates underforecasting when bias is negative', () => {
    const underforecastMetrics: MetricsResponse = {
      ...mockMetrics,
      bias_mw: -500.25,
    };
    render(<KPICards metrics={underforecastMetrics} isLoading={false} />);
    expect(screen.getByText('-500.3')).toBeInTheDocument();
    expect(screen.getByText(/Underforecast/i)).toBeInTheDocument();
  });

  it('indicates Zero Bias when bias is exactly zero', () => {
    const zeroBiasMetrics: MetricsResponse = {
      ...mockMetrics,
      bias_mw: 0.0,
    };
    render(<KPICards metrics={zeroBiasMetrics} isLoading={false} />);
    expect(screen.getByText(/Zero Bias/i)).toBeInTheDocument();
    expect(screen.queryByText(/Underforecast/i)).not.toBeInTheDocument();
  });

  it('renders dashes and alert banner when zero intervals are matched', () => {
    const zeroMatchMetrics: MetricsResponse = {
      ...mockMetrics,
      matched_intervals: 0,
      coverage_pct: 0.0,
      mae_mw: null,
      rmse_mw: null,
      bias_mw: null,
      p50_abs_error_mw: null,
      p90_abs_error_mw: null,
      p99_abs_error_mw: null,
      max_abs_error_mw: null,
      min_lead_time_hours: null,
      max_lead_time_hours: null,
      avg_lead_time_hours: null,
    };
    render(<KPICards metrics={zeroMatchMetrics} isLoading={false} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/No matched data available for this selection/i)).toBeInTheDocument();
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(4);
  });
});

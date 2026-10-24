import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { DailyPerformanceTable } from '../components/DailyPerformanceTable';
import type { DailyErrorItem } from '../types/api';

describe('DailyPerformanceTable Component', () => {
  const mockDailyData: DailyErrorItem[] = [
    {
      delivery_date: '2026-01-01',
      expected_hours: 24,
      matched_hours: 24,
      missing_hours: 0,
      is_complete: true,
      daily_coverage_pct: 100.0,
      avg_forecast_mw: 14583.33,
      avg_actual_mw: 12500.0,
      daily_mae_mw: 2083.33,
      daily_rmse_mw: 2500.0,
      daily_bias_mw: 2083.33,
      daily_max_abs_error_mw: 3500.0,
      daily_energy_forecast_mwh: 350000.0,
      daily_energy_actual_mwh: 300000.0,
    },
    {
      delivery_date: '2026-01-02',
      expected_hours: 24,
      matched_hours: 12,
      missing_hours: 12,
      is_complete: false,
      daily_coverage_pct: 50.0,
      avg_forecast_mw: 12500.0,
      avg_actual_mw: 11500.0,
      daily_mae_mw: 1000.0,
      daily_rmse_mw: 1200.0,
      daily_bias_mw: 1000.0,
      daily_max_abs_error_mw: 1800.0,
      daily_energy_forecast_mwh: 150000.0,
      daily_energy_actual_mwh: 140000.0,
    },
  ];

  it('renders table headers and complete rows', () => {
    render(<DailyPerformanceTable data={mockDailyData} isLoading={false} />);

    expect(screen.getByText('2026-01-01')).toBeInTheDocument();
    expect(screen.getByText('Complete (24h)')).toBeInTheDocument();
  });

  it('visibly distinguishes incomplete days with warning badge', () => {
    render(<DailyPerformanceTable data={mockDailyData} isLoading={false} />);

    expect(screen.getByText('2026-01-02')).toBeInTheDocument();
    expect(screen.getByText('Partial (12/24h)')).toBeInTheDocument();
    expect(screen.getByText('(-12h)')).toBeInTheDocument();
    expect(screen.getByText(/Days flagged as Partial indicate incomplete observation coverage/i)).toBeInTheDocument();
  });
});

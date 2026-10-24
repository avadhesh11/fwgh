/**
 * TypeScript API interfaces matching backend FastAPI schemas.
 */

export interface HealthResponse {
  status: string;
  version: string;
  data_loaded: boolean;
  fuelhh_records: number;
  windfor_records: number;
}

export interface ForecastVsActualItem {
  target_start_time: string;
  delivery_date: string;
  hour_index: number;
  cutoff_time: string;
  publish_time: string;
  lead_time_hours: number;
  forecast_mw: number;
  actual_mw: number;
  error_mw: number;
  abs_error_mw: number;
  percentage_error: number | null;
}

export interface ForecastVsActualResponse {
  scope: string | null;
  start_date: string;
  end_date: string;
  cutoff_time: string;
  expected_intervals: number;
  matched_intervals: number;
  coverage_pct: number;
  data: ForecastVsActualItem[];
}

export interface MetricsResponse {
  scope: string | null;
  start_date: string;
  end_date: string;
  cutoff_time: string;
  expected_intervals: number;
  matched_intervals: number;
  missing_forecasts: number;
  missing_actuals: number;
  coverage_pct: number;
  mae_mw: number | null;
  rmse_mw: number | null;
  bias_mw: number | null;
  p50_abs_error_mw: number | null;
  p90_abs_error_mw: number | null;
  p99_abs_error_mw: number | null;
  max_abs_error_mw: number | null;
  min_lead_time_hours: number | null;
  max_lead_time_hours: number | null;
  avg_lead_time_hours: number | null;
}

export interface ErrorByHorizonItem {
  lead_time_hours: number;
  count: number;
  avg_forecast_mw: number;
  avg_actual_mw: number;
  mae_mw: number;
  rmse_mw: number;
  bias_mw: number;
  p90_abs_error_mw: number;
  max_abs_error_mw: number;
}

export interface ErrorByHourItem {
  hour_of_day: number;
  settlement_periods: [number, number];
  count: number;
  avg_forecast_mw: number;
  avg_actual_mw: number;
  mae_mw: number;
  rmse_mw: number;
  bias_mw: number;
  p90_abs_error_mw: number;
  lead_time_hours: number;
}

export interface DailyErrorItem {
  delivery_date: string;
  expected_hours: number;
  matched_hours: number;
  missing_hours: number;
  is_complete: boolean;
  daily_coverage_pct: number;
  avg_forecast_mw?: number | null;
  avg_actual_mw?: number | null;
  daily_mae_mw?: number | null;
  daily_rmse_mw?: number | null;
  daily_bias_mw?: number | null;
  daily_max_abs_error_mw?: number | null;
  daily_energy_forecast_mwh?: number | null;
  daily_energy_actual_mwh?: number | null;
}

export interface FilterParams {
  scope?: "A" | "B";
  start_date?: string;
  end_date?: string;
  cutoff_time?: string;
}

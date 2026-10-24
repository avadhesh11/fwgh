import { useState, useEffect, useRef, useCallback } from 'react';
import { apiService } from './services/api';
import type {
  HealthResponse,
  MetricsResponse,
  ForecastVsActualItem,
  ErrorByHorizonItem,
  ErrorByHourItem,
  DailyErrorItem,
  FilterParams
} from './types/api';

import { Header } from './components/Header';
import { FilterBar } from './components/FilterBar';
import { KPICards } from './components/KPICards';
import { ForecastActualChart } from './components/ForecastActualChart';
import { ErrorByHorizonChart } from './components/ErrorByHorizonChart';
import { ErrorByHourChart } from './components/ErrorByHourChart';
import { DailyPerformanceTable } from './components/DailyPerformanceTable';
import { ErrorAlert } from './components/ErrorAlert';

export function App() {
  const [filters, setFilters] = useState<FilterParams>({
    scope: 'B',
    cutoff_time: '09:00',
    start_date: '2026-01-02',
    end_date: '2026-02-01',
  });

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);

  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [forecastActualData, setForecastActualData] = useState<ForecastVsActualItem[]>([]);
  const [horizonData, setHorizonData] = useState<ErrorByHorizonItem[]>([]);
  const [hourData, setHourData] = useState<ErrorByHourItem[]>([]);
  const [dailyData, setDailyData] = useState<DailyErrorItem[]>([]);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  // Fetch health check on mount
  const checkHealth = useCallback(async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const h = await apiService.getHealth();
      setHealth(h);
    } catch (err: any) {
      setHealthError(err.message || 'Failed to connect to backend service');
    } finally {
      setHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  // Fetch all dashboard data when filters change
  const loadDashboardData = useCallback(async (currentFilters: FilterParams) => {
    // Abort previous in-flight requests to prevent stale responses
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsLoading(true);
    setError(null);

    try {
      const [metricsRes, fvaRes, horizonRes, hourRes, dailyRes] = await Promise.all([
        apiService.getMetrics(currentFilters, controller.signal),
        apiService.getForecastVsActual(currentFilters, controller.signal),
        apiService.getErrorByHorizon(currentFilters, controller.signal),
        apiService.getErrorByHour(currentFilters, controller.signal),
        apiService.getDailyErrors(currentFilters, controller.signal),
      ]);

      setMetrics(metricsRes);
      setForecastActualData(fvaRes.data);
      setHorizonData(horizonRes);
      setHourData(hourRes);
      setDailyData(dailyRes);
    } catch (err: any) {
      if (err.name === 'AbortError') {
        // Request was cancelled by a newer filter change; ignore
        return;
      }
      setError(err.message || 'An error occurred while fetching dashboard analytics.');
      setMetrics(null);
      setForecastActualData([]);
      setHorizonData([]);
      setHourData([]);
      setDailyData([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData(filters);

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [filters, loadDashboardData]);

  const handleFilterChange = (newFilters: FilterParams) => {
    setFilters(newFilters);
  };

  const handleRefresh = () => {
    checkHealth();
    loadDashboardData(filters);
  };

  return (
    <div className="dashboard-container">
      <Header
        health={health}
        healthLoading={healthLoading}
        healthError={healthError}
      />

      <FilterBar
        filters={filters}
        onFilterChange={handleFilterChange}
        onRefresh={handleRefresh}
        isLoading={isLoading}
      />

      {error && (
        <ErrorAlert message={error} onRetry={handleRefresh} />
      )}

      {/* Primary KPI Summary Cards */}
      <KPICards metrics={metrics} isLoading={isLoading} />

      {/* Main Forecast vs Actual Time-series Chart */}
      <ForecastActualChart data={forecastActualData} isLoading={isLoading} />

      {/* 2-Column Analytical Layout: Horizon Error & Diurnal Profile */}
      <div className="dashboard-grid-2">
        <ErrorByHorizonChart data={horizonData} isLoading={isLoading} />
        <ErrorByHourChart data={hourData} isLoading={isLoading} />
      </div>

      {/* Daily Performance & Completeness Breakdown */}
      <DailyPerformanceTable data={dailyData} isLoading={isLoading} />

      {/* Analytical Methodology Footer */}
      <footer style={{ borderTop: '1px solid #1e293b', paddingTop: '16px', color: '#64748b', fontSize: '0.78rem', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: '12px' }}>
        <div>
          <strong>Methodology Note:</strong> Actuals are aggregated from half-hourly FUELHH using arithmetic mean (P1 + P2)/2 in MW. Errors defined as Forecast − Actual. Positive bias indicates overforecasting.
        </div>
        <div>
          Data Source: Elexon BMRS API (FUELHH/stream & WINDFOR/stream) • Pilot Cutoff: 09:00 UK local time on D-1
        </div>
      </footer>
    </div>
  );
}

export default App;

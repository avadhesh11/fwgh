import React from 'react';
import { Target, TrendingUp, AlertTriangle, CheckCircle2, Clock, Zap } from 'lucide-react';
import type { MetricsResponse } from '../types/api';

interface KPICardsProps {
  metrics: MetricsResponse | null;
  isLoading: boolean;
}

export const KPICards: React.FC<KPICardsProps> = ({ metrics, isLoading }) => {
  if (isLoading && !metrics) {
    return (
      <div className="kpi-grid">
        {[1, 2, 3, 4, 5, 6].map(i => (
          <div key={i} className="kpi-card" style={{ height: '140px', opacity: 0.5 }}>
            <div className="spinner" style={{ margin: 'auto' }} />
          </div>
        ))}
      </div>
    );
  }

  const hasNoData = metrics && metrics.matched_intervals === 0;

  const getBiasLabel = () => {
    if (!metrics || metrics.bias_mw === null || metrics.bias_mw === undefined) return 'No data';
    if (metrics.bias_mw > 0) return '▲ Persistent Overforecast (F > Actual)';
    if (metrics.bias_mw < 0) return '▼ Underforecast (F < Actual)';
    return 'Zero Bias (F = Actual)';
  };

  const getBiasColor = () => {
    if (!metrics || metrics.bias_mw === null || metrics.bias_mw === undefined) return '#94a3b8';
    if (metrics.bias_mw > 0) return '#f59e0b';
    if (metrics.bias_mw < 0) return '#38bdf8';
    return '#10b981';
  };

  return (
    <>
      {hasNoData && (
        <div
          role="alert"
          style={{
            background: 'rgba(245, 158, 11, 0.1)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            borderRadius: '8px',
            padding: '12px 16px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            color: '#fbbf24',
            fontSize: '0.9rem',
          }}
        >
          <AlertTriangle size={18} />
          <span>
            <strong>No matched data available for this selection.</strong> (0 of {metrics?.expected_intervals} target intervals matched). Defined metrics are shown as &mdash;.
          </span>
        </div>
      )}

      <div className="kpi-grid">
        {/* 1. MAE */}
        <div className="kpi-card cyan">
          <div className="kpi-header">
            <span className="kpi-title">Mean Absolute Error</span>
            <Target size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value-area">
            <span className="kpi-value">
              {metrics && metrics.mae_mw !== null && metrics.mae_mw !== undefined
                ? metrics.mae_mw.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })
                : '—'}
            </span>
            <span className="kpi-unit">MW</span>
          </div>
          <div className="kpi-footer">
            Average magnitude of hourly forecast deviation
          </div>
        </div>

        {/* 2. RMSE */}
        <div className="kpi-card blue">
          <div className="kpi-header">
            <span className="kpi-title">Root Mean Squared Error</span>
            <Zap size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value-area">
            <span className="kpi-value">
              {metrics && metrics.rmse_mw !== null && metrics.rmse_mw !== undefined
                ? metrics.rmse_mw.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })
                : '—'}
            </span>
            <span className="kpi-unit">MW</span>
          </div>
          <div className="kpi-footer">
            Penalizes large outlier forecast errors heavily
          </div>
        </div>

        {/* 3. Bias */}
        <div className="kpi-card amber">
          <div className="kpi-header">
            <span className="kpi-title">Mean Bias (Signed)</span>
            <TrendingUp size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value-area">
            <span className="kpi-value" style={{ color: getBiasColor() }}>
              {metrics && metrics.bias_mw !== null && metrics.bias_mw !== undefined
                ? `${metrics.bias_mw > 0 ? '+' : ''}${metrics.bias_mw.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}`
                : '—'}
            </span>
            <span className="kpi-unit">MW</span>
          </div>
          <div className="kpi-footer" style={{ color: getBiasColor() }}>
            {getBiasLabel()}
          </div>
        </div>

        {/* 4. P90 Absolute Error */}
        <div className="kpi-card purple">
          <div className="kpi-header">
            <span className="kpi-title">P90 Absolute Error</span>
            <AlertTriangle size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value-area">
            <span className="kpi-value">
              {metrics && metrics.p90_abs_error_mw !== null && metrics.p90_abs_error_mw !== undefined
                ? metrics.p90_abs_error_mw.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })
                : '—'}
            </span>
            <span className="kpi-unit">MW</span>
          </div>
          <div className="kpi-footer">
            P50: {metrics && metrics.p50_abs_error_mw !== null && metrics.p50_abs_error_mw !== undefined ? `${metrics.p50_abs_error_mw.toLocaleString()} MW` : '—'} • Max: {metrics && metrics.max_abs_error_mw !== null && metrics.max_abs_error_mw !== undefined ? `${metrics.max_abs_error_mw.toLocaleString()} MW` : '—'}
          </div>
        </div>

        {/* 5. Coverage */}
        <div className="kpi-card emerald">
          <div className="kpi-header">
            <span className="kpi-title">Interval Coverage</span>
            <CheckCircle2 size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value-area">
            <span className="kpi-value">{metrics ? `${metrics.coverage_pct.toFixed(1)}%` : '—'}</span>
          </div>
          <div className="kpi-footer">
            {metrics ? `${metrics.matched_intervals} / ${metrics.expected_intervals} target hours matched` : '—'}
          </div>
        </div>

        {/* 6. Lead Time */}
        <div className="kpi-card cyan">
          <div className="kpi-header">
            <span className="kpi-title">Average Lead Time</span>
            <Clock size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value-area">
            <span className="kpi-value">
              {metrics && metrics.avg_lead_time_hours !== null && metrics.avg_lead_time_hours !== undefined
                ? `${metrics.avg_lead_time_hours.toFixed(1)}`
                : '—'}
            </span>
            <span className="kpi-unit">Hours</span>
          </div>
          <div className="kpi-footer">
            Range: {metrics && metrics.min_lead_time_hours !== null && metrics.max_lead_time_hours !== null
              ? `${metrics.min_lead_time_hours}h to ${metrics.max_lead_time_hours}h`
              : '—'}
          </div>
        </div>
      </div>
    </>
  );
};

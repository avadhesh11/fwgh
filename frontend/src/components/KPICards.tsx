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

  const isOverforecast = (metrics?.bias_mw || 0) > 0;

  return (
    <div className="kpi-grid">
      {/* 1. MAE */}
      <div className="kpi-card cyan">
        <div className="kpi-header">
          <span className="kpi-title">Mean Absolute Error</span>
          <Target size={18} className="kpi-icon" />
        </div>
        <div className="kpi-value-area">
          <span className="kpi-value">{metrics ? metrics.mae_mw.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : '—'}</span>
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
          <span className="kpi-value">{metrics ? metrics.rmse_mw.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : '—'}</span>
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
          <span className="kpi-value" style={{ color: isOverforecast ? '#f59e0b' : '#38bdf8' }}>
            {metrics ? `${metrics.bias_mw > 0 ? '+' : ''}${metrics.bias_mw.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}` : '—'}
          </span>
          <span className="kpi-unit">MW</span>
        </div>
        <div className="kpi-footer" style={{ color: '#f59e0b' }}>
          {isOverforecast ? '▲ Persistent Overforecast (F > Actual)' : '▼ Underforecast (F < Actual)'}
        </div>
      </div>

      {/* 4. P90 Absolute Error */}
      <div className="kpi-card purple">
        <div className="kpi-header">
          <span className="kpi-title">P90 Absolute Error</span>
          <AlertTriangle size={18} className="kpi-icon" />
        </div>
        <div className="kpi-value-area">
          <span className="kpi-value">{metrics ? metrics.p90_abs_error_mw.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : '—'}</span>
          <span className="kpi-unit">MW</span>
        </div>
        <div className="kpi-footer">
          P50: {metrics?.p50_abs_error_mw?.toLocaleString() || '—'} MW • Max: {metrics?.max_abs_error_mw?.toLocaleString() || '—'} MW
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
          <span className="kpi-value">{metrics ? `${metrics.avg_lead_time_hours.toFixed(1)}` : '—'}</span>
          <span className="kpi-unit">Hours</span>
        </div>
        <div className="kpi-footer">
          Range: {metrics ? `${metrics.min_lead_time_hours}h to ${metrics.max_lead_time_hours}h` : '—'}
        </div>
      </div>
    </div>
  );
};

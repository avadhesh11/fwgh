import React from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts';
import type { ErrorByHorizonItem } from '../types/api';

interface ErrorByHorizonChartProps {
  data: ErrorByHorizonItem[];
  isLoading: boolean;
}

export const ErrorByHorizonChart: React.FC<ErrorByHorizonChartProps> = ({ data, isLoading }) => {
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const item: ErrorByHorizonItem = payload[0].payload;
      const isEmpty = item.count === 0;

      return (
        <div className="custom-tooltip">
          <div className="tooltip-header">
            Horizon: {item.horizon_bucket}
          </div>
          {isEmpty ? (
            <div className="tooltip-row" style={{ color: '#94a3b8', fontStyle: 'italic' }}>
              No forecast observations in this lead-time window
            </div>
          ) : (
            <>
              {item.avg_lead_time_hours !== null && item.avg_lead_time_hours !== undefined && (
                <div className="tooltip-row">
                  <span style={{ color: '#94a3b8' }}>Avg Lead Time:</span>
                  <strong>{item.avg_lead_time_hours.toFixed(1)} Hours</strong>
                </div>
              )}
              <div className="tooltip-row">
                <span style={{ color: '#38bdf8' }}>MAE:</span>
                <strong>{item.mae_mw !== null ? `${item.mae_mw.toLocaleString()} MW` : '—'}</strong>
              </div>
              <div className="tooltip-row">
                <span style={{ color: '#f59e0b' }}>Signed Bias:</span>
                <strong style={{ color: item.bias_mw !== null && item.bias_mw > 0 ? '#f59e0b' : '#38bdf8' }}>
                  {item.bias_mw !== null ? `${item.bias_mw > 0 ? '+' : ''}${item.bias_mw.toLocaleString()} MW` : '—'}
                </strong>
              </div>
              {item.p90_abs_error_mw !== null && (
                <div className="tooltip-row">
                  <span style={{ color: '#8b5cf6' }}>P90 Abs Error:</span>
                  <strong>{item.p90_abs_error_mw.toLocaleString()} MW</strong>
                </div>
              )}
              <div className="tooltip-row">
                <span style={{ color: '#94a3b8' }}>Sample Count:</span>
                <span>{item.count} intervals</span>
              </div>
            </>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-card">
      <div className="chart-header">
        <div className="chart-title-area">
          <h3 className="chart-title">Forecast Error by Lead Time Horizon</h3>
          <span className="chart-subtitle">
            Operational lead-time intervals: (delivery start − publication time). Evaluates error as forecast horizon expands.
          </span>
        </div>

        <div className="chart-legend-custom">
          <div className="legend-item">
            <div className="legend-dot" style={{ backgroundColor: '#0284c7' }} />
            <span>MAE (MW)</span>
          </div>
          <div className="legend-item">
            <div className="legend-dot" style={{ backgroundColor: '#f59e0b' }} />
            <span>Bias (MW)</span>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="loading-box">
          <div className="spinner" />
          <span>Computing horizon error distributions...</span>
        </div>
      ) : !data.length ? (
        <div className="loading-box">
          <span>No horizon data available.</span>
        </div>
      ) : (
        <div style={{ width: '100%', height: 320 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis
                dataKey="horizon_bucket"
                stroke="#64748b"
                tick={{ fontSize: 11 }}
              />
              <YAxis
                stroke="#64748b"
                tickFormatter={(val: number) => `${(val / 1000).toFixed(1)}k`}
                tick={{ fontSize: 11 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="mae_mw" fill="#0284c7" radius={[4, 4, 0, 0]} name="MAE" />
              <Line
                type="monotone"
                dataKey="bias_mw"
                stroke="#f59e0b"
                strokeWidth={2}
                dot={{ r: 3, fill: '#f59e0b' }}
                name="Bias"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

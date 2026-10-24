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
import type { ErrorByHourItem } from '../types/api';

interface ErrorByHourChartProps {
  data: ErrorByHourItem[];
  isLoading: boolean;
}

export const ErrorByHourChart: React.FC<ErrorByHourChartProps> = ({ data, isLoading }) => {
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const item: ErrorByHourItem = payload[0].payload;
      return (
        <div className="custom-tooltip">
          <div className="tooltip-header">
            Hour {item.hour_of_day}:00 UTC (Settlement Periods {item.settlement_periods[0]}&{item.settlement_periods[1]})
          </div>
          <div className="tooltip-row">
            <span style={{ color: '#38bdf8' }}>Avg Forecast:</span>
            <strong>{item.avg_forecast_mw.toLocaleString()} MW</strong>
          </div>
          <div className="tooltip-row">
            <span style={{ color: '#10b981' }}>Avg Actual:</span>
            <strong>{item.avg_actual_mw.toLocaleString()} MW</strong>
          </div>
          <div className="tooltip-row" style={{ borderTop: '1px solid #1c263c', paddingTop: '4px' }}>
            <span style={{ color: '#f59e0b' }}>MAE:</span>
            <strong>{item.mae_mw.toLocaleString()} MW</strong>
          </div>
          <div className="tooltip-row">
            <span style={{ color: '#f59e0b' }}>Signed Bias:</span>
            <strong style={{ color: item.bias_mw > 0 ? '#f59e0b' : '#38bdf8' }}>
              {item.bias_mw > 0 ? '+' : ''}{item.bias_mw.toLocaleString()} MW
            </strong>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-card">
      <div className="chart-header">
        <div className="chart-title-area">
          <h3 className="chart-title">Diurnal Error Profile by Hour of Day</h3>
          <span className="chart-subtitle">
            Systematic hourly pattern across the 24 delivery hours (Settlement Periods 1 to 48)
          </span>
        </div>

        <div className="chart-legend-custom">
          <div className="legend-item">
            <div className="legend-dot" style={{ backgroundColor: '#0ea5e9' }} />
            <span>Hourly MAE</span>
          </div>
          <div className="legend-item">
            <div className="legend-dot" style={{ backgroundColor: '#10b981' }} />
            <span>Actual Gen</span>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="loading-box">
          <div className="spinner" />
          <span>Computing diurnal hourly metrics...</span>
        </div>
      ) : !data.length ? (
        <div className="loading-box">
          <span>No hourly data available.</span>
        </div>
      ) : (
        <div style={{ width: '100%', height: 320 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis
                dataKey="hour_of_day"
                tickFormatter={(val: number) => `${val}h`}
                stroke="#64748b"
                tick={{ fontSize: 11 }}
              />
              <YAxis
                stroke="#64748b"
                tickFormatter={(val: number) => `${(val / 1000).toFixed(1)}k`}
                tick={{ fontSize: 11 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="mae_mw" fill="#0ea5e9" radius={[4, 4, 0, 0]} name="MAE" />
              <Line
                type="monotone"
                dataKey="avg_actual_mw"
                stroke="#10b981"
                strokeWidth={2}
                dot={false}
                name="Avg Actual MW"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

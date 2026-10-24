import React, { useState, useMemo } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts';
import type { ForecastVsActualItem } from '../types/api';

interface ForecastActualChartProps {
  data: ForecastVsActualItem[];
  isLoading: boolean;
}

export const ForecastActualChart: React.FC<ForecastActualChartProps> = ({ data, isLoading }) => {
  const [slice, setSlice] = useState<'ALL' | 'W1' | 'W2' | 'W3' | 'W4' | 'W5'>('ALL');

  // Filter data by selected slice
  const filteredData = useMemo(() => {
    if (!data.length || slice === 'ALL') return data;
    if (slice === 'W1') return data.slice(0, 168);       // Days 1-7 (7*24 = 168)
    if (slice === 'W2') return data.slice(168, 336);     // Days 8-14
    if (slice === 'W3') return data.slice(336, 504);     // Days 15-21
    if (slice === 'W4') return data.slice(504, 672);     // Days 22-28
    if (slice === 'W5') return data.slice(672);          // Days 29-31
    return data;
  }, [data, slice]);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const item: ForecastVsActualItem = payload[0].payload;
      const isOver = item.error_mw > 0;
      return (
        <div className="custom-tooltip">
          <div className="tooltip-header">
            {item.delivery_date} • Hour {item.hour_index}:00 UTC
          </div>
          <div className="tooltip-row">
            <span style={{ color: '#38bdf8' }}>Forecast:</span>
            <strong>{item.forecast_mw.toLocaleString()} MW</strong>
          </div>
          <div className="tooltip-row">
            <span style={{ color: '#10b981' }}>Actual:</span>
            <strong>{item.actual_mw.toLocaleString()} MW</strong>
          </div>
          <div className="tooltip-row" style={{ borderTop: '1px solid #1c263c', paddingTop: '4px', marginTop: '4px' }}>
            <span style={{ color: isOver ? '#f59e0b' : '#8b5cf6' }}>Error (F - A):</span>
            <strong style={{ color: isOver ? '#f59e0b' : '#8b5cf6' }}>
              {item.error_mw > 0 ? '+' : ''}{item.error_mw.toLocaleString()} MW
            </strong>
          </div>
          <div className="tooltip-row">
            <span style={{ color: '#94a3b8' }}>Published:</span>
            <span>{item.publish_time.replace('T', ' ').slice(5, 16)} UTC</span>
          </div>
          <div className="tooltip-row">
            <span style={{ color: '#94a3b8' }}>Lead Time:</span>
            <span>{item.lead_time_hours} hours</span>
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
          <h2 className="chart-title">Forecast vs Actual Wind Generation</h2>
          <span className="chart-subtitle">
            Hourly WINDFOR forecast published on day D-1 before cutoff vs aggregated FUELHH generation outturn (MW)
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          <div className="chart-legend-custom">
            <div className="legend-item">
              <div className="legend-dot" style={{ backgroundColor: '#38bdf8' }} />
              <span>Forecast (WINDFOR)</span>
            </div>
            <div className="legend-item">
              <div className="legend-dot" style={{ backgroundColor: '#10b981' }} />
              <span>Actual (FUELHH)</span>
            </div>
          </div>

          <div className="slice-btn-group">
            <button
              type="button"
              className={`slice-btn ${slice === 'ALL' ? 'active' : ''}`}
              onClick={() => setSlice('ALL')}
            >
              All Month
            </button>
            <button
              type="button"
              className={`slice-btn ${slice === 'W1' ? 'active' : ''}`}
              onClick={() => setSlice('W1')}
            >
              W1
            </button>
            <button
              type="button"
              className={`slice-btn ${slice === 'W2' ? 'active' : ''}`}
              onClick={() => setSlice('W2')}
            >
              W2
            </button>
            <button
              type="button"
              className={`slice-btn ${slice === 'W3' ? 'active' : ''}`}
              onClick={() => setSlice('W3')}
            >
              W3
            </button>
            <button
              type="button"
              className={`slice-btn ${slice === 'W4' ? 'active' : ''}`}
              onClick={() => setSlice('W4')}
            >
              W4
            </button>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="loading-box">
          <div className="spinner" />
          <span>Loading time-series data...</span>
        </div>
      ) : !filteredData.length ? (
        <div className="loading-box">
          <span>No observations match the selected criteria.</span>
        </div>
      ) : (
        <div style={{ width: '100%', height: 380 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={filteredData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis
                dataKey="target_start_time"
                tickFormatter={(val: string) => {
                  const d = new Date(val);
                  return `${d.getUTCDate()}/${d.getUTCMonth()+1} ${d.getUTCHours()}:00`;
                }}
                stroke="#64748b"
                tick={{ fontSize: 11 }}
                minTickGap={40}
              />
              <YAxis
                stroke="#64748b"
                tickFormatter={(val: number) => `${(val / 1000).toFixed(0)}k`}
                tick={{ fontSize: 11 }}
                domain={[0, 'auto']}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="actual_mw"
                fill="rgba(16, 185, 129, 0.12)"
                stroke="#10b981"
                strokeWidth={2}
                name="Actual (FUELHH)"
              />
              <Line
                type="monotone"
                dataKey="forecast_mw"
                stroke="#38bdf8"
                strokeWidth={2}
                dot={false}
                name="Forecast (WINDFOR)"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

import React from 'react';
import { AlertCircle, CheckCircle, Calendar } from 'lucide-react';
import type { DailyErrorItem } from '../types/api';

interface DailyPerformanceTableProps {
  data: DailyErrorItem[];
  isLoading: boolean;
}

export const DailyPerformanceTable: React.FC<DailyPerformanceTableProps> = ({ data, isLoading }) => {
  return (
    <div className="chart-card">
      <div className="chart-header">
        <div className="chart-title-area">
          <h3 className="chart-title">Daily Forecast Accuracy & Energy Outturn</h3>
          <span className="chart-subtitle">
            Day-by-day verification of coverage, energy volume (MWh), and forecast error metrics
          </span>
        </div>
      </div>

      {isLoading ? (
        <div className="loading-box">
          <div className="spinner" />
          <span>Aggregating daily performance metrics...</span>
        </div>
      ) : !data.length ? (
        <div className="loading-box">
          <span>No daily data available.</span>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Delivery Date</th>
                <th>Status</th>
                <th>Coverage</th>
                <th>Forecast Energy</th>
                <th>Actual Energy</th>
                <th>Daily MAE</th>
                <th>Daily Bias</th>
                <th>Max Deviation</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => {
                const isOver = (row.daily_bias_mw ?? 0) > 0;
                return (
                  <tr key={row.delivery_date}>
                    <td style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Calendar size={13} style={{ color: '#64748b' }} />
                      {row.delivery_date}
                    </td>
                    <td>
                      {row.is_complete ? (
                        <span className="badge badge-success">
                          <CheckCircle size={10} />
                          Complete (24h)
                        </span>
                      ) : (
                        <span className="badge badge-warning">
                          <AlertCircle size={10} />
                          Partial ({row.matched_hours}/24h)
                        </span>
                      )}
                    </td>
                    <td>
                      <span style={{ fontWeight: 600 }}>{row.daily_coverage_pct}%</span>
                      {row.missing_hours > 0 && (
                        <span style={{ color: '#f59e0b', fontSize: '0.75rem', marginLeft: '4px' }}>
                          (-{row.missing_hours}h)
                        </span>
                      )}
                    </td>
                    <td>
                      {row.daily_energy_forecast_mwh != null ? (
                        <span style={{ color: row.is_complete ? 'inherit' : '#f59e0b' }}>
                          {row.daily_energy_forecast_mwh.toLocaleString()} MWh{!row.is_complete ? '*' : ''}
                        </span>
                      ) : (
                        <span>—</span>
                      )}
                    </td>
                    <td>
                      {row.daily_energy_actual_mwh != null ? (
                        <span style={{ color: row.is_complete ? 'inherit' : '#f59e0b' }}>
                          {row.daily_energy_actual_mwh.toLocaleString()} MWh{!row.is_complete ? '*' : ''}
                        </span>
                      ) : (
                        <span>—</span>
                      )}
                    </td>
                    <td style={{ fontWeight: 600 }}>
                      {row.daily_mae_mw != null ? `${row.daily_mae_mw.toLocaleString()} MW` : '—'}
                    </td>
                    <td style={{ color: row.daily_bias_mw == null ? '#94a3b8' : isOver ? '#f59e0b' : '#38bdf8', fontWeight: 600 }}>
                      {row.daily_bias_mw != null ? `${row.daily_bias_mw > 0 ? '+' : ''}${row.daily_bias_mw.toLocaleString()} MW` : '—'}
                    </td>
                    <td>
                      {row.daily_max_abs_error_mw != null ? `${row.daily_max_abs_error_mw.toLocaleString()} MW` : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div style={{ marginTop: '12px', fontSize: '0.76rem', color: '#64748b' }}>
            * Note: Days flagged as Partial indicate incomplete observation coverage; energy totals represent matched hours only and are not full 24-hour daily sums.
          </div>
        </div>
      )}
    </div>
  );
};

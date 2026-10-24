import React from 'react';
import { Wind, Activity } from 'lucide-react';
import type { HealthResponse } from '../types/api';

interface HeaderProps {
  health: HealthResponse | null;
  healthLoading: boolean;
  healthError: string | null;
}

export const Header: React.FC<HeaderProps> = ({ health, healthLoading, healthError }) => {
  return (
    <header className="dashboard-header">
      <div className="header-title-area">
        <div className="portal-badge">
          <Wind size={13} />
          Elexon BMRS Decision Audit Portal
        </div>
        <h1 className="header-title">
          Wind Forecast Decision Portal
        </h1>
        <p className="header-subtitle">
          Evaluates day-ahead wind generation forecasts available at the decision cutoff against actual metered generation across Great Britain.
        </p>
      </div>

      <div className="system-status">
        <Activity size={16} color={health?.data_loaded ? "#10b981" : "#ef4444"} />
        <div>
          {healthLoading ? (
            <span style={{ color: "#94a3b8" }}>Connecting to backend...</span>
          ) : healthError ? (
            <span style={{ color: "#ef4444" }}>Backend Offline</span>
          ) : (
            <span>
              <strong>API Connected</strong> • {health?.fuelhh_records.toLocaleString()} FUELHH • {health?.windfor_records.toLocaleString()} WINDFOR
            </span>
          )}
        </div>
        <div className={`status-dot ${health?.data_loaded ? '' : 'error'}`} />
      </div>
    </header>
  );
};

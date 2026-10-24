import React from 'react';
import { Calendar, Clock, RefreshCw } from 'lucide-react';
import type { FilterParams } from '../types/api';

interface FilterBarProps {
  filters: FilterParams;
  onFilterChange: (newFilters: FilterParams) => void;
  onRefresh: () => void;
  isLoading: boolean;
}

const COMMON_CUTOFFS = ["04:00", "07:00", "09:00", "12:00", "18:00"];

export const FilterBar: React.FC<FilterBarProps> = ({
  filters,
  onFilterChange,
  onRefresh,
  isLoading
}) => {
  const isScopeA = filters.start_date === '2026-01-01' && filters.end_date === '2026-01-31';
  const isScopeB = filters.start_date === '2026-01-02' && filters.end_date === '2026-02-01';
  const isCustom = !isScopeA && !isScopeB;
  const currentCutoff = filters.cutoff_time || '09:00';

  const handleScopeSelect = (scope: 'A' | 'B') => {
    if (scope === 'A') {
      onFilterChange({
        ...filters,
        scope: 'A',
        start_date: '2026-01-01',
        end_date: '2026-01-31',
      });
    } else {
      onFilterChange({
        ...filters,
        scope: 'B',
        start_date: '2026-01-02',
        end_date: '2026-02-01',
      });
    }
  };

  const handleCutoffSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onFilterChange({
      ...filters,
      cutoff_time: e.target.value
    });
  };

  const handleStartDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      ...filters,
      scope: undefined,
      start_date: e.target.value
    });
  };

  const handleEndDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      ...filters,
      scope: undefined,
      end_date: e.target.value
    });
  };

  return (
    <div className="filter-bar">
      <div className="filter-groups">
        {/* Scope Selector */}
        <div className="filter-group">
          <label className="filter-label">Evaluation Scope</label>
          <div className="scope-btn-group">
            <button
              type="button"
              className={`scope-btn ${isScopeA ? 'active' : ''}`}
              onClick={() => handleScopeSelect('A')}
            >
              Scope A (Delivery Jan 1–31)
            </button>
            <button
              type="button"
              className={`scope-btn ${isScopeB ? 'active' : ''}`}
              onClick={() => handleScopeSelect('B')}
            >
              Scope B (Decisions Jan 1–31)
            </button>
            {isCustom && (
              <span
                style={{
                  alignSelf: 'center',
                  padding: '4px 10px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  background: 'rgba(245, 158, 11, 0.15)',
                  color: '#fbbf24',
                  border: '1px solid rgba(245, 158, 11, 0.3)',
                  borderRadius: '6px',
                  marginLeft: '4px',
                }}
              >
                Custom range
              </span>
            )}
          </div>
        </div>

        {/* Cutoff Selector */}
        <div className="filter-group">
          <label htmlFor="cutoff-select" className="filter-label" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Clock size={12} />
            Decision Cutoff (D-1 UK)
          </label>
          <select
            id="cutoff-select"
            className="select-input"
            value={currentCutoff}
            onChange={handleCutoffSelect}
          >
            {COMMON_CUTOFFS.map(c => (
              <option key={c} value={c}>
                {c} UK {c === '09:00' ? '(Pilot Default)' : ''}
              </option>
            ))}
          </select>
        </div>

        {/* Date Range Inputs */}
        <div className="filter-group">
          <label className="filter-label" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Calendar size={12} />
            Delivery Dates (Supported: Jan 1 – Feb 1, 2026)
          </label>
          <div className="date-inputs">
            <input
              type="date"
              className="text-input"
              min="2026-01-01"
              max="2026-02-01"
              value={filters.start_date || '2026-01-02'}
              onChange={handleStartDateChange}
              aria-label="Start date"
            />
            <span style={{ color: '#64748b' }}>to</span>
            <input
              type="date"
              className="text-input"
              min="2026-01-01"
              max="2026-02-01"
              value={filters.end_date || '2026-02-01'}
              onChange={handleEndDateChange}
              aria-label="End date"
            />
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button
          type="button"
          className="refresh-btn"
          onClick={onRefresh}
          disabled={isLoading}
        >
          <RefreshCw size={14} className={isLoading ? 'spinner' : ''} style={{ animationDuration: '0.8s' }} />
          Refresh
        </button>
      </div>
    </div>
  );
};

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
  const currentScope = filters.scope || 'A';
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
      start_date: e.target.value
    });
  };

  const handleEndDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      ...filters,
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
              className={`scope-btn ${currentScope === 'A' ? 'active' : ''}`}
              onClick={() => handleScopeSelect('A')}
            >
              Scope A (Delivery Jan 1–31)
            </button>
            <button
              type="button"
              className={`scope-btn ${currentScope === 'B' ? 'active' : ''}`}
              onClick={() => handleScopeSelect('B')}
            >
              Scope B (Decisions Jan 1–31)
            </button>
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
            Delivery Dates
          </label>
          <div className="date-inputs">
            <input
              type="date"
              className="text-input"
              value={filters.start_date || (currentScope === 'A' ? '2026-01-01' : '2026-01-02')}
              onChange={handleStartDateChange}
            />
            <span style={{ color: '#64748b' }}>to</span>
            <input
              type="date"
              className="text-input"
              value={filters.end_date || (currentScope === 'A' ? '2026-01-31' : '2026-02-01')}
              onChange={handleEndDateChange}
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

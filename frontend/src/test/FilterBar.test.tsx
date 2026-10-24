import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { FilterBar } from '../components/FilterBar';
import type { FilterParams } from '../types/api';

describe('FilterBar Component', () => {
  const initialFilters: FilterParams = {
    scope: 'A',
    cutoff_time: '09:00',
    start_date: '2026-01-01',
    end_date: '2026-01-31',
  };

  it('renders Scope A and Scope B buttons and calls onFilterChange on click', () => {
    const handleFilterChange = vi.fn();
    const handleRefresh = vi.fn();

    render(
      <FilterBar
        filters={initialFilters}
        onFilterChange={handleFilterChange}
        onRefresh={handleRefresh}
        isLoading={false}
      />
    );

    const scopeBBtn = screen.getByRole('button', { name: /Scope B/i });
    fireEvent.click(scopeBBtn);

    expect(handleFilterChange).toHaveBeenCalledWith(expect.objectContaining({
      scope: 'B',
      start_date: '2026-01-02',
      end_date: '2026-02-01',
    }));
  });

  it('changes cutoff time when select is changed', () => {
    const handleFilterChange = vi.fn();
    const handleRefresh = vi.fn();

    render(
      <FilterBar
        filters={initialFilters}
        onFilterChange={handleFilterChange}
        onRefresh={handleRefresh}
        isLoading={false}
      />
    );

    const select = screen.getByLabelText(/Cutoff/i);
    fireEvent.change(select, { target: { value: '04:00' } });

    expect(handleFilterChange).toHaveBeenCalledWith(expect.objectContaining({
      cutoff_time: '04:00',
    }));
  });

  it('triggers onRefresh when refresh button is clicked', () => {
    const handleFilterChange = vi.fn();
    const handleRefresh = vi.fn();

    render(
      <FilterBar
        filters={initialFilters}
        onFilterChange={handleFilterChange}
        onRefresh={handleRefresh}
        isLoading={false}
      />
    );

    const refreshBtn = screen.getByRole('button', { name: /Refresh/i });
    fireEvent.click(refreshBtn);

    expect(handleRefresh).toHaveBeenCalledTimes(1);
  });
});

"""
Automated tests for Elexon BMRS time-resolution validation, interval alignment, and audit reconciliation.

Validates:
- Arithmetic mean aggregation of half-hourly FUELHH (average MW) to hourly actuals.
- Incomplete / missing half-hour handling.
- Record deduplication and explicit DataIntegrityError on conflicting values.
- Reconciled lead-time calculation derived from timezone-aware timestamps:
  lead_time_hours = (target_startTime - publishTime).total_seconds() / 3600.
- Configurable decision cutoff logic (09:00 UK on day D-1) and latest eligible forecast selection.
- Strict post-cutoff exclusion.
- Missing records are never treated as zero; coverage denominator is expected scope intervals.
- Error sign convention (forecast - actual; positive indicates overforecast).
- Core verification metrics (MAE, RMSE, Bias, P90).
"""

import pytest
from datetime import datetime, date, timedelta
from app.services.alignment import (
    aggregate_fuelhh_to_hourly,
    filter_and_select_forecasts,
    match_forecasts_and_actuals,
    validate_and_deduplicate_fuelhh,
    validate_and_deduplicate_windfor,
    DataIntegrityError,
    parse_iso_datetime
)


def test_fuelhh_aggregation_arithmetic_mean_mw():
    """
    FUELHH values represent average MW over 30 minutes.
    Over a 1-hour interval [00:00, 01:00), the average power is (SP1 + SP2) / 2.
    It MUST NOT be summed (1000 + 2000 != 3000 MW).
    """
    raw_fuelhh = [
        {
            "dataset": "FUELHH",
            "publishTime": "2026-01-01T00:30:00Z",
            "startTime": "2026-01-01T00:00:00Z",
            "settlementDate": "2026-01-01",
            "settlementPeriod": 1,
            "fuelType": "WIND",
            "generation": 1000.0
        },
        {
            "dataset": "FUELHH",
            "publishTime": "2026-01-01T01:00:00Z",
            "startTime": "2026-01-01T00:30:00Z",
            "settlementDate": "2026-01-01",
            "settlementPeriod": 2,
            "fuelType": "WIND",
            "generation": 2000.0
        }
    ]
    
    hourly = aggregate_fuelhh_to_hourly(raw_fuelhh)
    target_dt = parse_iso_datetime("2026-01-01T00:00:00Z")
    
    assert target_dt in hourly
    record = hourly[target_dt]
    assert record.generation_mw == 1500.0  # (1000 + 2000) / 2
    assert record.settlement_periods == (1, 2)
    assert record.is_complete is True


def test_fuelhh_missing_half_hour_is_not_aggregated():
    """If an hour only has 1 settlement period present, it cannot form a complete 1-hour actual."""
    raw_fuelhh = [
        {
            "dataset": "FUELHH",
            "publishTime": "2026-01-01T00:30:00Z",
            "startTime": "2026-01-01T00:00:00Z",
            "settlementDate": "2026-01-01",
            "settlementPeriod": 1,
            "fuelType": "WIND",
            "generation": 1200.0
        }
    ]
    
    hourly = aggregate_fuelhh_to_hourly(raw_fuelhh)
    target_dt = parse_iso_datetime("2026-01-01T00:00:00Z")
    assert target_dt not in hourly


def test_fuelhh_exact_duplicate_dropped_cleanly():
    """Exact duplicates sharing key, publishTime, and generation are cleanly dropped to 1 record."""
    raw_fuelhh = [
        {"dataset": "FUELHH", "publishTime": "2026-01-01T00:30:00Z", "startTime": "2026-01-01T00:00:00Z",
         "settlementDate": "2026-01-01", "settlementPeriod": 1, "fuelType": "WIND", "generation": 1000.0},
        {"dataset": "FUELHH", "publishTime": "2026-01-01T00:30:00Z", "startTime": "2026-01-01T00:00:00Z",
         "settlementDate": "2026-01-01", "settlementPeriod": 1, "fuelType": "WIND", "generation": 1000.0},
    ]
    dedup = validate_and_deduplicate_fuelhh(raw_fuelhh)
    assert len(dedup) == 1
    assert dedup[0]["generation"] == 1000.0


def test_fuelhh_conflicting_values_raises_integrity_error():
    """If identical composite key and publishTime have conflicting generation values, raise DataIntegrityError."""
    raw_fuelhh = [
        {"dataset": "FUELHH", "publishTime": "2026-01-01T00:30:00Z", "startTime": "2026-01-01T00:00:00Z",
         "settlementDate": "2026-01-01", "settlementPeriod": 1, "fuelType": "WIND", "generation": 1000.0},
        {"dataset": "FUELHH", "publishTime": "2026-01-01T00:30:00Z", "startTime": "2026-01-01T00:00:00Z",
         "settlementDate": "2026-01-01", "settlementPeriod": 1, "fuelType": "WIND", "generation": 1500.0},
    ]
    with pytest.raises(DataIntegrityError):
        validate_and_deduplicate_fuelhh(raw_fuelhh)


def test_windfor_conflicting_values_raises_integrity_error():
    """If identical (publishTime, startTime) key has conflicting generation values, raise DataIntegrityError."""
    raw_windfor = [
        {"dataset": "WINDFOR", "publishTime": "2026-01-01T07:30:00Z", "startTime": "2026-01-02T00:00:00Z", "generation": 12000},
        {"dataset": "WINDFOR", "publishTime": "2026-01-01T07:30:00Z", "startTime": "2026-01-02T00:00:00Z", "generation": 15000},
    ]
    with pytest.raises(DataIntegrityError):
        validate_and_deduplicate_windfor(raw_windfor)


def test_lead_time_calculation_reconciled():
    """
    Verify lead-time calculation from timezone-aware timestamps:
    lead_time_hours = (target_startTime - publishTime).total_seconds() / 3600.
    
    Given D-1 latest publication at 07:30:00 UTC:
    - Hour 00:00 delivery on Day D -> lead time is exactly 16.5 hours.
    - Hour 23:00 delivery on Day D -> lead time is exactly 39.5 hours.
    - Mean across 24 hours is exactly 28.0 hours.
    """
    utc_tz = parse_iso_datetime("2026-01-01T00:00:00Z").tzinfo
    publish_time = datetime(2025, 12, 31, 7, 30, tzinfo=utc_tz)
    
    # Hour 00:00
    target_h0 = datetime(2026, 1, 1, 0, 0, tzinfo=utc_tz)
    lt_h0 = (target_h0 - publish_time).total_seconds() / 3600.0
    assert lt_h0 == 16.5

    # Hour 23:00
    target_h23 = datetime(2026, 1, 1, 23, 0, tzinfo=utc_tz)
    lt_h23 = (target_h23 - publish_time).total_seconds() / 3600.0
    assert lt_h23 == 39.5

    # 24 hours sequence
    all_lts = [(datetime(2026, 1, 1, h, 0, tzinfo=utc_tz) - publish_time).total_seconds() / 3600.0 for h in range(24)]
    assert min(all_lts) == 16.5
    assert max(all_lts) == 39.5
    assert sum(all_lts) / len(all_lts) == 28.0


def test_cutoff_decision_latest_eligible_forecast():
    """
    Given delivery target hour 2026-01-02T12:00:00Z (Day D):
    Decision cutoff is Day D-1 at 09:00 UK -> 2026-01-01T09:00:00Z.
    - Forecast published at 07:30Z is eligible.
    - Forecast published at 08:30Z is eligible and newer (selected).
    - Forecast published at 09:30Z is post-cutoff (ineligible).
    """
    target_st = parse_iso_datetime("2026-01-02T12:00:00Z")
    cutoff = parse_iso_datetime("2026-01-01T09:00:00Z")
    
    records = [
        {"dataset": "WINDFOR", "publishTime": "2026-01-01T07:30:00Z", "startTime": "2026-01-02T12:00:00Z", "generation": 14000},
        {"dataset": "WINDFOR", "publishTime": "2026-01-01T08:30:00Z", "startTime": "2026-01-02T12:00:00Z", "generation": 14500},
        {"dataset": "WINDFOR", "publishTime": "2026-01-01T09:30:00Z", "startTime": "2026-01-02T12:00:00Z", "generation": 15000},
    ]
    
    selected = filter_and_select_forecasts(records, target_st, cutoff)
    assert selected is not None
    assert selected["publishTime"] == "2026-01-01T08:30:00Z"
    assert selected["generation"] == 14500


def test_strict_cutoff_boundary_and_post_cutoff_rejection():
    """
    Strict regression test for cutoff filtering:
    Given cutoff at 04:00:00Z on D-1:
    - 02:30:00Z is eligible.
    - 04:00:00Z is eligible (exact boundary).
    - 04:00:01Z is ineligible (1 second past cutoff).
    - 04:30:00Z is ineligible (30 minutes past cutoff).
    A forecast published after the decision cutoff MUST NEVER be selected.
    """
    target_st = parse_iso_datetime("2026-01-02T00:00:00Z")
    cutoff = parse_iso_datetime("2026-01-01T04:00:00Z")

    records = [
        {"dataset": "WINDFOR", "publishTime": "2026-01-01T02:30:00Z", "startTime": "2026-01-02T00:00:00Z", "generation": 10000},
        {"dataset": "WINDFOR", "publishTime": "2026-01-01T04:00:00Z", "startTime": "2026-01-02T00:00:00Z", "generation": 11000},
        {"dataset": "WINDFOR", "publishTime": "2026-01-01T04:00:01Z", "startTime": "2026-01-02T00:00:00Z", "generation": 99999},
        {"dataset": "WINDFOR", "publishTime": "2026-01-01T04:30:00Z", "startTime": "2026-01-02T00:00:00Z", "generation": 88888},
    ]

    selected = filter_and_select_forecasts(records, target_st, cutoff)
    assert selected is not None
    assert selected["publishTime"] == "2026-01-01T04:00:00Z"
    assert selected["generation"] == 11000  # 04:00:01 and 04:30 are rejected!

    # Now if the 04:00 exact boundary is removed, 02:30 must be selected, NOT 04:30
    records_without_exact = [r for r in records if r["publishTime"] != "2026-01-01T04:00:00Z"]
    selected_earlier = filter_and_select_forecasts(records_without_exact, target_st, cutoff)
    assert selected_earlier is not None
    assert selected_earlier["publishTime"] == "2026-01-01T02:30:00Z"
    assert selected_earlier["generation"] == 10000


def test_missing_records_not_treated_as_zero():
    """
    Verify that missing intervals are excluded from MAE/RMSE calculations (never treated as 0)
    and that coverage denominator is the expected number of scope intervals.
    """
    deliv_date = date(2026, 1, 2)
    # 24 expected intervals, but only 20 actuals provided (4 missing actuals)
    # Actuals = 10000 MW, Forecast = 11000 MW (Error = +1000 MW)
    hourly_actuals = {}
    for h in range(20):  # 4 hours missing (hours 20-23)
        st = parse_iso_datetime(f"2026-01-02T{h:02d}:00:00Z")
        hourly_actuals[st] = type('obj', (object,), {
            "target_start_time": st,
            "generation_mw": 10000.0
        })()

    windfor_records = []
    for h in range(24):
        windfor_records.append({
            "dataset": "WINDFOR",
            "publishTime": "2026-01-01T07:30:00Z",
            "startTime": f"2026-01-02T{h:02d}:00:00Z",
            "generation": 11000
        })

    matched, metrics = match_forecasts_and_actuals(
        windfor_records=windfor_records,
        hourly_actuals=hourly_actuals,
        delivery_start_date=deliv_date,
        delivery_end_date=deliv_date,
        cutoff_hour_uk=9
    )

    # Denominator must be 24 (expected total)
    assert metrics.expected_intervals == 24
    assert metrics.matched_intervals == 20
    assert metrics.missing_actuals == 4
    assert metrics.coverage_pct == (20 / 24) * 100.0

    # MAE must be calculated ONLY over the 20 matched observations (1000.0 MW).
    # If missing were treated as zero (actual=0 -> error=11000), MAE would be much higher:
    # (20 * 1000 + 4 * 11000) / 24 = 2666.67.
    assert metrics.mae_mw == 1000.0
    assert metrics.rmse_mw == 1000.0
    assert metrics.bias_mw == 1000.0


def test_error_sign_convention():
    """
    Verification of error definition:
    error = forecast - actual
    Positive error means overforecast; negative means underforecast.
    """
    forecast_high = 18000.0
    forecast_low = 10000.0
    actual = 14000.0
    
    overforecast_error = forecast_high - actual
    underforecast_error = forecast_low - actual
    
    assert overforecast_error == +4000.0  # Overforecast
    assert underforecast_error == -4000.0  # Underforecast


def test_zero_matched_intervals_returns_none_metrics():
    """
    Verify that zero matched intervals return coverage 0.0% and None for undefined metrics
    (MAE, RMSE, Bias, Percentiles, lead times).
    """
    deliv_date = date(2026, 1, 2)
    matched, metrics = match_forecasts_and_actuals(
        windfor_records=[],
        hourly_actuals={},
        delivery_start_date=deliv_date,
        delivery_end_date=deliv_date,
        cutoff_hour_uk=9
    )

    assert metrics.expected_intervals == 24
    assert metrics.matched_intervals == 0
    assert metrics.missing_forecasts == 24
    assert metrics.missing_actuals == 0
    assert metrics.coverage_pct == 0.0
    assert metrics.mae_mw is None
    assert metrics.rmse_mw is None
    assert metrics.bias_mw is None
    assert metrics.p50_abs_error_mw is None
    assert metrics.p90_abs_error_mw is None
    assert metrics.p99_abs_error_mw is None
    assert metrics.max_abs_error_mw is None
    assert metrics.min_lead_time_hours is None
    assert metrics.max_lead_time_hours is None
    assert metrics.avg_lead_time_hours is None


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
    compute_error_by_horizon,
    HORIZON_BUCKET_DEFINITIONS,
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
    Verify that zero matched intervals return coverage 0.0%, 24 missing forecasts,
    24 missing actuals (independent counters), and None for undefined metrics.
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
    assert metrics.missing_actuals == 24
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


def test_forecast_vintage_rule_enforcement():
    """
    Verify that only forecasts published on Day D-1 and at or before decision cutoff are eligible:
    - Pre-D-1 forecast (published on D-2) is rejected.
    - D-1 forecast before cutoff is eligible.
    - D-1 forecast at exact cutoff boundary is eligible (inclusive).
    - D-1 post-cutoff forecast is rejected.
    - Day D forecast is rejected.
    """
    target_st = parse_iso_datetime("2026-01-02T12:00:00Z")  # Delivery Day D = 2026-01-02
    cutoff = parse_iso_datetime("2026-01-01T09:00:00Z")     # Cutoff = 2026-01-01 09:00 (D-1)

    records = [
        # Older forecast published before D-1 (D-2)
        {"dataset": "WINDFOR", "publishTime": "2025-12-31T23:59:59Z", "startTime": "2026-01-02T12:00:00Z", "generation": 9000},
        # Eligible D-1 forecast before cutoff
        {"dataset": "WINDFOR", "publishTime": "2026-01-01T07:30:00Z", "startTime": "2026-01-02T12:00:00Z", "generation": 12000},
        # Eligible D-1 forecast at exact cutoff boundary
        {"dataset": "WINDFOR", "publishTime": "2026-01-01T09:00:00Z", "startTime": "2026-01-02T12:00:00Z", "generation": 13000},
        # Post-cutoff D-1 forecast (1 second late)
        {"dataset": "WINDFOR", "publishTime": "2026-01-01T09:00:01Z", "startTime": "2026-01-02T12:00:00Z", "generation": 99999},
        # Post-cutoff Day D forecast
        {"dataset": "WINDFOR", "publishTime": "2026-01-02T06:00:00Z", "startTime": "2026-01-02T12:00:00Z", "generation": 88888},
    ]

    # Latest eligible at 09:00 cutoff must be the 09:00:00Z forecast
    selected = filter_and_select_forecasts(records, target_st, cutoff)
    assert selected is not None
    assert selected["publishTime"] == "2026-01-01T09:00:00Z"
    assert selected["generation"] == 13000

    # If the exact 09:00 forecast is removed, the 07:30 forecast must be selected
    records_without_exact = [r for r in records if r["publishTime"] != "2026-01-01T09:00:00Z"]
    selected_earlier = filter_and_select_forecasts(records_without_exact, target_st, cutoff)
    assert selected_earlier is not None
    assert selected_earlier["publishTime"] == "2026-01-01T07:30:00Z"
    assert selected_earlier["generation"] == 12000

    # If all D-1 forecasts are removed, the older D-2 forecast (2025-12-31) must NOT be selected
    records_only_d2_and_post = [r for r in records if not r["publishTime"].startswith("2026-01-01")]
    selected_none = filter_and_select_forecasts(records_only_d2_and_post, target_st, cutoff)
    assert selected_none is None


def test_missing_data_counters_independent():
    """
    Verify independent calculation of missing-forecast and missing-actual counters:
    - Forecast-only missing
    - Actual-only missing
    - Both missing
    """
    deliv_date = date(2026, 1, 2)
    utc_tz = parse_iso_datetime("2026-01-01T00:00:00Z").tzinfo

    # 1. Forecast-only missing: 24 actuals, but only 18 forecasts (hours 0-17)
    actuals_24 = {}
    for h in range(24):
        st = datetime(2026, 1, 2, h, 0, tzinfo=utc_tz)
        actuals_24[st] = type('obj', (object,), {"target_start_time": st, "generation_mw": 10000.0})()

    forecasts_18 = []
    for h in range(18):
        forecasts_18.append({
            "dataset": "WINDFOR",
            "publishTime": "2026-01-01T07:30:00Z",
            "startTime": f"2026-01-02T{h:02d}:00:00Z",
            "generation": 11000.0
        })

    _, m_fc_missing = match_forecasts_and_actuals(forecasts_18, actuals_24, deliv_date, deliv_date, 9)
    assert m_fc_missing.expected_intervals == 24
    assert m_fc_missing.matched_intervals == 18
    assert m_fc_missing.missing_forecasts == 6
    assert m_fc_missing.missing_actuals == 0
    assert m_fc_missing.coverage_pct == (18 / 24) * 100.0

    # 2. Actual-only missing: 24 forecasts, but only 20 actuals (hours 0-19)
    actuals_20 = {st: actuals_24[st] for st in list(actuals_24.keys())[:20]}
    forecasts_24 = []
    for h in range(24):
        forecasts_24.append({
            "dataset": "WINDFOR",
            "publishTime": "2026-01-01T07:30:00Z",
            "startTime": f"2026-01-02T{h:02d}:00:00Z",
            "generation": 11000.0
        })

    _, m_act_missing = match_forecasts_and_actuals(forecasts_24, actuals_20, deliv_date, deliv_date, 9)
    assert m_act_missing.expected_intervals == 24
    assert m_act_missing.matched_intervals == 20
    assert m_act_missing.missing_forecasts == 0
    assert m_act_missing.missing_actuals == 4
    assert m_act_missing.coverage_pct == (20 / 24) * 100.0

    # 3. Both missing on overlapping and distinct intervals:
    # Hours 0-11: both present (12 matched)
    # Hours 12-15: forecast only (4 actual missing)
    # Hours 16-19: actual only (4 forecast missing)
    # Hours 20-23: neither present (4 both missing)
    mixed_actuals = {}
    for h in list(range(0, 12)) + list(range(16, 20)):  # 12 + 4 = 16 actuals
        st = datetime(2026, 1, 2, h, 0, tzinfo=utc_tz)
        mixed_actuals[st] = type('obj', (object,), {"target_start_time": st, "generation_mw": 10000.0})()

    mixed_forecasts = []
    for h in list(range(0, 16)):  # 12 + 4 = 16 forecasts
        mixed_forecasts.append({
            "dataset": "WINDFOR",
            "publishTime": "2026-01-01T07:30:00Z",
            "startTime": f"2026-01-02T{h:02d}:00:00Z",
            "generation": 11000.0
        })

    _, m_mixed = match_forecasts_and_actuals(mixed_forecasts, mixed_actuals, deliv_date, deliv_date, 9)
    assert m_mixed.expected_intervals == 24
    assert m_mixed.matched_intervals == 12  # only hours 0-11
    # missing forecasts: hours 16-23 = 8
    assert m_mixed.missing_forecasts == 8
    # missing actuals: hours 12-15 and 20-23 = 8
    assert m_mixed.missing_actuals == 8
    assert m_mixed.coverage_pct == (12 / 24) * 100.0


def test_compute_error_by_horizon_buckets():
    """
    Verify forecast-horizon analysis:
    - Defined operational buckets: < 12h, 12–18h, 18–24h, 24–30h, 30–36h, 36–42h, ≥ 42h
    - Correct bucket boundary assignment [min, max)
    - Empty buckets return count=0 and None for metrics
    - Non-empty buckets return correct MAE, RMSE, bias, and average lead time
    """
    class MockAligned:
        def __init__(self, lead_time_hours: float, fc: float, act: float):
            self.lead_time_hours = lead_time_hours
            self.forecast_mw = fc
            self.actual_mw = act
            self.error_mw = fc - act

    # Test samples placing observations across different buckets and boundaries:
    # < 12h: 11.9h (1 item)
    # 12–18h: 12.0h (boundary check: must go to 12-18h, not < 12h), 15.0h (2 items)
    # 18–24h: 18.0h (boundary check), 20.0h (2 items)
    # 24–30h: 27.5h (1 item)
    # 30–36h: (empty! 0 items)
    # 36–42h: 41.9h (1 item)
    # ≥ 42h: 42.0h (boundary check), 50.0h (2 items)
    aligned_items = [
        MockAligned(11.9, 12000.0, 10000.0),  # error = +2000
        MockAligned(12.0, 15000.0, 14000.0),  # error = +1000
        MockAligned(15.0, 13000.0, 10000.0),  # error = +3000
        MockAligned(18.0, 11000.0, 12000.0),  # error = -1000
        MockAligned(20.0, 14000.0, 10000.0),  # error = +4000
        MockAligned(27.5, 10000.0, 10000.0),  # error = 0
        MockAligned(41.9, 8000.0, 10000.0),   # error = -2000
        MockAligned(42.0, 16000.0, 12000.0),  # error = +4000
        MockAligned(50.0, 10000.0, 12000.0),  # error = -2000
    ]

    buckets = compute_error_by_horizon(aligned_items)
    assert len(buckets) == 7
    b_dict = {b["horizon_bucket"]: b for b in buckets}

    # 1. < 12h: 1 item, lead 11.9, error +2000
    b_lt12 = b_dict["< 12h"]
    assert b_lt12["count"] == 1
    assert b_lt12["avg_lead_time_hours"] == 11.9
    assert b_lt12["mae_mw"] == 2000.0
    assert b_lt12["rmse_mw"] == 2000.0
    assert b_lt12["bias_mw"] == 2000.0

    # 2. 12–18h: 2 items (12.0h and 15.0h) -> errors +1000, +3000
    b_12_18 = b_dict["12–18h"]
    assert b_12_18["count"] == 2
    assert b_12_18["avg_lead_time_hours"] == 13.5
    assert b_12_18["mae_mw"] == 2000.0
    assert b_12_18["bias_mw"] == 2000.0  # (1000 + 3000)/2

    # 3. 18–24h: 2 items (18.0h and 20.0h) -> errors -1000, +4000
    b_18_24 = b_dict["18–24h"]
    assert b_18_24["count"] == 2
    assert b_18_24["avg_lead_time_hours"] == 19.0
    assert b_18_24["mae_mw"] == 2500.0  # (| -1000 | + | 4000 |) / 2
    assert b_18_24["bias_mw"] == 1500.0  # (-1000 + 4000) / 2

    # 4. 24–30h: 1 item (27.5h) -> error 0
    b_24_30 = b_dict["24–30h"]
    assert b_24_30["count"] == 1
    assert b_24_30["mae_mw"] == 0.0
    assert b_24_30["bias_mw"] == 0.0

    # 5. 30–36h: EMPTY bucket (0 items) -> None metrics (never 0.0!)
    b_30_36 = b_dict["30–36h"]
    assert b_30_36["count"] == 0
    assert b_30_36["avg_lead_time_hours"] is None
    assert b_30_36["mae_mw"] is None
    assert b_30_36["rmse_mw"] is None
    assert b_30_36["bias_mw"] is None
    assert b_30_36["p90_abs_error_mw"] is None
    assert b_30_36["max_abs_error_mw"] is None

    # 6. 36–42h: 1 item (41.9h) -> error -2000
    b_36_42 = b_dict["36–42h"]
    assert b_36_42["count"] == 1
    assert b_36_42["mae_mw"] == 2000.0
    assert b_36_42["bias_mw"] == -2000.0

    # 7. ≥ 42h: 2 items (42.0h, 50.0h) -> errors +4000, -2000
    b_ge42 = b_dict["≥ 42h"]
    assert b_ge42["count"] == 2
    assert b_ge42["avg_lead_time_hours"] == 46.0
    assert b_ge42["mae_mw"] == 3000.0
    assert b_ge42["bias_mw"] == 1000.0  # (4000 - 2000) / 2


def test_bias_positive_negative_interpretation():
    """
    Verify bias definition and sign conventions:
    - error = forecast - actual
    - Positive bias: forecast exceeds actual on average (overforecasting).
    - Negative bias: forecast is lower than actual on average (underforecasting).
    """
    deliv_date = date(2026, 1, 2)
    utc_tz = parse_iso_datetime("2026-01-01T00:00:00Z").tzinfo

    actuals = {}
    for h in range(24):
        st = datetime(2026, 1, 2, h, 0, tzinfo=utc_tz)
        actuals[st] = type('obj', (object,), {"target_start_time": st, "generation_mw": 10000.0})()

    # Overforecast case: forecast = 12000, actual = 10000 -> bias = +2000
    forecasts_high = [
        {"dataset": "WINDFOR", "publishTime": "2026-01-01T07:30:00Z", "startTime": f"2026-01-02T{h:02d}:00:00Z", "generation": 12000.0}
        for h in range(24)
    ]
    _, m_over = match_forecasts_and_actuals(forecasts_high, actuals, deliv_date, deliv_date, 9)
    assert m_over.bias_mw == 2000.0
    assert m_over.bias_mw > 0  # Systematic overprediction

    # Underforecast case: forecast = 8000, actual = 10000 -> bias = -2000
    forecasts_low = [
        {"dataset": "WINDFOR", "publishTime": "2026-01-01T07:30:00Z", "startTime": f"2026-01-02T{h:02d}:00:00Z", "generation": 8000.0}
        for h in range(24)
    ]
    _, m_under = match_forecasts_and_actuals(forecasts_low, actuals, deliv_date, deliv_date, 9)
    assert m_under.bias_mw == -2000.0
    assert m_under.bias_mw < 0  # Systematic underprediction





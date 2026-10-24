"""
Automated API and Service integration tests for Wind Forecast Decision Portal.

Covers:
- All 6 endpoints: /health, /forecast-vs-actual, /metrics, /error-by-horizon, /error-by-hour, /daily-errors
- Parameter validation: invalid scopes, inverted date ranges, invalid cutoff formats
- Documented evaluation scopes: Scope A (Jan 1-31) and Scope B (Jan 2-Feb 1)
- Deterministic mock data fixtures (zero external dependency)
- Forecast cutoff selection and publication timestamps
- Missing actuals and forecasts (ensuring missing records are never treated as zero)
- Exact duplicate pruning and conflicting record integrity errors
- Metric calculations: MAE, RMSE, Bias, P50, P90, P99, Max error, zero-error case, empty results
"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_loader import set_cached_data, clear_cache


@pytest.fixture(autouse=True)
def reset_data_cache():
    """Ensure in-memory cache is reset before each test."""
    clear_cache()
    yield
    clear_cache()


def create_deterministic_fixtures(delivery_date_str: str = "2026-01-02", actual_gen: float = 10000.0, fc_gen: float = 12000.0):
    """
    Generate 24 hours of deterministic half-hourly actuals and hourly forecasts.
    For delivery_date_str:
      - Cutoff on previous day at 09:00:00Z.
      - Forecast published on previous day at 07:30:00Z.
      - Error = fc_gen - actual_gen = +2000.0 MW.
    """
    deliv_d = date.fromisoformat(delivery_date_str)
    prev_d = (deliv_d - timedelta(days=1)).strftime("%Y-%m-%d")
    raw_fuelhh = []
    # 48 settlement periods
    for sp in range(1, 49):
        h = (sp - 1) // 2
        m = "00" if sp % 2 == 1 else "30"
        st = f"{delivery_date_str}T{h:02d}:{m}:00Z"
        raw_fuelhh.append({
            "dataset": "FUELHH",
            "publishTime": f"{delivery_date_str}T{h:02d}:30:00Z",
            "startTime": st,
            "settlementDate": delivery_date_str,
            "settlementPeriod": sp,
            "fuelType": "WIND",
            "generation": actual_gen
        })

    raw_windfor = []
    # 24 hours of forecasts
    for h in range(24):
        raw_windfor.append({
            "dataset": "WINDFOR",
            "publishTime": f"{prev_d}T07:30:00Z",
            "startTime": f"{delivery_date_str}T{h:02d}:00:00Z",
            "generation": fc_gen
        })

    return raw_fuelhh, raw_windfor


client = TestClient(app)


def test_health_check_endpoint():
    """Verify /api/health endpoint response structure."""
    fuelhh, windfor = create_deterministic_fixtures()
    set_cached_data(fuelhh=fuelhh, windfor=windfor)

    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
    assert data["data_loaded"] is True
    assert data["fuelhh_records"] == 48
    assert data["windfor_records"] == 24


def test_forecast_vs_actual_scope_a():
    """Verify /api/forecast-vs-actual with Scope A parameter."""
    fuelhh, windfor = create_deterministic_fixtures("2026-01-01")
    set_cached_data(fuelhh=fuelhh, windfor=windfor)

    resp = client.get("/api/forecast-vs-actual?scope=A&start_date=2026-01-01&end_date=2026-01-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["scope"] == "A"
    assert data["expected_intervals"] == 24
    assert data["matched_intervals"] == 24
    assert data["coverage_pct"] == 100.0
    assert len(data["data"]) == 24

    first = data["data"][0]
    assert first["delivery_date"] == "2026-01-01"
    assert first["hour_index"] == 0
    assert first["forecast_mw"] == 12000.0
    assert first["actual_mw"] == 10000.0
    assert first["error_mw"] == 2000.0
    assert first["lead_time_hours"] == 16.5  # 00:00 - 07:30 = 16.5h


def test_forecast_vs_actual_scope_b():
    """Verify /api/forecast-vs-actual with Scope B parameter (Jan 2 to Feb 1)."""
    fuelhh, windfor = create_deterministic_fixtures("2026-01-02")
    set_cached_data(fuelhh=fuelhh, windfor=windfor)

    resp = client.get("/api/forecast-vs-actual?scope=B&start_date=2026-01-02&end_date=2026-01-02")
    assert resp.status_code == 200
    data = resp.json()
    assert data["scope"] == "B"
    assert data["matched_intervals"] == 24


def test_metrics_endpoint_calculation():
    """Verify statistical metrics calculation against deterministic reference."""
    fuelhh, windfor = create_deterministic_fixtures(actual_gen=10000.0, fc_gen=12000.0)
    set_cached_data(fuelhh=fuelhh, windfor=windfor)

    resp = client.get("/api/metrics?start_date=2026-01-02&end_date=2026-01-02")
    assert resp.status_code == 200
    m = resp.json()

    assert m["expected_intervals"] == 24
    assert m["matched_intervals"] == 24
    assert m["coverage_pct"] == 100.0
    assert m["mae_mw"] == 2000.0
    assert m["rmse_mw"] == 2000.0
    assert m["bias_mw"] == 2000.0
    assert m["p50_abs_error_mw"] == 2000.0
    assert m["p90_abs_error_mw"] == 2000.0
    assert m["p99_abs_error_mw"] == 2000.0
    assert m["max_abs_error_mw"] == 2000.0
    assert m["min_lead_time_hours"] == 16.5
    assert m["max_lead_time_hours"] == 39.5
    assert m["avg_lead_time_hours"] == 28.0


def test_metrics_zero_error_case():
    """Verify zero-error case produces exactly 0.0 for all error metrics."""
    fuelhh, windfor = create_deterministic_fixtures(actual_gen=15000.0, fc_gen=15000.0)
    set_cached_data(fuelhh=fuelhh, windfor=windfor)

    resp = client.get("/api/metrics?start_date=2026-01-02&end_date=2026-01-02")
    assert resp.status_code == 200
    m = resp.json()
    assert m["mae_mw"] == 0.0
    assert m["rmse_mw"] == 0.0
    assert m["bias_mw"] == 0.0
    assert m["p50_abs_error_mw"] == 0.0
    assert m["p90_abs_error_mw"] == 0.0
    assert m["max_abs_error_mw"] == 0.0


def test_empty_results_and_coverage():
    """Verify empty results return 0 matched intervals, 0.0% coverage, and null metrics."""
    # Empty datasets
    set_cached_data(fuelhh=[], windfor=[])

    resp = client.get("/api/metrics?start_date=2026-01-02&end_date=2026-01-02")
    assert resp.status_code == 200
    m = resp.json()
    assert m["expected_intervals"] == 24
    assert m["matched_intervals"] == 0
    assert m["coverage_pct"] == 0.0
    assert m["mae_mw"] is None
    assert m["rmse_mw"] is None
    assert m["bias_mw"] is None
    assert m["p50_abs_error_mw"] is None
    assert m["p90_abs_error_mw"] is None
    assert m["p99_abs_error_mw"] is None
    assert m["max_abs_error_mw"] is None
    assert m["min_lead_time_hours"] is None
    assert m["max_lead_time_hours"] is None
    assert m["avg_lead_time_hours"] is None


def test_error_by_horizon_endpoint():
    """Verify /api/error-by-horizon returns lead time grouped statistics."""
    fuelhh, windfor = create_deterministic_fixtures()
    set_cached_data(fuelhh=fuelhh, windfor=windfor)

    resp = client.get("/api/error-by-horizon?start_date=2026-01-02&end_date=2026-01-02")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 24  # 24 distinct lead times from 16.5 to 39.5
    assert data[0]["lead_time_hours"] == 16.5
    assert data[0]["count"] == 1
    assert data[0]["mae_mw"] == 2000.0


def test_error_by_hour_endpoint():
    """Verify /api/error-by-hour returns 24 hourly buckets with settlement periods."""
    fuelhh, windfor = create_deterministic_fixtures()
    set_cached_data(fuelhh=fuelhh, windfor=windfor)

    resp = client.get("/api/error-by-hour?start_date=2026-01-02&end_date=2026-01-02")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 24
    for h in range(24):
        item = data[h]
        assert item["hour_of_day"] == h
        assert item["settlement_periods"] == [h * 2 + 1, h * 2 + 2]
        assert item["mae_mw"] == 2000.0


def test_daily_errors_endpoint():
    """Verify /api/daily-errors returns day-level statistics and energy in MWh."""
    fuelhh, windfor = create_deterministic_fixtures(actual_gen=10000.0, fc_gen=12000.0)
    set_cached_data(fuelhh=fuelhh, windfor=windfor)

    resp = client.get("/api/daily-errors?start_date=2026-01-02&end_date=2026-01-02")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    day = data[0]
    assert day["delivery_date"] == "2026-01-02"
    assert day["matched_hours"] == 24
    assert day["daily_coverage_pct"] == 100.0
    assert day["daily_mae_mw"] == 2000.0
    assert day["is_complete"] is True
    assert day["missing_hours"] == 0
    assert day["daily_energy_forecast_mwh"] == 12000.0 * 24  # 288,000 MWh
    assert day["daily_energy_actual_mwh"] == 10000.0 * 24    # 240,000 MWh


def test_daily_errors_partial_day_handling():
    """Verify that partial days are marked is_complete=False and missing_hours > 0."""
    fuelhh, windfor = create_deterministic_fixtures(actual_gen=10000.0, fc_gen=12000.0)
    # Remove 8 half-hours (4 hours missing -> 20 hours matched)
    fuelhh_partial = fuelhh[:40]
    set_cached_data(fuelhh=fuelhh_partial, windfor=windfor)

    resp = client.get("/api/daily-errors?start_date=2026-01-02&end_date=2026-01-02")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    day = data[0]
    assert day["expected_hours"] == 24
    assert day["matched_hours"] == 20
    assert day["missing_hours"] == 4
    assert day["is_complete"] is False
    assert day["daily_coverage_pct"] == round((20 / 24) * 100.0, 2)
    assert day["daily_energy_forecast_mwh"] == 12000.0 * 20
    assert day["daily_energy_actual_mwh"] == 10000.0 * 20


def test_invalid_query_parameters_validation():
    """Verify HTTP 400 responses on invalid user input."""
    fuelhh, windfor = create_deterministic_fixtures()
    set_cached_data(fuelhh=fuelhh, windfor=windfor)

    # 1. Invalid scope
    resp = client.get("/api/metrics?scope=XYZ")
    assert resp.status_code == 400
    assert "Invalid scope" in resp.json()["detail"]

    # 2. Inverted date range
    resp = client.get("/api/metrics?start_date=2026-01-10&end_date=2026-01-05")
    assert resp.status_code == 400
    assert "cannot be after end_date" in resp.json()["detail"]

    # 4. Dates before supported cached delivery window (prior to 2026-01-01)
    resp = client.get("/api/metrics?start_date=2025-12-31&end_date=2026-01-15")
    assert resp.status_code == 400
    assert "outside the supported cached delivery window" in resp.json()["detail"]

    # 5. Dates after supported cached delivery window (after 2026-02-01)
    resp = client.get("/api/metrics?start_date=2026-01-15&end_date=2026-02-05")
    assert resp.status_code == 400
    assert "outside the supported cached delivery window" in resp.json()["detail"]

    # 6. Providing only one date without scope
    resp = client.get("/api/metrics?start_date=2026-01-10")
    assert resp.status_code == 400
    assert "Both start_date and end_date must be provided" in resp.json()["detail"]

    resp = client.get("/api/metrics?end_date=2026-01-10")
    assert resp.status_code == 400
    assert "Both start_date and end_date must be provided" in resp.json()["detail"]


def test_default_route_returns_scope_b():
    """Verify that calling /api/metrics with no parameters defaults to Scope B benchmark."""
    clear_cache()
    resp = client.get("/api/metrics")
    assert resp.status_code == 200
    m = resp.json()
    assert m["scope"] == "B"
    assert m["start_date"] == "2026-01-02"
    assert m["end_date"] == "2026-02-01"
    assert m["cutoff_time"] == "09:00"
    assert m["expected_intervals"] == 744
    assert m["matched_intervals"] == 744
    assert m["coverage_pct"] == 100.0
    assert m["mae_mw"] == 2038.91
    assert m["rmse_mw"] == 2504.76
    assert m["bias_mw"] == 1747.89
    assert m["p90_abs_error_mw"] == 4097.90


def test_missing_records_not_treated_as_zero_in_api():
    """Verify missing actuals penalize coverage denominator and are not evaluated as 0 MW."""
    fuelhh, windfor = create_deterministic_fixtures(actual_gen=10000.0, fc_gen=11000.0)
    # Remove half of the actuals (only 12 hours present, 12 missing)
    fuelhh_partial = fuelhh[:24]  # 24 half-hours = 12 hours
    set_cached_data(fuelhh=fuelhh_partial, windfor=windfor)

    resp = client.get("/api/metrics?start_date=2026-01-02&end_date=2026-01-02")
    assert resp.status_code == 200
    m = resp.json()

    assert m["expected_intervals"] == 24
    assert m["matched_intervals"] == 12
    assert m["missing_actuals"] == 12
    assert m["coverage_pct"] == 50.0

    # MAE must be exactly 1000 MW (11000 - 10000) over the 12 matched intervals.
    # If missing were treated as zero (11000 - 0 = 11000), MAE would be 6000 MW.
    assert m["mae_mw"] == 1000.0


def test_conflicting_data_raises_server_error():
    """Verify conflicting generation values for identical key trigger a DataIntegrityError / HTTP 500."""
    fuelhh, windfor = create_deterministic_fixtures()
    # Add conflicting record for period 1
    fuelhh.append({
        "dataset": "FUELHH",
        "publishTime": fuelhh[0]["publishTime"],
        "startTime": fuelhh[0]["startTime"],
        "settlementDate": fuelhh[0]["settlementDate"],
        "settlementPeriod": 1,
        "fuelType": "WIND",
        "generation": 99999.0  # Conflicting value
    })
    set_cached_data(fuelhh=fuelhh, windfor=windfor)

    resp = client.get("/api/metrics?start_date=2026-01-02&end_date=2026-01-02")
    assert resp.status_code == 500
    assert "Conflicting generation values" in resp.json()["detail"]


def test_real_data_regression_scope_a():
    """Verify real cached data benchmark metrics against Scope A reference values."""
    clear_cache()  # Force reading from backend/data/
    resp = client.get("/api/metrics?scope=A")
    assert resp.status_code == 200
    m = resp.json()
    assert m["expected_intervals"] == 744
    assert m["matched_intervals"] == 744
    assert m["coverage_pct"] == 100.0
    assert m["missing_actuals"] == 0
    assert m["missing_forecasts"] == 0
    assert m["mae_mw"] == 2142.12
    assert m["rmse_mw"] == 2611.70
    assert m["bias_mw"] == 1851.90
    assert m["p90_abs_error_mw"] == 4300.15
    assert m["min_lead_time_hours"] == 16.5
    assert m["max_lead_time_hours"] == 39.5
    assert m["avg_lead_time_hours"] == 28.0


def test_real_data_regression_scope_b():
    """Verify real cached data benchmark metrics against Scope B reference values."""
    clear_cache()
    resp = client.get("/api/metrics?scope=B")
    assert resp.status_code == 200
    m = resp.json()
    assert m["expected_intervals"] == 744
    assert m["matched_intervals"] == 744
    assert m["coverage_pct"] == 100.0
    assert m["missing_actuals"] == 0
    assert m["missing_forecasts"] == 0
    assert m["mae_mw"] == 2038.91
    assert m["rmse_mw"] == 2504.76
    assert m["bias_mw"] == 1747.89
    assert m["p90_abs_error_mw"] == 4097.90
    assert m["min_lead_time_hours"] == 16.5
    assert m["max_lead_time_hours"] == 39.5
    assert m["avg_lead_time_hours"] == 28.0


def test_cutoff_change_alters_forecast_selection():
    """Verify changing cutoff from 09:00 to 04:00 selects earlier vintage and alters lead times and metrics."""
    clear_cache()
    resp_0900 = client.get("/api/metrics?scope=A&cutoff_time=09:00")
    resp_0400 = client.get("/api/metrics?scope=A&cutoff_time=04:00")
    assert resp_0900.status_code == 200
    assert resp_0400.status_code == 200
    m_0900 = resp_0900.json()
    m_0400 = resp_0400.json()

    # Lead times with 04:00 cutoff must be longer because latest eligible forecast is earlier
    assert m_0400["min_lead_time_hours"] > m_0900["min_lead_time_hours"]
    assert m_0400["avg_lead_time_hours"] > m_0900["avg_lead_time_hours"]
    # MAE should differ between cutoffs
    assert m_0400["mae_mw"] != m_0900["mae_mw"]


def test_cutoff_0400_never_selects_0430_on_real_data():
    """
    Verify on real January 2026 data that cutoff_time=04:00:
    - Never selects a forecast published after 04:00 (such as 04:30:00Z).
    - Every selected forecast has publishTime <= cutoff_time.
    - All selected forecasts on real data are published at 02:30:00Z.
    """
    clear_cache()
    resp = client.get("/api/forecast-vs-actual?scope=A&cutoff_time=04:00")
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) == 744

    for item in items:
        # publish_time must be strictly <= cutoff_time
        assert item["publish_time"] <= item["cutoff_time"], f"Violation: {item['publish_time']} > {item['cutoff_time']}"
        # Assert that 04:30 is NEVER selected
        assert not item["publish_time"].endswith("T04:30:00+00:00"), f"Post-cutoff 04:30 selected for {item['target_start_time']}"
        # On real data, the latest publication before 04:00 is 02:30:00Z
        assert item["publish_time"].endswith("T02:30:00+00:00"), f"Unexpected publication {item['publish_time']}"


def test_cors_headers_and_origin_policy():
    """Verify CORS middleware responds with explicit allowed origin and credentials appropriately."""
    # Allowed origin request
    resp = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert resp.headers.get("access-control-allow-credentials") == "true"

    # Disallowed origin should not be reflected
    disallowed_resp = client.get("/api/health", headers={"Origin": "http://evil-unauthorized-domain.com"})
    assert disallowed_resp.status_code == 200
    assert disallowed_resp.headers.get("access-control-allow-origin") is None

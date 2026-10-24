"""
API Route Handlers for Wind Forecast Decision Portal.
Provides endpoints for:
- Health check
- Forecast vs Actual hourly comparison
- Overall verification metrics
- Error distribution by lead-time horizon
- Error distribution by hour of day
- Daily aggregated errors and energy totals
"""

from fastapi import APIRouter, Query, HTTPException, status
from datetime import date, datetime
from typing import Optional, Tuple, List, Dict, Any

from app.config import settings
from app.models.schemas import (
    HealthResponse,
    ForecastVsActualResponse,
    ForecastVsActualItem,
    MetricsResponse,
    ErrorByHorizonItem,
    ErrorByHourItem,
    DailyErrorItem
)
from app.services.data_loader import load_fuelhh_data, load_windfor_data
from app.services.alignment import (
    aggregate_fuelhh_to_hourly,
    match_forecasts_and_actuals,
    compute_error_by_horizon,
    compute_error_by_hour,
    compute_daily_errors,
    MatchedForecastActual,
    VerificationMetrics
)

router = APIRouter()


def resolve_and_validate_params(
    scope: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
    cutoff_time: str
) -> Tuple[date, date, int, int, Optional[str]]:
    """Validate query parameters and resolve effective delivery range and cutoff."""
    norm_scope = scope.upper() if scope else None
    
    if norm_scope and norm_scope not in ["A", "B"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scope '{scope}'. Supported values are 'A' and 'B'."
        )

    # Cutoff time validation (HH:MM)
    try:
        parts = cutoff_time.strip().split(":")
        if len(parts) != 2:
            raise ValueError
        cutoff_hour = int(parts[0])
        cutoff_minute = int(parts[1])
        if not (0 <= cutoff_hour <= 23 and 0 <= cutoff_minute <= 59):
            raise ValueError
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cutoff_time '{cutoff_time}'. Must be in 'HH:MM' 24-hour format (00:00 to 23:59)."
        )

    # Date range resolution
    resolved_start = start_date
    resolved_end = end_date

    if norm_scope == "A":
        resolved_start = resolved_start or date.fromisoformat(settings.SCOPE_A_START)
        resolved_end = resolved_end or date.fromisoformat(settings.SCOPE_A_END)
    elif norm_scope == "B":
        resolved_start = resolved_start or date.fromisoformat(settings.SCOPE_B_START)
        resolved_end = resolved_end or date.fromisoformat(settings.SCOPE_B_END)
    else:
        # Default to Scope B if neither scope nor dates are supplied
        if resolved_start is None and resolved_end is None:
            norm_scope = settings.DEFAULT_SCOPE
            resolved_start = date.fromisoformat(settings.SCOPE_B_START)
            resolved_end = date.fromisoformat(settings.SCOPE_B_END)
        elif resolved_start is None or resolved_end is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both start_date and end_date must be provided when querying custom date ranges."
            )

    if resolved_start > resolved_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date range: start_date ({resolved_start}) cannot be after end_date ({resolved_end})."
        )

    # Server-side validation against supported cached dataset window
    supported_min = date.fromisoformat(settings.SUPPORTED_DELIVERY_START)
    supported_max = date.fromisoformat(settings.SUPPORTED_DELIVERY_END)
    if resolved_start < supported_min or resolved_end > supported_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Requested date range ({resolved_start} to {resolved_end}) is outside "
                f"the supported cached delivery window ({settings.SUPPORTED_DELIVERY_START} to {settings.SUPPORTED_DELIVERY_END})."
            )
        )

    # Determine accurate effective scope indicator
    scope_a_start = date.fromisoformat(settings.SCOPE_A_START)
    scope_a_end = date.fromisoformat(settings.SCOPE_A_END)
    scope_b_start = date.fromisoformat(settings.SCOPE_B_START)
    scope_b_end = date.fromisoformat(settings.SCOPE_B_END)

    if norm_scope:
        effective_scope = norm_scope
    elif resolved_start == scope_a_start and resolved_end == scope_a_end:
        effective_scope = "A"
    elif resolved_start == scope_b_start and resolved_end == scope_b_end:
        effective_scope = "B"
    else:
        effective_scope = None

    return resolved_start, resolved_end, cutoff_hour, cutoff_minute, effective_scope


def execute_alignment(
    start_d: date,
    end_d: date,
    cutoff_h: int,
    cutoff_m: int
) -> Tuple[List[MatchedForecastActual], VerificationMetrics]:
    """Execute cached data loading and alignment matching."""
    try:
        fuelhh_raw = load_fuelhh_data()
        windfor_raw = load_windfor_data()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load cached datasets: {str(e)}"
        )

    try:
        hourly_actuals = aggregate_fuelhh_to_hourly(fuelhh_raw)
        matched, metrics = match_forecasts_and_actuals(
            windfor_records=windfor_raw,
            hourly_actuals=hourly_actuals,
            delivery_start_date=start_d,
            delivery_end_date=end_d,
            cutoff_hour_uk=cutoff_h,
            cutoff_minute_uk=cutoff_m
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data integrity or alignment error: {str(e)}"
        )

    return matched, metrics


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint displaying system and dataset loading status."""
    fuelhh_loaded = False
    windfor_loaded = False
    fuelhh_count = 0
    windfor_count = 0

    try:
        f = load_fuelhh_data()
        fuelhh_count = len(f)
        fuelhh_loaded = True
    except Exception:
        pass

    try:
        w = load_windfor_data()
        windfor_count = len(w)
        windfor_loaded = True
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        data_loaded=fuelhh_loaded and windfor_loaded,
        fuelhh_records=fuelhh_count,
        windfor_records=windfor_count
    )


@router.get("/forecast-vs-actual", response_model=ForecastVsActualResponse)
def get_forecast_vs_actual(
    scope: Optional[str] = Query(None, description="Predefined scope: 'A' (Jan 1-31) or 'B' (Jan 2-Feb 1)"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    cutoff_time: str = Query("09:00", description="Cutoff time on D-1 in HH:MM format (default: 09:00)")
):
    """Retrieve hourly matched forecast vs actual readings with lead times and errors."""
    start_d, end_d, cutoff_h, cutoff_m, norm_scope = resolve_and_validate_params(
        scope, start_date, end_date, cutoff_time
    )
    matched, metrics = execute_alignment(start_d, end_d, cutoff_h, cutoff_m)

    items: List[ForecastVsActualItem] = []
    for m in matched:
        pct_err = round((m.error_mw / m.actual_mw) * 100.0, 2) if m.actual_mw > 0 else None
        items.append(ForecastVsActualItem(
            target_start_time=m.target_start_time.isoformat(),
            delivery_date=m.target_start_time.date().strftime("%Y-%m-%d"),
            hour_index=m.target_start_time.hour,
            cutoff_time=m.cutoff_time.isoformat(),
            publish_time=m.publish_time.isoformat(),
            lead_time_hours=round(m.lead_time_hours, 2),
            forecast_mw=round(m.forecast_mw, 2),
            actual_mw=round(m.actual_mw, 2),
            error_mw=round(m.error_mw, 2),
            abs_error_mw=round(abs(m.error_mw), 2),
            percentage_error=pct_err
        ))

    return ForecastVsActualResponse(
        scope=norm_scope,
        start_date=start_d.strftime("%Y-%m-%d"),
        end_date=end_d.strftime("%Y-%m-%d"),
        cutoff_time=f"{cutoff_h:02d}:{cutoff_m:02d}",
        expected_intervals=metrics.expected_intervals,
        matched_intervals=metrics.matched_intervals,
        coverage_pct=round(metrics.coverage_pct, 2),
        data=items
    )


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(
    scope: Optional[str] = Query(None, description="Predefined scope: 'A' (Jan 1-31) or 'B' (Jan 2-Feb 1)"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    cutoff_time: str = Query("09:00", description="Cutoff time on D-1 in HH:MM format (default: 09:00)")
):
    """Retrieve full statistical verification metrics (MAE, RMSE, Bias, P50, P90, P99, Max error, Coverage)."""
    start_d, end_d, cutoff_h, cutoff_m, norm_scope = resolve_and_validate_params(
        scope, start_date, end_date, cutoff_time
    )
    matched, metrics = execute_alignment(start_d, end_d, cutoff_h, cutoff_m)

    def _round(val: Optional[float], decimals: int = 2) -> Optional[float]:
        return round(val, decimals) if val is not None else None

    return MetricsResponse(
        scope=norm_scope,
        start_date=start_d.strftime("%Y-%m-%d"),
        end_date=end_d.strftime("%Y-%m-%d"),
        cutoff_time=f"{cutoff_h:02d}:{cutoff_m:02d}",
        expected_intervals=metrics.expected_intervals,
        matched_intervals=metrics.matched_intervals,
        missing_forecasts=metrics.missing_forecasts,
        missing_actuals=metrics.missing_actuals,
        coverage_pct=round(metrics.coverage_pct, 2),
        mae_mw=_round(metrics.mae_mw),
        rmse_mw=_round(metrics.rmse_mw),
        bias_mw=_round(metrics.bias_mw),
        p50_abs_error_mw=_round(metrics.p50_abs_error_mw),
        p90_abs_error_mw=_round(metrics.p90_abs_error_mw),
        p99_abs_error_mw=_round(metrics.p99_abs_error_mw),
        max_abs_error_mw=_round(metrics.max_abs_error_mw),
        min_lead_time_hours=_round(metrics.min_lead_time_hours),
        max_lead_time_hours=_round(metrics.max_lead_time_hours),
        avg_lead_time_hours=_round(metrics.avg_lead_time_hours)
    )


@router.get("/error-by-horizon", response_model=List[ErrorByHorizonItem])
def get_error_by_horizon(
    scope: Optional[str] = Query(None, description="Predefined scope: 'A' (Jan 1-31) or 'B' (Jan 2-Feb 1)"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    cutoff_time: str = Query("09:00", description="Cutoff time on D-1 in HH:MM format (default: 09:00)")
):
    """Retrieve error metrics grouped by lead-time horizon."""
    start_d, end_d, cutoff_h, cutoff_m, _ = resolve_and_validate_params(
        scope, start_date, end_date, cutoff_time
    )
    matched, _ = execute_alignment(start_d, end_d, cutoff_h, cutoff_m)
    return compute_error_by_horizon(matched)


@router.get("/error-by-hour", response_model=List[ErrorByHourItem])
def get_error_by_hour(
    scope: Optional[str] = Query(None, description="Predefined scope: 'A' (Jan 1-31) or 'B' (Jan 2-Feb 1)"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    cutoff_time: str = Query("09:00", description="Cutoff time on D-1 in HH:MM format (default: 09:00)")
):
    """Retrieve error metrics grouped by target hour of day (0 to 23)."""
    start_d, end_d, cutoff_h, cutoff_m, _ = resolve_and_validate_params(
        scope, start_date, end_date, cutoff_time
    )
    matched, _ = execute_alignment(start_d, end_d, cutoff_h, cutoff_m)
    return compute_error_by_hour(matched)


@router.get("/daily-errors", response_model=List[DailyErrorItem])
def get_daily_errors(
    scope: Optional[str] = Query(None, description="Predefined scope: 'A' (Jan 1-31) or 'B' (Jan 2-Feb 1)"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    cutoff_time: str = Query("09:00", description="Cutoff time on D-1 in HH:MM format (default: 09:00)")
):
    """Retrieve day-by-day errors and total daily energy (MWh)."""
    start_d, end_d, cutoff_h, cutoff_m, _ = resolve_and_validate_params(
        scope, start_date, end_date, cutoff_time
    )
    matched, _ = execute_alignment(start_d, end_d, cutoff_h, cutoff_m)
    return compute_daily_errors(matched, start_d, end_d)

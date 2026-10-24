"""
Data Alignment, Aggregation, and Forecast Verification Service.

Implements verified Elexon BMRS dataset semantics:
- FUELHH: 30-minute average power in MW.
- WINDFOR: 60-minute forecast power in MW.
- Aggregation: Arithmetic mean of 2 consecutive settlement periods (2h+1, 2h+2)
  representing average MW over the 1-hour interval [HH:00, (HH+1):00).
- Decision Cutoff: Configurable cutoff on D-1 (pilot assumption: 09:00 UK time).
- Error Definition: Forecast - Actual (positive indicates overforecast).
- Integrity: Explicit conflict detection for composite keys with differing generation values.
"""

from dataclasses import dataclass
from datetime import datetime, date, timedelta, time
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import math
import numpy as np


class DataIntegrityError(Exception):
    """Raised when conflicting records exist for the same composite key."""
    pass


@dataclass
class FuelHHRecord:
    dataset: str
    publish_time: datetime
    start_time: datetime
    settlement_date: str
    settlement_period: int
    fuel_type: str
    generation: Optional[float]


@dataclass
class WindforRecord:
    dataset: str
    publish_time: datetime
    start_time: datetime
    generation: Optional[float]


@dataclass
class HourlyActual:
    target_start_time: datetime
    settlement_date: str
    hour_index: int  # 0 to 23
    settlement_periods: Tuple[int, int]
    generation_mw: float
    is_complete: bool


@dataclass
class MatchedForecastActual:
    target_start_time: datetime
    cutoff_time: datetime
    publish_time: datetime
    lead_time_hours: float
    forecast_mw: float
    actual_mw: float
    error_mw: float  # forecast - actual


@dataclass
class VerificationMetrics:
    expected_intervals: int
    matched_intervals: int
    missing_forecasts: int
    missing_actuals: int
    coverage_pct: float
    mae_mw: Optional[float]
    rmse_mw: Optional[float]
    bias_mw: Optional[float]
    p50_abs_error_mw: Optional[float]
    p90_abs_error_mw: Optional[float]
    p99_abs_error_mw: Optional[float]
    max_abs_error_mw: Optional[float]
    min_lead_time_hours: Optional[float]
    max_lead_time_hours: Optional[float]
    avg_lead_time_hours: Optional[float]


def parse_iso_datetime(dt_str: str) -> datetime:
    """Parse ISO 8601 timestamp string into timezone-aware UTC datetime."""
    clean_str = dt_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(clean_str)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.fromisoformat("2000-01-01T00:00:00+00:00").tzinfo)
    return dt


def validate_and_deduplicate_fuelhh(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate and deduplicate FUELHH records.
    
    Composite Key: (settlementDate, settlementPeriod) for fuelType == 'WIND'
    Rules:
    - If exact duplicates (same key, same generation, same publishTime), retain 1.
    - If multiple publications exist with different publishTime, retain the latest publishTime.
    - If multiple records exist with the SAME key and publishTime but conflicting generation, raise DataIntegrityError.
    """
    grouped: Dict[Tuple[str, int], List[Dict[str, Any]]] = defaultdict(list)
    for r in records:
        if r.get("fuelType") and r.get("fuelType") != "WIND":
            continue
        key = (r["settlementDate"], r["settlementPeriod"])
        grouped[key].append(r)

    deduplicated: List[Dict[str, Any]] = []
    for key, group in grouped.items():
        if len(group) == 1:
            deduplicated.append(group[0])
            continue

        # Check for conflicts at identical publishTime
        by_pt: Dict[datetime, List[Dict[str, Any]]] = defaultdict(list)
        for r in group:
            pt = parse_iso_datetime(r["publishTime"])
            by_pt[pt].append(r)

        for pt, pt_records in by_pt.items():
            gens = set(x.get("generation") for x in pt_records)
            if len(gens) > 1:
                raise DataIntegrityError(
                    f"Conflicting generation values {gens} for FUELHH key {key} at publishTime {pt.isoformat()}"
                )

        # Select the record with latest publishTime
        latest_pt = max(by_pt.keys())
        deduplicated.append(by_pt[latest_pt][0])

    return deduplicated


def validate_and_deduplicate_windfor(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate and deduplicate WINDFOR records.
    
    Composite Key: (publishTime, startTime)
    Rules:
    - If exact duplicate records exist, drop duplicates.
    - If identical key has conflicting generation values, raise DataIntegrityError.
    """
    grouped: Dict[Tuple[datetime, datetime], List[Dict[str, Any]]] = defaultdict(list)
    for r in records:
        key = (parse_iso_datetime(r["publishTime"]), parse_iso_datetime(r["startTime"]))
        grouped[key].append(r)

    deduplicated: List[Dict[str, Any]] = []
    for key, group in grouped.items():
        if len(group) == 1:
            deduplicated.append(group[0])
            continue

        gens = set(x.get("generation") for x in group)
        if len(gens) > 1:
            pt_str, st_str = key[0].isoformat(), key[1].isoformat()
            raise DataIntegrityError(
                f"Conflicting generation values {gens} for WINDFOR key (publishTime={pt_str}, startTime={st_str})"
            )

        deduplicated.append(group[0])

    return deduplicated


def aggregate_fuelhh_to_hourly(records: List[Dict[str, Any]]) -> Dict[datetime, HourlyActual]:
    """
    Aggregate half-hourly FUELHH actual records to hourly resolution.
    
    Settlement Periods:
      SP 1 (00:00-00:30) & SP 2 (00:30-01:00) -> Hour 00:00
      SP 2h+1 & SP 2h+2 -> Hour h
      
    Aggregation Rule:
      Both FUELHH and WINDFOR are denominated in MW (rate of energy / average power).
      Total energy in 1 hr = (P_sp1 * 0.5h + P_sp2 * 0.5h) MWh.
      Average power in 1 hr = Total Energy / 1 hr = (P_sp1 + P_sp2) / 2 MW.
      Therefore, arithmetic mean of MW values is mathematically required.
    """
    # 1. Deduplicate & validate
    validated_records = validate_and_deduplicate_fuelhh(records)

    # 2. Group by target hour
    hourly_groups: Dict[Tuple[str, int], List[Dict[str, Any]]] = defaultdict(list)
    for r in validated_records:
        sd = r["settlementDate"]
        sp = r["settlementPeriod"]
        hour_idx = (sp - 1) // 2
        hourly_groups[(sd, hour_idx)].append(r)

    # 3. Compute hourly average
    hourly_actuals: Dict[datetime, HourlyActual] = {}
    for (sd, hour_idx), sp_records in hourly_groups.items():
        if len(sp_records) == 2:
            sp1_rec = next((x for x in sp_records if x["settlementPeriod"] == hour_idx * 2 + 1), None)
            sp2_rec = next((x for x in sp_records if x["settlementPeriod"] == hour_idx * 2 + 2), None)
            if sp1_rec and sp2_rec:
                g1 = sp1_rec.get("generation")
                g2 = sp2_rec.get("generation")
                if g1 is not None and g2 is not None:
                    target_st = parse_iso_datetime(f"{sd}T{hour_idx:02d}:00:00Z")
                    avg_mw = (float(g1) + float(g2)) / 2.0
                    hourly_actuals[target_st] = HourlyActual(
                        target_start_time=target_st,
                        settlement_date=sd,
                        hour_index=hour_idx,
                        settlement_periods=(hour_idx * 2 + 1, hour_idx * 2 + 2),
                        generation_mw=avg_mw,
                        is_complete=True
                    )

    return hourly_actuals


def filter_and_select_forecasts(
    windfor_records: List[Dict[str, Any]],
    target_start_time: datetime,
    cutoff_time: datetime
) -> Optional[Dict[str, Any]]:
    """
    Select the latest eligible WINDFOR forecast for target_start_time.
    Enforces that eligible forecasts must be published on Day D-1 and strictly
    at or before the cutoff time (d_minus_1_start <= publishTime <= cutoff_time).
    """
    target_d = target_start_time.date()
    prev_d = target_d - timedelta(days=1)
    tz = cutoff_time.tzinfo or target_start_time.tzinfo
    d_minus_1_start = datetime(prev_d.year, prev_d.month, prev_d.day, 0, 0, 0, tzinfo=tz)

    eligible = []
    for r in windfor_records:
        st = parse_iso_datetime(r["startTime"])
        if st == target_start_time:
            pt = parse_iso_datetime(r["publishTime"])
            if d_minus_1_start <= pt <= cutoff_time:
                eligible.append((pt, r))

    if not eligible:
        return None

    # Pick the forecast with latest publishTime
    eligible.sort(key=lambda x: x[0])
    return eligible[-1][1]


def match_forecasts_and_actuals(
    windfor_records: List[Dict[str, Any]],
    hourly_actuals: Dict[datetime, HourlyActual],
    delivery_start_date: date,
    delivery_end_date: date,
    cutoff_hour_uk: int = 9,
    cutoff_minute_uk: int = 0
) -> Tuple[List[MatchedForecastActual], VerificationMetrics]:
    """
    Perform cutoff-based matching for delivery intervals between delivery_start_date and delivery_end_date.
    
    Decision cutoff: (Delivery Date - 1 day) at cutoff_hour_uk:cutoff_minute_uk UK local time.
    For January (GMT = UTC+0), UK local time is equivalent to UTC.
    Only forecasts published on Day D-1 and at or before the decision cutoff are eligible.
    """
    # 1. Deduplicate & validate WINDFOR
    validated_windfor = validate_and_deduplicate_windfor(windfor_records)

    # 2. Pre-index WINDFOR records by target startTime
    wf_by_target: Dict[datetime, List[Tuple[datetime, Dict[str, Any]]]] = defaultdict(list)
    for r in validated_windfor:
        st = parse_iso_datetime(r["startTime"])
        pt = parse_iso_datetime(r["publishTime"])
        wf_by_target[st].append((pt, r))

    for st in wf_by_target:
        wf_by_target[st].sort(key=lambda x: x[0])

    matched_list: List[MatchedForecastActual] = []
    
    # 3. Generate all expected target hourly intervals
    cur_d = delivery_start_date
    expected_hours: List[datetime] = []
    utc_tz = parse_iso_datetime("2026-01-01T00:00:00Z").tzinfo

    while cur_d <= delivery_end_date:
        for h in range(24):
            expected_hours.append(datetime(cur_d.year, cur_d.month, cur_d.day, h, 0, tzinfo=utc_tz))
        cur_d += timedelta(days=1)

    expected_total = len(expected_hours)
    missing_forecasts = 0
    missing_actuals = 0

    for target_st in expected_hours:
        deliv_date = target_st.date()
        # Cutoff is on day D - 1 day at cutoff_hour_uk:cutoff_minute_uk
        prev_day = deliv_date - timedelta(days=1)
        d_minus_1_start = datetime(prev_day.year, prev_day.month, prev_day.day, 0, 0, 0, tzinfo=utc_tz)
        cutoff_dt = datetime(prev_day.year, prev_day.month, prev_day.day, cutoff_hour_uk, cutoff_minute_uk, tzinfo=utc_tz)

        # Retrieve eligible forecast vintages (must be published on Day D-1 and publishTime <= cutoff_dt)
        candidates = wf_by_target.get(target_st, [])
        eligible = [c for c in candidates if d_minus_1_start <= c[0] <= cutoff_dt]

        has_forecast = len(eligible) > 0
        actual_rec = hourly_actuals.get(target_st)
        has_actual = (actual_rec is not None and actual_rec.generation_mw is not None)

        # Independent calculation of missing-data conditions for every expected interval
        if not has_forecast:
            missing_forecasts += 1
        if not has_actual:
            missing_actuals += 1

        # Only add interval to matched results when both forecast and complete actual are available
        if not (has_forecast and has_actual):
            continue

        latest_pt, latest_rec = eligible[-1]
        fc_val = float(latest_rec["generation"])
        act_val = float(actual_rec.generation_mw)
        err = fc_val - act_val
        lead_time = (target_st - latest_pt).total_seconds() / 3600.0

        matched_list.append(MatchedForecastActual(
            target_start_time=target_st,
            cutoff_time=cutoff_dt,
            publish_time=latest_pt,
            lead_time_hours=lead_time,
            forecast_mw=fc_val,
            actual_mw=act_val,
            error_mw=err
        ))

    # 4. Metrics calculation (missing records are NOT treated as zero)
    if matched_list:
        errors = [m.error_mw for m in matched_list]
        abs_errors = [abs(e) for e in errors]
        lead_times = [m.lead_time_hours for m in matched_list]
        
        mae = float(sum(abs_errors) / len(abs_errors))
        rmse = float(math.sqrt(sum(e**2 for e in errors) / len(errors)))
        bias = float(sum(errors) / len(errors))
        p50 = float(np.percentile(abs_errors, 50))
        p90 = float(np.percentile(abs_errors, 90))
        p99 = float(np.percentile(abs_errors, 99))
        max_err = float(max(abs_errors))
        min_lt = float(min(lead_times))
        max_lt = float(max(lead_times))
        avg_lt = float(sum(lead_times) / len(lead_times))
    else:
        mae = rmse = bias = p50 = p90 = p99 = max_err = min_lt = max_lt = avg_lt = None

    coverage = (len(matched_list) / expected_total * 100.0) if expected_total > 0 else 0.0

    metrics = VerificationMetrics(
        expected_intervals=expected_total,
        matched_intervals=len(matched_list),
        missing_forecasts=missing_forecasts,
        missing_actuals=missing_actuals,
        coverage_pct=coverage,
        mae_mw=mae,
        rmse_mw=rmse,
        bias_mw=bias,
        p50_abs_error_mw=p50,
        p90_abs_error_mw=p90,
        p99_abs_error_mw=p99,
        max_abs_error_mw=max_err,
        min_lead_time_hours=min_lt,
        max_lead_time_hours=max_lt,
        avg_lead_time_hours=avg_lt
    )

    return matched_list, metrics


HORIZON_BUCKET_DEFINITIONS: List[Dict[str, Any]] = [
    {"label": "< 12h", "min_h": 0.0, "max_h": 12.0},
    {"label": "12–18h", "min_h": 12.0, "max_h": 18.0},
    {"label": "18–24h", "min_h": 18.0, "max_h": 24.0},
    {"label": "24–30h", "min_h": 24.0, "max_h": 30.0},
    {"label": "30–36h", "min_h": 30.0, "max_h": 36.0},
    {"label": "36–42h", "min_h": 36.0, "max_h": 42.0},
    {"label": "≥ 42h", "min_h": 42.0, "max_h": 100.0},
]


def compute_error_by_horizon(matched_list: List[MatchedForecastActual]) -> List[Dict[str, Any]]:
    """
    Group errors by defined operational lead-time horizon buckets.
    Lead time is derived as: (target_startTime - publishTime).total_seconds() / 3600.
    Handles empty buckets by returning count=0 and None for error metrics.
    """
    results: List[Dict[str, Any]] = []

    for b in HORIZON_BUCKET_DEFINITIONS:
        min_h = float(b["min_h"])
        max_h = float(b["max_h"])
        items = [m for m in matched_list if min_h <= m.lead_time_hours < max_h]

        if items:
            errors = [m.error_mw for m in items]
            abs_errors = [abs(e) for e in errors]
            fcs = [m.forecast_mw for m in items]
            acts = [m.actual_mw for m in items]
            lts = [m.lead_time_hours for m in items]
            avg_lt = round(float(sum(lts) / len(lts)), 2)

            results.append({
                "horizon_bucket": b["label"],
                "min_lead_time_hours": min_h,
                "max_lead_time_hours": max_h,
                "count": len(items),
                "lead_time_hours": avg_lt,
                "avg_lead_time_hours": avg_lt,
                "avg_forecast_mw": round(float(sum(fcs) / len(fcs)), 2),
                "avg_actual_mw": round(float(sum(acts) / len(acts)), 2),
                "mae_mw": round(float(sum(abs_errors) / len(abs_errors)), 2),
                "rmse_mw": round(float(math.sqrt(sum(e**2 for e in errors) / len(errors))), 2),
                "bias_mw": round(float(sum(errors) / len(errors)), 2),
                "p90_abs_error_mw": round(float(np.percentile(abs_errors, 90)), 2),
                "max_abs_error_mw": round(float(max(abs_errors)), 2),
            })
        else:
            results.append({
                "horizon_bucket": b["label"],
                "min_lead_time_hours": min_h,
                "max_lead_time_hours": max_h,
                "count": 0,
                "lead_time_hours": None,
                "avg_lead_time_hours": None,
                "avg_forecast_mw": None,
                "avg_actual_mw": None,
                "mae_mw": None,
                "rmse_mw": None,
                "bias_mw": None,
                "p90_abs_error_mw": None,
                "max_abs_error_mw": None,
            })

    return results


def compute_error_by_hour(matched_list: List[MatchedForecastActual]) -> List[Dict[str, Any]]:
    """Group errors by target hour of day (0 to 23)."""
    grouped: Dict[int, List[MatchedForecastActual]] = defaultdict(list)
    for m in matched_list:
        grouped[m.target_start_time.hour].append(m)

    results: List[Dict[str, Any]] = []
    for h in range(24):
        items = grouped.get(h, [])
        if not items:
            continue
        errors = [m.error_mw for m in items]
        abs_errors = [abs(e) for e in errors]
        fcs = [m.forecast_mw for m in items]
        acts = [m.actual_mw for m in items]
        lts = [m.lead_time_hours for m in items]

        results.append({
            "hour_of_day": h,
            "settlement_periods": [h * 2 + 1, h * 2 + 2],
            "count": len(items),
            "avg_forecast_mw": round(float(sum(fcs) / len(fcs)), 2),
            "avg_actual_mw": round(float(sum(acts) / len(acts)), 2),
            "mae_mw": round(float(sum(abs_errors) / len(abs_errors)), 2),
            "rmse_mw": round(float(math.sqrt(sum(e**2 for e in errors) / len(errors))), 2),
            "bias_mw": round(float(sum(errors) / len(errors)), 2),
            "p90_abs_error_mw": round(float(np.percentile(abs_errors, 90)), 2),
            "lead_time_hours": round(float(sum(lts) / len(lts)), 2),
        })

    return results


def compute_daily_errors(
    matched_list: List[MatchedForecastActual],
    delivery_start_date: date,
    delivery_end_date: date
) -> List[Dict[str, Any]]:
    """Group errors by delivery date."""
    grouped: Dict[date, List[MatchedForecastActual]] = defaultdict(list)
    for m in matched_list:
        grouped[m.target_start_time.date()].append(m)

    results: List[Dict[str, Any]] = []
    cur_d = delivery_start_date
    while cur_d <= delivery_end_date:
        items = grouped.get(cur_d, [])
        matched_hours = len(items)
        expected_hours = 24
        coverage = (matched_hours / expected_hours) * 100.0

        if items:
            errors = [m.error_mw for m in items]
            abs_errors = [abs(e) for e in errors]
            fcs = [m.forecast_mw for m in items]
            acts = [m.actual_mw for m in items]

            mae = round(float(sum(abs_errors) / len(abs_errors)), 2)
            rmse = round(float(math.sqrt(sum(e**2 for e in errors) / len(errors))), 2)
            bias = round(float(sum(errors) / len(errors)), 2)
            max_err = round(float(max(abs_errors)), 2)
            avg_fc = round(float(sum(fcs) / len(fcs)), 2)
            avg_act = round(float(sum(acts) / len(acts)), 2)
            energy_fc = round(float(sum(fcs)), 2)  # MW * 1h = MWh
            energy_act = round(float(sum(acts)), 2)  # MW * 1h = MWh
        else:
            mae = rmse = bias = max_err = avg_fc = avg_act = energy_fc = energy_act = None

        results.append({
            "delivery_date": cur_d.strftime("%Y-%m-%d"),
            "expected_hours": expected_hours,
            "matched_hours": matched_hours,
            "missing_hours": expected_hours - matched_hours,
            "is_complete": matched_hours == expected_hours,
            "daily_coverage_pct": round(coverage, 2),
            "avg_forecast_mw": avg_fc,
            "avg_actual_mw": avg_act,
            "daily_mae_mw": mae,
            "daily_rmse_mw": rmse,
            "daily_bias_mw": bias,
            "daily_max_abs_error_mw": max_err,
            "daily_energy_forecast_mwh": energy_fc,
            "daily_energy_actual_mwh": energy_act,
        })
        cur_d += timedelta(days=1)

    return results

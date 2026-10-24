"""
Pydantic API Schemas for Request & Response validation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class HealthResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "ok"})
    version: str = Field(..., json_schema_extra={"example": "1.0.0"})
    data_loaded: bool = Field(..., json_schema_extra={"example": True})
    fuelhh_records: int = Field(..., json_schema_extra={"example": 1536})
    windfor_records: int = Field(..., json_schema_extra={"example": 19856})
    message: Optional[str] = Field(None, json_schema_extra={"example": "Partial data load"})


class ForecastVsActualItem(BaseModel):
    target_start_time: str = Field(..., json_schema_extra={"example": "2026-01-01T00:00:00+00:00"})
    delivery_date: str = Field(..., json_schema_extra={"example": "2026-01-01"})
    hour_index: int = Field(..., json_schema_extra={"example": 0})
    cutoff_time: str = Field(..., json_schema_extra={"example": "2025-12-31T09:00:00+00:00"})
    publish_time: str = Field(..., json_schema_extra={"example": "2025-12-31T07:30:00+00:00"})
    lead_time_hours: float = Field(..., json_schema_extra={"example": 16.5})
    forecast_mw: float = Field(..., json_schema_extra={"example": 19412.0})
    actual_mw: float = Field(..., json_schema_extra={"example": 13814.5})
    error_mw: float = Field(..., json_schema_extra={"example": 5597.5})
    abs_error_mw: float = Field(..., json_schema_extra={"example": 5597.5})
    percentage_error: Optional[float] = Field(None, json_schema_extra={"example": 40.52})


class ForecastVsActualResponse(BaseModel):
    scope: Optional[str] = None
    start_date: str
    end_date: str
    cutoff_time: str
    expected_intervals: int
    matched_intervals: int
    coverage_pct: float
    data: List[ForecastVsActualItem]


class MetricsResponse(BaseModel):
    scope: Optional[str] = None
    start_date: str
    end_date: str
    cutoff_time: str
    expected_intervals: int
    matched_intervals: int
    missing_forecasts: int
    missing_actuals: int
    coverage_pct: float
    mae_mw: Optional[float] = None
    rmse_mw: Optional[float] = None
    bias_mw: Optional[float] = None
    p50_abs_error_mw: Optional[float] = None
    p90_abs_error_mw: Optional[float] = None
    p99_abs_error_mw: Optional[float] = None
    max_abs_error_mw: Optional[float] = None
    min_lead_time_hours: Optional[float] = None
    max_lead_time_hours: Optional[float] = None
    avg_lead_time_hours: Optional[float] = None


class ErrorByHorizonItem(BaseModel):
    horizon_bucket: str
    min_lead_time_hours: float
    max_lead_time_hours: float
    count: int
    lead_time_hours: Optional[float] = None
    avg_lead_time_hours: Optional[float] = None
    avg_forecast_mw: Optional[float] = None
    avg_actual_mw: Optional[float] = None
    mae_mw: Optional[float] = None
    rmse_mw: Optional[float] = None
    bias_mw: Optional[float] = None
    p90_abs_error_mw: Optional[float] = None
    max_abs_error_mw: Optional[float] = None


class ErrorByHourItem(BaseModel):
    hour_of_day: int
    settlement_periods: List[int]
    count: int
    avg_forecast_mw: float
    avg_actual_mw: float
    mae_mw: float
    rmse_mw: float
    bias_mw: float
    p90_abs_error_mw: float
    lead_time_hours: float


class DailyErrorItem(BaseModel):
    delivery_date: str
    expected_hours: int
    matched_hours: int
    missing_hours: int = 0
    is_complete: bool = True
    daily_coverage_pct: float
    avg_forecast_mw: Optional[float] = None
    avg_actual_mw: Optional[float] = None
    daily_mae_mw: Optional[float] = None
    daily_rmse_mw: Optional[float] = None
    daily_bias_mw: Optional[float] = None
    daily_max_abs_error_mw: Optional[float] = None
    daily_energy_forecast_mwh: Optional[float] = None
    daily_energy_actual_mwh: Optional[float] = None

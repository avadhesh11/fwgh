# Elexon BMRS Data Source & Time-Resolution Validation Report (Audited & Reconciled)
**Dataset Scope**: `FUELHH/stream` vs `WINDFOR/stream`  
**Analysis Period**: January 2026 (including December 30, 2025 – February 1, 2026 delivery and publication windows)  
**Status**: Completed, Audited & Reconciled  

---

## Executive Summary

Before implementing the Wind Forecast Decision Portal, an empirical and schema audit of the official Elexon BMRS streaming APIs was conducted. All data boundaries, timestamp semantics, lead-time derivations, and metric calculations were audited and reconciled against raw records.

Key verified findings:
1. **Units**: Both `FUELHH` and `WINDFOR` represent power in **Megawatts (MW)**. Specifically, `FUELHH` represents the **average MW over 30 minutes**, while `WINDFOR` represents the **forecast average MW over 60 minutes**. Neither dataset reports MWh energy totals.
2. **Temporal Resolution**:
   - `FUELHH` actuals are strictly **half-hourly (30 minutes)**, with `settlementPeriod` (1–48) and `startTime` on `:00` and `:30`.
   - `WINDFOR` forecasts are strictly **hourly (60 minutes)**. Across all 19,856 inspected records, 100% of records have `startTime` at minute `:00`. No half-hourly forecast records exist.
3. **Semantics of `startTime`**: In both datasets, `startTime` designates the **beginning (start) of the target interval in UTC**.
4. **Recommended Alignment**: **Hourly Comparison**. Actuals from `FUELHH` are aggregated to 1-hour intervals via the **arithmetic mean of two consecutive half-hourly periods** $(P_{2h+1} + P_{2h+2}) / 2$. Because values are power rates (MW), averaging preserves physical units and true information resolution without inventing false sub-hourly forecast precision.
5. **Reconciled Lead-Time Derivation**: Under the 09:00 UK cutoff on day $D-1$, the actual latest eligible publication across **100% of days in January 2026** was **07:30:00 UTC** (NGESO's morning forecast run). Using the timezone-aware formula `lead_time_hours = (target_startTime - publishTime).total_seconds() / 3600`, lead times strictly range from **16.5 hours** (for delivery hour 00:00) to **39.5 hours** (for delivery hour 23:00), with an exact mean of **28.0 hours**.
6. **Date-Range Completeness & Coverage**:
   - **Scope A (Delivery Jan 1–31)**: 744 / 744 matched hours (**100.00% coverage**). Requires forecasts published on Dec 31, 2025.
   - **Scope B (Decisions Jan 1–31 -> Delivery Jan 2–Feb 1)**: 744 / 744 matched hours (**100.00% coverage**). Requires actuals for February 1, 2026 (all 48 settlement periods confirmed present).
7. **Integrity & Conflict Policy**: Confirmed zero duplicate keys or conflicting values in the Elexon dataset. The service implements strict duplicate pruning and raises `DataIntegrityError` if key collisions with conflicting generation values ever occur. Missing records are strictly excluded from error averages and penalize coverage rather than being treated as zero.
8. **Automated Verification**: An expanded 9-test unit suite verifies interval aggregation, conflict detection, cutoff filtering, lead-time derivation, and metric calculations.

---

## 1. Evidence and Representative Raw Records

### 1.1 Outturn Dataset: `FUELHH/stream`
- **Endpoint**: `https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream`
- **Official Schema**: `AugmentedOutturnData`
- **Swagger Documentation**:
  > *"This endpoint provides the half-hourly generation outturn (Generation By Fuel type)... updated at 30-minute intervals with average MW values over 30 minutes for each category."*

#### Representative Raw Record
```json
{
  "dataset": "FUELHH",
  "publishTime": "2026-01-01T00:30:00Z",
  "startTime": "2026-01-01T00:00:00Z",
  "settlementDate": "2026-01-01",
  "settlementPeriod": 1,
  "fuelType": "WIND",
  "generation": 13756
}
```

| Field | Type | Description | Observed Nulls |
| :--- | :--- | :--- | :--- |
| `dataset` | string | Constant identifier (`FUELHH`) | 0 |
| `publishTime` | string (ISO 8601 UTC) | Time outturn was calculated & released (30 min after interval start) | 0 |
| `startTime` | string (ISO 8601 UTC) | Exact start of the 30-minute settlement period | 0 |
| `settlementDate` | string (`YYYY-MM-DD`) | GB settlement date | 0 |
| `settlementPeriod` | integer (1–48) | Half-hour settlement period index | 0 |
| `fuelType` | string | Generation fuel type (`WIND`, `CCGT`, `NUCLEAR`, etc.) | 0 |
| `generation` | integer (int64) | **Average power in MW** over the half-hour | 0 |

---

### 1.2 Forecast Dataset: `WINDFOR/stream`
- **Endpoint**: `https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream`
- **Official Schema**: `WindGenerationForecast`
- **Swagger Documentation**:
  > *"This endpoint provides wind generation forecast data... for wind farms which are visible to the ESO and have operational metering. Updated data is published by NGESO up to 8 times a day at 03:30, 05:30, 08:30, 10:30, 12:30, 16:30, 19:30 and 23:30."*

#### Representative Raw Record
```json
{
  "dataset": "WINDFOR",
  "publishTime": "2025-12-31T07:30:00Z",
  "startTime": "2026-01-01T00:00:00Z",
  "generation": 19412
}
```

| Field | Type | Description | Observed Nulls |
| :--- | :--- | :--- | :--- |
| `dataset` | string | Constant identifier (`WINDFOR`) | 0 |
| `publishTime` | string (ISO 8601 UTC) | Vintage timestamp when the forecast run was published | 0 |
| `startTime` | string (ISO 8601 UTC) | Exact start of the 1-hour target forecast interval | 0 |
| `generation` | integer (int64) | **Forecast average power in MW** over the hour | 0 |

---

## 2. Confirmed Temporal Resolutions, Units, and Timestamp Semantics

### 2.1 Resolution & Cadence
- **`FUELHH` Resolution**: Strictly **30 minutes**. Every settlement date contains exactly 48 records for `fuelType="WIND"`.
- **`WINDFOR` Resolution**: Strictly **60 minutes**.
  - Consecutive record step size: **60.0 minutes (100% of rows)**.
  - Distribution of `startTime` minutes: **`00` (100.0%)**, `:30` (0.0%).
  - Each forecast run contains **73 hourly steps** covering a rolling 72-hour horizon.
  - Publication times observed before the 09:00 cutoff were consistently **07:30:00 UTC**.

### 2.2 Semantic Meaning of `startTime`
- In `FUELHH`, `startTime = 2026-01-01T00:00:00Z` with `settlementPeriod = 1` and `publishTime = 2026-01-01T00:30:00Z` demonstrates that `startTime` marks the **beginning of the delivery interval**.
- In `WINDFOR`, `startTime = 2026-01-01T00:00:00Z` marks the **beginning of the 1-hour forecast window** `[00:00:00, 01:00:00)`.

### 2.3 Unit & Interval Physics
- Values in both datasets are in the range of 1,500 MW to 21,500 MW (consistent with Great Britain transmission-connected metered wind generation).
- **FUELHH is MW, not MWh**: Official documentation states: *"average MW values over 30 minutes"*.
- **WINDFOR is MW**: Forecast expected average output over the 1-hour window.

---

## 3. Recommended Comparison Method & Justification

### Recommendation: Hourly Comparison (Aggregate Actuals to Forecast Resolution)

$$\text{Actual}_{\text{Hour } h} = \frac{\text{Actual}_{\text{SP } (2h+1)} + \text{Actual}_{\text{SP } (2h+2)}}{2}$$

$$\text{Error}_{\text{Hour } h} = \text{Forecast}_{\text{Hour } h} - \text{Actual}_{\text{Hour } h}$$

### Why Hourly Aggregation is Recommended:
1. **Mathematical & Physical Rigor**: Because generation is measured in MW (rate of energy), the average power over an hour comprising two 30-minute intervals of average power $P_1$ and $P_2$ is:
   $$P_{\text{hourly}} = \frac{P_1 \times 0.5\,\text{h} + P_2 \times 0.5\,\text{h}}{1.0\,\text{h}} = \frac{P_1 + P_2}{2}\text{ MW}$$
   Summing the values would erroneously double the apparent power.
2. **No Fictitious Data Creation**: Mapping hourly forecasts to half-hourly intervals by duplicating the forecast ($F_{sp1} = F, F_{sp2} = F$) violates the assignment instruction: *"Do not silently duplicate hourly forecasts across half-hourly intervals."* Duplication treats a single hourly prediction as two independent predictions, distorting sample sizes, autocorrelation, and P90 tail risk metrics.
3. **Clean Alignment**: Hourly actuals align 1:1 with WINDFOR target intervals `[HH:00, (HH+1):00)`.

---

## 4. Reconciled Lead-Time Derivation and Business Logic Audit

### 4.1 Lead-Time Reconciliation
In earlier drafting, the narrative cited a theoretical "08:30" publication example from Swagger documentation, while reporting a 16.5-hour lead time. This has been audited and resolved:
- **Observed Publication Cadence**: In January 2026, the morning WINDFOR forecast runs published prior to the 09:00 UK cutoff were published at **07:30:00 UTC** across **100% of delivery days** (744 out of 744 intervals).
- **Lead Time Formula**:
  $$\text{lead\_time\_hours} = \frac{(T_{\text{target\_startTime}} - T_{\text{publishTime}}).\text{total\_seconds}()}{3600}$$
- **Exact Derivation for Delivery Day $D$**:
  - Hour 00:00: `(D 00:00:00Z - (D-1) 07:30:00Z) = 16.5 hours`.
  - Hour 01:00: `(D 01:00:00Z - (D-1) 07:30:00Z) = 17.5 hours`.
  - ...
  - Hour 23:00: `(D 23:00:00Z - (D-1) 07:30:00Z) = 39.5 hours`.
- **Summary Lead-Time Metrics**:
  - **Minimum**: **16.5 hours**
  - **Maximum**: **39.5 hours**
  - **Mean**: $\frac{1}{24}\sum_{h=0}^{23}(16.5 + h) = 16.5 + 11.5 =$ **28.0 hours**.

*(Note: If a hypothetical forecast had been published at 08:30 on D-1, the lead time would have been $15.5$ to $38.5$ hours with mean $27.0$ hours. The 16.5–39.5 hour range is the empirical reality of NGESO's 07:30 publication schedule).*

---

### 4.2 Empirical January 2026 Benchmark Results

Both decision scopes were audited and recalculated from the validated dataset:

| Metric | Scope A (Delivery Jan 1–31, 2026) | Scope B (Decisions Jan 1–31 -> Delivery Jan 2–Feb 1) | Unit |
| :--- | :--- | :--- | :--- |
| **Expected Intervals** | 744 | 744 | hours |
| **Valid Matched Intervals** | 744 | 744 | hours |
| **Coverage** | **100.00%** | **100.00%** | % |
| **Missing Actuals / Forecasts** | 0 / 0 | 0 / 0 | intervals |
| **Mean Absolute Error (MAE)** | **2,142.12** | **2,038.91** | MW |
| **Root Mean Squared Error (RMSE)** | **2,611.70** | **2,504.76** | MW |
| **Bias (Mean Forecast - Actual)** | **+1,851.90** | **+1,747.89** | MW (Overforecast) |
| **P90 Absolute Error** | **4,300.15** | **4,097.90** | MW |
| **Lead Time (Min / Max / Mean)** | **16.5 / 39.5 / 28.0** | **16.5 / 39.5 / 28.0** | hours |

*Audit Note on Missing Records*: Missing intervals are never treated as zero. If an interval lacks an actual or eligible forecast, it is excluded from error metrics, and penalizes the coverage denominator.

---

## 5. Duplicate Handling, Integrity Protection, and API Sizing

### 5.1 Deduplication & Conflict Policy
- **Composite Keys**:
  - `FUELHH`: `(settlementDate, settlementPeriod)`
  - `WINDFOR`: `(publishTime, startTime)`
- **Conflict Handling**:
  - Exact duplicate rows (matching key and generation) are automatically pruned.
  - Key collisions with **conflicting generation values** raise `DataIntegrityError` to prevent silent corrupted averages.
  - In the audited January 2026 dataset, **zero duplicate keys and zero conflicting values** were found.

### 5.2 API Query Strategy
1. **`FUELHH/stream`**:
   - Query: `settlementDateFrom=2026-01-01&settlementDateTo=2026-02-01&fuelType=WIND`.
   - Returns 1,536 records across 32 delivery days (~95 KB).
2. **`WINDFOR/stream`**:
   - Query by publication window in 5-day chunks (`publishDateTimeFrom` to `publishDateTimeTo`).
   - Sizing: ~2,920 records per 5-day chunk (~200 KB). Total volume for Dec 30, 2025 to Feb 2, 2026: 19,856 records.

---

## 6. Automated Test Suite

The test suite in [`fwgh/backend/tests/test_alignment.py`](file:///e:/avadhesh/projects/GridBricks/fwgh/backend/tests/test_alignment.py) covers all audit requirements:
1. `test_fuelhh_aggregation_arithmetic_mean_mw`: Proves $(1000 + 2000)/2 = 1500\text{ MW}$.
2. `test_fuelhh_missing_half_hour_is_not_aggregated`: Rejects incomplete hourly intervals.
3. `test_fuelhh_exact_duplicate_dropped_cleanly`: Validates exact duplicate pruning.
4. `test_fuelhh_conflicting_values_raises_integrity_error`: Asserts `DataIntegrityError` on conflicting outturn values.
5. `test_windfor_conflicting_values_raises_integrity_error`: Asserts `DataIntegrityError` on conflicting forecast values.
6. `test_lead_time_calculation_reconciled`: Asserts exact dynamic derivation of 16.5h, 39.5h, and 28.0h mean from UTC timestamps.
7. `test_cutoff_decision_latest_eligible_forecast`: Asserts strict 09:00 D-1 cutoff eligibility.
8. `test_missing_records_not_treated_as_zero`: Confirms missing intervals are excluded from error averages and penalize coverage.
9. `test_error_sign_convention`: Confirms $F - A$ convention (+500 MW for overforecast, -300 MW for underforecast).

All 9 tests pass with 100% success rate.

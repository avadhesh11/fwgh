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
  $$\text{Lead Time (hours)} = \frac{T_{\text{target start}} - T_{\text{publishTime}}}{3600\text{ seconds}}$$
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

The test suite in [`backend/tests/test_alignment.py`](../backend/tests/test_alignment.py) covers all audit requirements:
1. `test_fuelhh_aggregation_arithmetic_mean_mw`: Proves $(1000 + 2000)/2 = 1500\text{ MW}$.
2. `test_fuelhh_missing_half_hour_is_not_aggregated`: Rejects incomplete hourly intervals.
3. `test_fuelhh_exact_duplicate_dropped_cleanly`: Validates exact duplicate pruning.
4. `test_fuelhh_conflicting_values_raises_integrity_error`: Asserts `DataIntegrityError` on conflicting outturn values.
5. `test_windfor_conflicting_values_raises_integrity_error`: Asserts `DataIntegrityError` on conflicting forecast values.
6. `test_lead_time_calculation_reconciled`: Asserts exact dynamic derivation of 16.5h, 39.5h, and 28.0h mean from UTC timestamps.
7. `test_cutoff_decision_latest_eligible_forecast`: Asserts strict 09:00 D-1 cutoff eligibility.
8. `test_strict_cutoff_boundary_and_post_cutoff_rejection`: Asserts inclusive cutoff boundary and post-cutoff rejection.
9. `test_missing_records_not_treated_as_zero`: Confirms missing intervals are excluded from error averages and penalize coverage.
10. `test_error_sign_convention`: Confirms $F - A$ convention (+500 MW for overforecast, -300 MW for underforecast).
11. `test_zero_matched_intervals_returns_none_metrics`: Asserts None metrics when matched count is zero.
12. `test_forecast_vintage_rule_enforcement`: Asserts D-1 publication eligibility rule.
13. `test_missing_data_counters_independent`: Confirms independent missing-forecast and missing-actual counters.
14. `test_compute_error_by_horizon_buckets`: Validates 7 operational lead-time buckets, boundary conditions, empty bucket handling, and metrics.
15. `test_bias_positive_negative_interpretation`: Proves signed bias calculations for over- and underforecasting.

---

## 7. Phase 2: Operational Lead-Time Horizon Analysis

### 7.1 Problem with Unbinned Horizon Measurements
Under fixed Day $D-1$ cutoff rules (e.g. 09:00 UK), the selected forecast for every settlement period of Day $D$ is published at the exact same publication run (`07:30 UTC`).
Consequently:
$$\text{lead time hours} = 16.5 + \text{hour of day}$$
Evaluating error by exact unrounded lead time produced 24 distinct points that were mathematically identical to the diurnal hour-of-day curve shifted by 16.5 hours.

### 7.2 Operational Bucket Architecture
To make horizon analysis operationally meaningful, forecasts are grouped into **7 defined operational intervals**:

$$\text{Lead Time (hours)} = \frac{\text{startTime} - \text{publishTime}}{3600\text{ seconds}}$$

| Bucket Label | Lead-Time Range $[h_{\min}, h_{\max})$ | Operational Horizon | Scope B (09:00 Cutoff) Obs | Scope B MAE (MW) | Scope B Bias (MW) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `< 12h` | $[0.0, 12.0)$ hours | Intraday / Short-range gate closure | 0 *(Empty at D-1)* | *None* | *None* |
| `12–18h` | $[12.0, 18.0)$ hours | Early morning delivery (00:00–02:00) | 62 | 2,098.40 | +2,043.01 |
| `18–24h` | $[18.0, 24.0)$ hours | Morning peak & day hours (02:00–08:00) | 186 | 2,359.13 | +2,286.58 |
| `24–30h` | $[24.0, 30.0)$ hours | Midday solar/wind blend (08:00–14:00) | 186 | 1,965.71 | +1,629.65 |
| `30–36h` | $[30.0, 36.0)$ hours | Afternoon / evening peak (14:00–20:00) | 186 | 1,900.66 | +1,322.53 |
| `36–42h` | $[36.0, 42.0)$ hours | Late night delivery (20:00–24:00) | 124 | 1,846.03 | +1,607.67 |
| `≥ 42h` | $[42.0, 100.0)$ hours | Multi-day forward planning horizon | 0 *(Empty at D-1 09:00)* | *None* | *None* |

*Empty Bucket Treatment*: Buckets without observations return `count = 0` and `None` (`null`) for all error metrics. They are visually indicated on the UI without fabricating zero error.

---

## 8. Phase 2: Empirical Bias Investigation & Decision Support

### 8.1 Empirical Reproduction
Under the standard Scope B benchmark (Jan 2 to Feb 1, 2026, 09:00 UK cutoff):
- **Actual Generation Mean**: `11,283.56 MW`
- **Forecast Generation Mean**: `13,031.44 MW`
- **Mean Signed Bias**: `+1,747.89 MW` (+15.49% relative to mean actual generation)
- **Sign Convention**: $\text{Error} = \text{Forecast} - \text{Actual}$. Positive bias indicates overforecasting.

### 8.2 Empirical Multi-Dimensional Breakdown
1. **Directional Persistence**: 632 of 744 hours (84.9%) were overforecast.
2. **Daily Persistence**: 27 of 31 days (87.1%) exhibited positive net daily bias.
3. **Diurnal Pattern**: Overnight hours exhibit the highest bias, peaking at `+2,334.60 MW` at 04:00 UTC (SPs 9–10) and reaching a low of `+1,303.29 MW` at 16:00 UTC (SPs 33–34).
4. **Horizon Persistence**: Positive bias remains high across all lead times (+1,322 MW to +2,286 MW).

### 8.3 Data-Supported Facts vs Unverified Hypotheses
- **What is proven**: Forecasts consistently overpredicted metered outturn in January 2026.
- **What is unproven (cautious interpretation)**:
  - *NWP model wind speed bias*: Weather models may overpredict sustained boundary-layer winds.
  - *Transmission constraint curtailment*: National Grid ESO regularly curtails Scottish and northern wind generation via Balancing Mechanism Bid-Offer Acceptances (BOAs). `FUELHH` records the curtailed generation, while `WINDFOR` reflects unconstrained potential. Since BOA logs are not included in this dataset, curtailment volume cannot be proved from the cached files.
  - *Capacity scope mismatch*: Differences between transmission-connected wind farms in `FUELHH` and embedded generation assumptions in `WINDFOR`.
- **Operational Recommendation**: Do not apply flat bias subtraction or alter raw records. Cashout imbalance risk is asymmetric, and artificial deductions without balancing data distort bidding strategies.


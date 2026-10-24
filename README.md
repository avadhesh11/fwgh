# Wind Forecast Decision Portal — Great Britain (BMRS)

A full-stack energy analytics and verification platform that evaluates day-ahead wind generation forecasts against actual metered generation across Great Britain under strict decision cutoffs.

Built with a **FastAPI** backend and a **React 19 + TypeScript + Vite** frontend.

---

## Live Demo

* **Live Demo URL**: `https://gridbricks.example.com` *(Deployment placeholder — to be updated upon live hosting)*
* **Backend Health Check**: `http://localhost:8000/api/health`
* **Swagger API Docs**: `http://localhost:8000/docs`

---

## 1. System Architecture

```
                                      +-------------------------------+
                                      |    User / Trading Browser     |
                                      +---------------+---------------+
                                                      |
                                             HTTP :80 / :5173
                                                      v
                                      +-------------------------------+
                                      |   Frontend (React + Nginx)    |
                                      |   - Trading Terminal UI       |
                                      |   - Recharts Visualizations   |
                                      |   - Nginx Reverse Proxy /api/ |
                                      +---------------+---------------+
                                                      |
                                            HTTP Proxy /api/ -> :8000
                                                      v
                                      +-------------------------------+
                                      |     Backend (FastAPI REST)    |
                                      |   - /api/health               |
                                      |   - /api/metrics              |
                                      |   - /api/forecast-vs-actual   |
                                      |   - /api/error-by-horizon     |
                                      |   - /api/error-by-hour        |
                                      |   - /api/daily-errors         |
                                      +---------------+---------------+
                                                      |
                                            In-Memory Cached Data
                                                      v
                                      +-------------------------------+
                                      |   Validated Elexon Datasets   |
                                      |   - FUELHH: 1,536 intervals   |
                                      |   - WINDFOR: 19,856 records   |
                                      +-------------------------------+
```

---

## 2. Methodology & Alignment Rules

### A. Data Provenance & Source Streams
All raw market data originates from official **Elexon BMRS** API streams:
1. **Actual Generation**: `FUELHH/stream` (`fuelType = "WIND"`), reporting metered half-hourly generation in megawatts (MW).
2. **Forecast Generation**: `WINDFOR/stream`, reporting national wind generation forecasts in megawatts (MW) published at periodic intervals for forward settlement periods.

### B. UTC Timestamp Alignment & Hourly Aggregation
* Electricity market settlement periods are half-hourly (SPs 1 to 48).
* In Great Britain, hour $H$ (from $H$:00 to $H+1$:00 UTC) consists of settlement periods $2H + 1$ and $2H + 2$.
* Hourly actual generation is computed as the **arithmetic mean** of the two half-hourly periods:
  $$\text{Actual}_H = \frac{P_{2H+1} + P_{2H+2}}{2}\quad (\text{MW})$$
* **Strict Completeness Requirement**: If either half-hour period is missing, the target hour is marked as missing. Missing observations are never filled or treated as zero.

### C. Forecast Vintage & Cutoff Decision Rule
* In day-ahead electricity markets, trading decisions are finalized by a cutoff time on Day $D-1$.
* **Vintage Eligibility Rule**: For target delivery date $D$, only forecasts published on Day $D-1$ strictly at or before the decision cutoff are eligible:
  $$\text{publishTime} \le \text{cutoff\_datetime}_{D-1}$$
* Out of all eligible forecasts, the **latest published forecast** is selected to reflect the most current information available to the decision-maker.
* Forecasts published after the cutoff time are strictly rejected.

### D. Pilot Decision Cutoff Assumption
* Default pilot cutoff: **09:00 UK local time** on Day $D-1$.
* In January (UTC = GMT), 09:00 UK local time corresponds exactly to `09:00:00Z`.
* Under this cutoff, the latest eligible publication in the dataset is published at `07:30:00Z` on Day $D-1$, giving a lead time range of **16.5 hours to 39.5 hours** (mean: **28.0 hours**).
* Changing cutoff to `04:00` selects the forecast published at `02:30:00Z` on Day $D-1$, expanding lead times to **21.5h to 44.5h** (mean: **33.0 hours**).

### E. Error Sign Convention
$$\text{Error} = \text{Forecast} - \text{Actual}$$
* **Positive Bias ($\text{Error} > 0$)**: Indicates persistent **overforecasting** (forecast exceeded actual outturn).
* **Negative Bias ($\text{Error} < 0$)**: Indicates **underforecasting**.

### F. Cached Dataset Date Boundaries & Server-Side Validation
The repository contains validated, locally cached JSON datasets in `backend/data/`:
* **Cached Actuals**: January 1, 2026 00:00 UTC through February 1, 2026 23:30 UTC (1,536 half-hourly intervals = 768 target delivery hours).
* **Cached Forecasts**: December 30, 2025 00:00 UTC through February 2, 2026 00:00 UTC (19,856 forecast records).
* **Evaluation Scopes Supported**:
  - **Scope A**: Delivery dates January 1–31, 2026 (744 hours, 100% complete coverage).
  - **Scope B (Default)**: Decision dates January 1–31, 2026 $\rightarrow$ Delivery dates January 2–February 1, 2026 (744 hours, 100% complete coverage).
* **Server-Side Validation**: The supported delivery window is strictly **January 1, 2026 through February 1, 2026** (`2026-01-01` to `2026-02-01`). Requests specifying delivery dates outside this supported window, inverted date ranges (`start_date > end_date`), or partial date inputs are rejected with **HTTP 400 Bad Request** and a clear error message, preventing silent or misleading empty results.

---

## 3. Verified Benchmark Metrics

### Scope B (Default — Decisions Jan 1–31, 2026 -> Delivery Jan 2–Feb 1, 2026; Cutoff 09:00 UK)
* **MAE**: `2,038.91 MW`
* **RMSE**: `2,504.76 MW`
* **Mean Bias**: `+1,747.89 MW` (Overforecasting)
* **P90 Absolute Error**: `4,097.90 MW`
* **Coverage**: `100.00%` (744 / 744 target intervals)
* **Lead Time**: Min `16.5h`, Max `39.5h`, Mean `28.0h`

### Scope A (Delivery Jan 1–31, 2026; Cutoff 09:00 UK)
* **MAE**: `2,142.12 MW`
* **RMSE**: `2,611.70 MW`
* **Mean Bias**: `+1,851.90 MW` (Overforecasting)
* **P90 Absolute Error**: `4,300.15 MW`
* **Coverage**: `100.00%` (744 / 744 target intervals)
* **Lead Time**: Min `16.5h`, Max `39.5h`, Mean `28.0h`

### Scope A Sensitivity (Delivery Jan 1–31, 2026; Cutoff 04:00 UK)
* **MAE**: `2,199.81 MW`
* **RMSE**: `2,691.79 MW`
* **Mean Bias**: `+1,862.38 MW`
* **P90 Absolute Error**: `4,385.25 MW`
* **Coverage**: `100.00%` (744 / 744 target intervals)
* **Lead Time**: Min `21.5h`, Max `44.5h`, Mean `33.0h`

---

### 3.1 Forecast-Horizon Operational Lead-Time Analysis

In electricity market operations, grouping observations purely by unrounded raw lead time or delivery hour conflates diurnal intra-day patterns with forecast horizon effects. Under a fixed cutoff, $\text{lead\_time} = \text{base\_offset} + \text{hour\_of\_day}$, making a point-by-point lead-time curve identical to a shifted diurnal error curve.

To provide meaningful decision support across decision stages, forecast error is evaluated across **7 defined operational lead-time horizon buckets**:

$$\text{Lead Time (hours)} = \frac{\text{startTime} - \text{publishTime}}{3600\text{ seconds}}$$

| Bucket Label | Lead-Time Range $[h_{\min}, h_{\max})$ | Operational Context | Scope B (09:00 Cutoff) Obs | Scope B MAE (MW) | Scope B Bias (MW) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `< 12h` | $[0.0, 12.0)$ hours | Intraday / Short-range gate closure | 0 *(Empty at D-1)* | *None* | *None* |
| `12–18h` | $[12.0, 18.0)$ hours | Early morning delivery (00:00–02:00) | 62 | 2,098.40 | +2,043.01 |
| `18–24h` | $[18.0, 24.0)$ hours | Morning peak & day hours (02:00–08:00) | 186 | 2,359.13 | +2,286.58 |
| `24–30h` | $[24.0, 30.0)$ hours | Midday solar/wind blend (08:00–14:00) | 186 | 1,965.71 | +1,629.65 |
| `30–36h` | $[30.0, 36.0)$ hours | Afternoon / evening peak (14:00–20:00) | 186 | 1,900.66 | +1,322.53 |
| `36–42h` | $[36.0, 42.0)$ hours | Late night delivery (20:00–24:00) | 124 | 1,846.03 | +1,607.67 |
| `≥ 42h` | $[42.0, 100.0)$ hours | Multi-day forward planning horizon | 0 *(Empty at D-1 09:00)* | *None* | *None* |

*Empty Bucket Safeguard*: Buckets without observations return `count = 0` and `null` for MAE, RMSE, and bias. The system never injects synthetic zero-valued errors. When cutoff shifts to `04:00`, lead times shift rightward into longer buckets (`≥ 42h` receives 93 observations, `< 18h` becomes empty).

---

### 3.2 Empirical Bias Investigation & Decision-Support Quality

#### 1. Empirical Finding Reproduction
Under the standard Scope B benchmark (Jan 2 to Feb 1, 2026, 09:00 UK cutoff), the platform reproduces the reported positive bias:
* **Mean Actual Generation**: `11,283.56 MW`
* **Mean Forecast Generation**: `13,031.44 MW`
* **Mean Signed Bias**: `+1,747.89 MW` (+15.49% relative to mean actual generation)
* **Sign Convention**: $\text{Error} = \text{Forecast} - \text{Actual}$. A positive bias demonstrates that forecasts systematically exceeded actual generation outturns.

#### 2. Temporal & Diurnal Variation
* **Directional Persistence**: **632 out of 744 hours (84.9%)** exhibited overforecasting ($\text{Forecast} > \text{Actual}$).
* **Daily Persistence**: **27 out of 31 delivery days (87.1%)** had a net positive daily bias. Daily bias ranged from a mild underforecast of `-730.06 MW` (Jan 19) to a peak overforecast of `+5,374.79 MW` (Jan 28).
* **Diurnal Peak Deviation**: Bias is systematically higher overnight, reaching a maximum of `+2,334.60 MW` at **04:00 UTC** (SPs 9–10), and dipping to a minimum of `+1,303.29 MW` during the afternoon peak demand ramp at **16:00 UTC** (SPs 33–34).
* **Horizon Invariance**: Overforecast persists stubbornly across all lead times (+1,322 MW to +2,286 MW across 12h to 42h), proving that overprediction is not simply a degradation of longer-range forecasts.

#### 3. Analytical Interpretation & Decision-Support Boundaries
* **What the Data Establishes**: Forecasts consistently overstate metered generation in the audited January 2026 Elexon dataset.
* **Unproven Operational Hypotheses (Caution)**:
  1. *Meteorological / NWP Modeling*: Numerical weather prediction models may over-estimate sustained low-level wind speeds during Atlantic winter depressions.
  2. *System Operator Balancing Curtailment*: Under high wind conditions, National Grid ESO frequently curtails wind farms via Balancing Mechanism Bid-Offer Acceptances (BOAs) due to Scottish transmission export bottlenecks (B6 boundary). Metered actual generation (`FUELHH`) reflects constrained output, whereas raw `WINDFOR` reflects unconstrained available wind potential.
  3. *Metering Boundary Discrepancies*: Variations between transmission-connected wind farms in `FUELHH` and embedded (distribution-connected) wind modeled in national forecasting tools.
* **Operational Decision Rule**: The application strictly avoids applying artificial post-processing offsets or modifying benchmark baselines. In energy trading and balancing markets, imbalance cashout prices are asymmetric; naive bias subtraction without balancing mechanism bid data risks creating severe commercial imbalance exposure.

---

## 4. API Endpoints

All backend endpoints are prefixed with `/api`. Interactive documentation is available at `/docs` (Swagger UI).

| Endpoint | Method | Query Parameters | Description |
| :--- | :--- | :--- | :--- |
| `/api/health` | `GET` | *None* | Health status, version, data load status, and record counts. |
| `/api/forecast-vs-actual` | `GET` | `scope`, `cutoff_time`, `start_date`, `end_date` | Hourly matched series (forecast MW, actual MW, signed error, lead time, publish time). |
| `/api/metrics` | `GET` | `scope`, `cutoff_time`, `start_date`, `end_date` | Summary statistics (MAE, RMSE, Bias, P50, P90, P99, Max error, Coverage %, Lead time). |
| `/api/error-by-horizon` | `GET` | `scope`, `cutoff_time`, `start_date`, `end_date` | Error statistics grouped by 7 operational lead-time horizon buckets (<12h to ≥42h). |
| `/api/error-by-hour` | `GET` | `scope`, `cutoff_time`, `start_date`, `end_date` | Diurnal profile across the 24 hours of the day (SPs 1 to 48). |
| `/api/daily-errors` | `GET` | `scope`, `cutoff_time`, `start_date`, `end_date` | Daily aggregated errors, daily coverage %, and energy totals (MWh) with completeness flags. |

---

## 5. Environment Variables

### Backend Configuration
| Variable | Description | Default |
| :--- | :--- | :--- |
| `DATA_DIR` | Absolute or relative path to directory containing raw JSON cache files. | `/app/data` (in container) or `backend/data` |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins (no permissive wildcards with credentials). | `http://localhost:5173,http://127.0.0.1:5173,http://localhost:80,http://127.0.0.1:80,http://localhost,http://127.0.0.1` |
| `PORT` | Port for the uvicorn HTTP server. | `8000` |

### Frontend Configuration
| Variable | Description | Default |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Base URL for FastAPI backend endpoints passed at build time or runtime. | `/api` (relative path routed via Nginx proxy in production or Vite dev proxy) |

---

## 6. Running with Docker Compose (Recommended)

### Prerequisites
Docker 20.10+ and Docker Compose v2+.

### Build & Run Full Stack
From the project root:
```bash
docker compose up --build -d
```

### Accessing the Deployed Application
* **Frontend Portal**: Open [http://localhost](http://localhost) in your browser.
* **Backend Healthcheck**: `curl http://localhost:8000/api/health`
* **Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### Stopping Containers
```bash
docker compose down
```

---

## 7. Running Locally Without Docker

### Step 1: Run Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate | Unix: source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Backend runs at `http://127.0.0.1:8000`.

### Step 2: Run Frontend
In a second terminal:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser. Vite automatically proxies `/api` requests to `http://localhost:8000`.

---

## 8. Test Execution

### Backend Automated Test Suite (37 tests)
```bash
cd backend
python -m pytest tests/ -v
```
All 37 tests pass, covering alignment rules, duplicate pruning, integrity error handling, vintage eligibility (Day D-1 at or before cutoff), independent missing data counters, real-data regression baselines for Scope A and B, cutoff boundaries, server-side supported date range validation, nullable metrics on zero matches, accurate `/health` status and safe diagnostics, unhandled exception 500 handling, and explicit CORS headers.

### Frontend Test Suite (18 tests)
```bash
cd frontend
npm test -- --run
```
All 18 component and integration tests pass, verifying KPI formatting, Scope B default selection, custom date range badges and input bounds, cutoff sensitivity updates, zero-match alerts, daily completeness flags, horizon error buckets, diurnal error profile, and user-friendly error alerts on network or server failures.

### Frontend Production Bundle Build
```bash
cd frontend
npm run build
```
Type checks and bundles the client app cleanly into `dist/`.

---

## 9. AI Tool Disclosure

AI development tools, including Antigravity, were used to assist with code implementation, debugging, testing, and documentation. The developer remains responsible for reviewing the implementation and validating the reported results.

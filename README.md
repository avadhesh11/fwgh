# Wind Forecast Decision Portal — Great Britain (BMRS)

A full-stack energy analytics and verification platform that evaluates day-ahead wind generation forecasts against actual metered generation across Great Britain under strict decision cutoffs.

Built with a **FastAPI** backend and a **React 19 + TypeScript + Vite** frontend.

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

### F. Cached Dataset Date Boundaries & Scope Limitations
The repository contains validated, locally cached JSON datasets in `fwgh/backend/data/`:
* **Cached Actuals**: January 1, 2026 00:00 UTC through February 1, 2026 23:30 UTC (1,536 half-hourly intervals = 768 target delivery hours).
* **Cached Forecasts**: December 30, 2025 00:00 UTC through February 2, 2026 00:00 UTC (19,856 forecast records).
* **Evaluation Scopes Supported**:
  - **Scope A**: Delivery dates January 1–31, 2026 (744 hours, 100% complete coverage).
  - **Scope B**: Decision dates January 1–31, 2026 $\rightarrow$ Delivery dates January 2–February 1, 2026 (744 hours, 100% complete coverage).
* **Scope Boundary Note**: Dates outside January 1–February 1, 2026 are **not present** in the offline cache. Querying dates beyond this window returns 0 matched records; live streaming forecasts or arbitrary historical years are not supported without attaching live Elexon API ingestion pipelines.

---

## 3. Verified Benchmark Metrics

### Scope A (Delivery Jan 1–31, 2026; Cutoff 09:00 UK)
* **MAE**: `2,142.12 MW`
* **RMSE**: `2,611.70 MW`
* **Mean Bias**: `+1,851.90 MW` (Overforecasting)
* **P90 Absolute Error**: `4,300.15 MW`
* **Coverage**: `100.00%` (744 / 744 target intervals)
* **Lead Time**: Min `16.5h`, Max `39.5h`, Mean `28.0h`

### Scope A (Delivery Jan 1–31, 2026; Cutoff 04:00 UK)
* **MAE**: `2,199.81 MW`
* **RMSE**: `2,691.79 MW`
* **Mean Bias**: `+1,862.38 MW`
* **P90 Absolute Error**: `4,385.25 MW`
* **Coverage**: `100.00%` (744 / 744 target intervals)
* **Lead Time**: Min `21.5h`, Max `44.5h`, Mean `33.0h`

### Scope B (Decisions Jan 1–31, 2026 -> Delivery Jan 2–Feb 1, 2026; Cutoff 09:00 UK)
* **MAE**: `2,038.91 MW`
* **RMSE**: `2,504.76 MW`
* **Mean Bias**: `+1,747.89 MW`
* **P90 Absolute Error**: `4,097.90 MW`
* **Coverage**: `100.00%` (744 / 744 target intervals)
* **Lead Time**: Min `16.5h`, Max `39.5h`, Mean `28.0h`

---

## 4. API Endpoints

All backend endpoints are prefixed with `/api`. Interactive documentation is available at `/docs` (Swagger UI).

| Endpoint | Method | Query Parameters | Description |
| :--- | :--- | :--- | :--- |
| `/api/health` | `GET` | *None* | Health status, version, data load status, and record counts. |
| `/api/forecast-vs-actual` | `GET` | `scope`, `cutoff_time`, `start_date`, `end_date` | Hourly matched series (forecast MW, actual MW, signed error, lead time, publish time). |
| `/api/metrics` | `GET` | `scope`, `cutoff_time`, `start_date`, `end_date` | Summary statistics (MAE, RMSE, Bias, P50, P90, P99, Max error, Coverage %, Lead time). |
| `/api/error-by-horizon` | `GET` | `scope`, `cutoff_time`, `start_date`, `end_date` | Error statistics grouped by lead time horizon buckets (16.5h to 39.5h). |
| `/api/error-by-hour` | `GET` | `scope`, `cutoff_time`, `start_date`, `end_date` | Diurnal profile across the 24 hours of the day (SPs 1 to 48). |
| `/api/daily-errors` | `GET` | `scope`, `cutoff_time`, `start_date`, `end_date` | Daily aggregated errors, daily coverage %, and energy totals (MWh) with completeness flags. |

---

## 5. Environment Variables

### Backend Configuration
| Variable | Description | Default |
| :--- | :--- | :--- |
| `DATA_DIR` | Absolute or relative path to directory containing raw JSON cache files. | `/app/data` (in container) or `fwgh/backend/data` |
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
Or from inside `fwgh/`:
```bash
docker compose -f docker-compose.yml up --build -d
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
cd fwgh/backend
python -m venv .venv
# Windows: .venv\Scripts\activate | Unix: source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Backend runs at `http://127.0.0.1:8000`.

### Step 2: Run Frontend
In a second terminal:
```bash
cd fwgh/frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser. Vite automatically proxies `/api` requests to `http://localhost:8000`.

---

## 8. Test Execution

### Backend Automated Test Suite (28 tests)
```bash
cd fwgh/backend
python -m pytest tests/ -v
```
All 28 tests pass in < 2 seconds, covering alignment rules, duplicate pruning, integrity error handling, real-data regression baselines, cutoff boundaries, and explicit CORS headers.

### Frontend Test Suite (13 tests)
```bash
cd fwgh/frontend
npm test
```
All 13 component and integration tests pass, verifying KPI formatting, scope toggles, cutoff sensitivity updates, daily completeness flags, and error alerts.

### Frontend Production Bundle Build
```bash
cd fwgh/frontend
npm run build
```
Type checks and bundles the client app cleanly into `dist/`.

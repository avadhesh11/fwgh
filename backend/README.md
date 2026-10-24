# Wind Forecast Decision Portal — Backend API

Modular FastAPI backend service for Elexon BMRS wind generation forecast vs outturn evaluation.

---

## 1. Architecture Overview

```
fwgh/backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app definition & CORS configuration
│   ├── config.py                # Environment-aware settings & relative path resolution
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints.py         # 6 REST API endpoints with parameter validation
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py           # Pydantic response and query models
│   └── services/
│       ├── __init__.py
│       ├── alignment.py         # Core methodology: hourly aggregation, cutoff filtering, metrics
│       └── data_loader.py       # In-memory cached data loading (zero external API calls)
├── data/
│   ├── raw_fuelhh_cached.json   # Validated FUELHH actuals (Jan 1 – Feb 1, 2026)
│   └── raw_windfor_cached.json  # Validated WINDFOR forecasts (Dec 30, 2025 – Feb 2, 2026)
├── tests/
│   ├── test_alignment.py        # 9 unit tests for aggregation, conflict detection, lead times
│   └── test_api.py              # 12 API/service integration tests with deterministic fixtures
├── main.py                      # Root entrypoint (`uvicorn main:app`)
└── requirements.txt             # Backend dependencies
```

---

## 2. API Endpoints

All endpoints are prefixed with `/api`. Interactive documentation is available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

| Endpoint | Method | Query Parameters | Description |
| :--- | :--- | :--- | :--- |
| `/api/health` | `GET` | *None* | Health status, software version, data loading status, and record counts. |
| `/api/forecast-vs-actual` | `GET` | `scope`, `start_date`, `end_date`, `cutoff_time` | Matched hourly forecasts vs actual generation with publish timestamps, lead times, and errors. |
| `/api/metrics` | `GET` | `scope`, `start_date`, `end_date`, `cutoff_time` | Statistical benchmark metrics: MAE, RMSE, Bias, P50, P90, P99, Max error, and Coverage %. |
| `/api/error-by-horizon` | `GET` | `scope`, `start_date`, `end_date`, `cutoff_time` | Forecast error distribution and accuracy grouped by lead-time horizon (16.5h to 39.5h). |
| `/api/error-by-hour` | `GET` | `scope`, `start_date`, `end_date`, `cutoff_time` | Error and generation statistics grouped by hour of the day (Hour 0 to 23 / Settlement Periods 1-48). |
| `/api/daily-errors` | `GET` | `scope`, `start_date`, `end_date`, `cutoff_time` | Daily aggregated errors, daily coverage %, and total energy generated vs forecast (MWh). |

### Query Parameter Details
- **`scope`**: Predefined scope shortcut:
  - `"A"` (Default): Delivery window January 1–31, 2026 (744 expected hours).
  - `"B"`: Purchase decisions January 1–31, 2026 $\rightarrow$ Delivery window January 2–February 1, 2026 (744 expected hours).
- **`start_date`**: Custom delivery start date (`YYYY-MM-DD`). Overrides scope start date.
- **`end_date`**: Custom delivery end date (`YYYY-MM-DD`). Overrides scope end date.
- **`cutoff_time`**: Decision cutoff on day $D-1$ in `HH:MM` format (default: `"09:00"` UK local time).

---

## 3. Data Loading Strategy

1. **No External Calls**: Per design requirements, no live Elexon API requests are made during request handling.
2. **Relative Path Resolution**: `app/config.py` locates `raw_fuelhh_cached.json` and `raw_windfor_cached.json` by searching:
   - Environment variable `DATA_DIR` (if set)
   - `fwgh/backend/data/`
   - Fallback to `scripts/` in workspace root
3. **In-Memory Caching**: Once read from disk, raw records are cached in memory. Subsequent endpoint queries execute in **< 10 milliseconds**.
4. **Test Fixture Injection**: `app/services/data_loader.py` provides `set_cached_data()` enabling tests to inject deterministic mock data without filesystem access.

---

## 4. Run & Test Instructions

### Install Dependencies
```bash
cd fwgh/backend
pip install -r requirements.txt
```

### Run the FastAPI Server
```bash
# Using uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Or directly with Python
python main.py
```
Server runs at `http://localhost:8000`. API documentation at `http://localhost:8000/docs`.

### Run Automated Tests
```bash
# Run all tests
pytest tests/ -v

# Run API endpoint tests only
pytest tests/test_api.py -v

# Run alignment unit tests only
pytest tests/test_alignment.py -v
```

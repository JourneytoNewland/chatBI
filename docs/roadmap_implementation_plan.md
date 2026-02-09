# Implementation Plan - Phase 1 & 2

## Goal
Improve system stability by standardizing startup scripts and exception handling (Phase 1), and enhance flexibility by externalizing metric definitions (Phase 2).

## User Review Required
> [!IMPORTANT]
> This plan involves refactoring core logic for metric definitions. Ensure `configs/metrics.yaml` covers all existing hardcoded metrics to avoid regression.

## Proposed Changes

### Phase 1: Stability & Standards

#### [NEW] `scripts/run_demo_safe.sh`
- A new wrapper script that:
    - Checks if `.venv` exists.
    - Activates `.venv`.
    - Checks key dependencies (fastapi, uvicorn).
    - Starts `run_demo_server.py`.

#### [MODIFY] `src/api/main.py` & `scripts/run_demo_server.py`
- Add a global exception handler using `@app.exception_handler(Exception)`.
- Ensure all unhandled exceptions return a standard JSON response: `{"error": str(e), "code": 500, "success": false}`.

### Phase 2: Configuration & Metrics

#### [NEW] `configs/metrics.yaml`
- Centralized definition of all metrics (GMV, DAU, etc.) currently hardcoded in `run_demo_server.py` and `sql_generator_v2.py`.
- Format:
```yaml
metrics:
  - id: m001
    name: GMV
    synonyms: [成交金额, 交易额]
    table: fact_orders
    column: gmv
    ...
```

#### [NEW] `src/config/metric_loader.py`
- A singleton class `MetricLoader` to load and parse `configs/metrics.yaml`.
- Provides methods `get_metric_by_name(name)` and `get_all_metrics()`.

#### [MODIFY] `scripts/run_demo_server.py`
- Remove `MOCK_METRICS` constant.
- Use `MetricLoader` to initialize metric data.

#### [MODIFY] `src/mql/sql_generator_v2.py`
- Remove `METRIC_TABLE_MAPPING`.
- Use `MetricLoader` to resolve `metric_name` to `table` and `column`.

### Phase 1: Interaction & Visual Optimization (2026 Q1)
#### [NEW] `src/api/context_manager.py` (Session State)
- Implement `ContextManager` using Redis or in-memory dict (for MVP).
- Store `last_query_intent`, `last_sql`, and `last_filters` keyed by `session_id`.
- Enable "Drill-down" follow-ups (e.g., "What about in East China?") by merging new entities with cached context.

#### [MODIFY] `frontend/js/chart_renderer.js` (Smart Viz)
- Implement `AutoVizEngine`:
  - If output is TimeSeries -> render Line Chart.
  - If output is Categorical -> render Bar/Pie Chart.
  - If output is Geo -> render Map (future).
- Add support for "Drill-down" interactive clicks on chart elements.

### Phase 2: Enterprise Ecosystem Integration (2026 Q2)
#### [NEW] `scripts/sync_dbt_meta.py` (dbt Sync)
- Parse `dbt`'s `manifest.json` or `schema.yml`.
- Auto-generate or update `configs/metrics.yaml` with:
  - Metric descriptions from docstrings.
  - Column mappings from models.
- Verification: Run script against a sample dbt project and diff the yaml.

#### [NEW] `src/mql/federated_query.py` (Federation Layer)
- Introduce `QueryRouter` class.
- Route real-time queries (e.g., "Inventory right now") to ClickHouse/Redis.
- Route analytical queries (e.g., "Last month GMV") to PostgreSQL.

### Phase 3: Predictive & Automated BI (2026 Q3)
#### [NEW] `src/analysis/prophet_engine.py` (Forecasting)
- Integrate `facebook/prophet` library.
- Create `/api/v3/forecast` endpoint.
- Logic: Fetch last 90 days data -> Fit Prophet model -> Predict next 7-30 days -> Return confidence intervals.

#### [NEW] `src/reporting/daily_brief.py` (Auto-Report)
- Scheduled Cron job (Celery/APScheduler).
- Template-based generation (Jinja2) of HTML/PDF reports.
- Content: Key metric DoD/WoW changes + Top 3 anomalies + Forecast.

## Verification Plan

### Automated Verification
1.  **Startup Test**: Run `bash scripts/run_demo_safe.sh` and ensure server starts without error.
2.  **Functionality Test**: Run `python scripts/simulate_tests.py` (using `urllib` version) to verify:
    - Basic queries (GMV, DAU) still work.
    - Synonym matching works (via new config).
3.  **Exception Test**: Send a malformed request to `/api/v1/search` and verify response is JSON, not HTML 500 page.

### Manual Verification
1.  **Config Hot-Reload (Optional)**: Modify `metrics.yaml` (e.g., add a new synonym for GMV "卖了多少钱") and restart server to verify it's recognized.

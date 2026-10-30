# Server Resource Utilization Forecasting Using Time Series Analysis and Machine Learning

## Objective

This university mini-project forecasts server resource utilization from time-indexed performance metrics. The project is forecasting-first: it focuses on predicting future resource values rather than detecting anomalies. Models will be evaluated on chronologically held-out data to avoid data leakage.

## Academic phases

1. **Phase 1 — Synopsis (28 September–9 October 2026):** Select and explore a suitable server-metrics dataset with at least 500 observations. Perform exploratory analysis, missing-value checks, summary statistics, and time-series visual inspection. No forecasting models are developed in this phase.
2. **Phase 2 — Classical Forecasting (19–30 October 2026):** Clean and preprocess data, create chronological train/test splits, test stationarity, and develop ARIMA/SARIMA models where appropriate. Evaluate using MAE, RMSE, and MAPE where valid.
3. **Phase 3 — Advanced Forecasting (16–27 November 2026):** Develop XGBoost and LSTM models, compare all approaches on identical held-out periods, build a Streamlit dashboard, and prepare the final report and presentation.

## Project layout

- `data/` — raw, processed, and supporting dataset material (datasets are not tracked in Git).
- `notebooks/` — phase-specific exploratory and modelling notebooks.
- `src/` — reusable project modules.
- `reports/` and `presentations/` — figures and academic deliverables.
- `app/` — reserved for the Phase 3 Streamlit dashboard.
- `tests/` — project tests.

## Phase 1 environment

Use Python 3.11 and the local virtual environment:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

# Phase 2 ARIMA Baseline

## Scope

This is the first classical forecasting model in the project. It uses the validated, chronologically ordered selected CPU-utilization series. NAB anomaly labels were not loaded or used.

## Training-only selection

- **Training partition:** 3,226 observations from 2014-02-14 14:27:00 through 2014-02-25 19:12:00.
- **Differencing:** `d = 1`, based on the training-only ADF and KPSS results in `reports/phase2_stationarity_diagnostics.md`.
- **Candidate grid:** ARIMA(`p`, 1, `q`) for `p` and `q` in {0, 1, 2}.
- **Selection criterion:** lowest AIC calculated on the training partition only.
- **Selected baseline:** **ARIMA(2, 1, 2)** with training AIC **15,197.2428**.

This deliberately small grid is a transparent educational baseline, not exhaustive hyperparameter optimisation.

## Single held-out evaluation

After selection, ARIMA(2,1,2) forecast the unchanged 806-observation period from 2014-02-25 19:17:00 through 2014-02-28 14:22:00.

| Metric | Result |
|---|---:|
| MAE | 0.7671 |
| RMSE | 0.9763 |
| MAPE | 1.9966% |

MAPE is valid here because all held-out actual CPU-utilization values are positive.

## Interpretation and limitations

The reported metrics describe this single chronological holdout, not a general forecast guarantee. The model's selection did not use held-out observations, which prevents test leakage during order choice. The dataset remains short, univariate, and subject to observed changes in level. A good score on this period does not establish seasonality, production readiness, or superiority over future XGBoost/LSTM models.

### Residual diagnostic

A Ljung-Box check on post-initialization residuals (the first 30 residuals excluded) rejects the null hypothesis of no residual autocorrelation at lags 10, 20, and 50:

| Lag | Ljung-Box statistic | p-value |
|---|---:|---:|
| 10 | 557.6764 | 2.04e-113 |
| 20 | 1,049.1989 | 1.25e-209 |
| 50 | 2,115.1159 | < 1e-300 |

This indicates that ARIMA(2,1,2) leaves temporal structure unexplained. It remains a valid transparent baseline, but the residual evidence means it should not be described as a complete model of the series. This finding supports a later comparison with other methods rather than a claim of final model adequacy.

## Reproducible outputs

- Script: `src/run_arima_baseline.py`.
- Forecast table with 95% intervals: `data/processed/arima_212_holdout_forecast.csv`.
- Preparation and split record: `reports/phase2_data_preparation.md`.
- Stationarity rationale: `reports/phase2_stationarity_diagnostics.md`.

Run `python src/run_arima_baseline.py` from the activated virtual environment to reproduce the numerical result. A forecast plot is optional (`--plot`) and is deliberately separated from the numerical run, because a local Matplotlib-backend problem must not block training or evaluation. No Phase 2 forecast plot is currently claimed as generated.

## Next decision

Do not fit SARIMA merely because it was proposed in the synopsis. The current training history does not yet provide adequate evidence for a seasonal period. The next Phase 2 task is to resolve the local plotting-backend issue only if a forecast figure is required for documentation; the numerical baseline, split, and evaluation are already reproducible. Then the project should wait for its scheduled Phase 3 model-comparison work.

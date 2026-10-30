# Phase 3 XGBoost Forecast Plan

## Design

XGBoost is used as a machine-learning forecasting model, not as an anomaly detector. It predicts the next CPU-utilization value from the preceding 5-minute values at lags 1, 2, 3, 6, 12, and 24 (up to two hours of recent history). These lags provide short-term memory and do not make a claim that daily or weekly seasonality exists.

## Leakage controls

The model-selection validation period is the final 20% of the existing 3,226-observation training partition. Every candidate is trained only on the earlier portion and recursively forecasts that validation horizon. The final 806-observation test period is not used until the selected configuration has been refitted using all training observations.

During a recursive forecast, previous predictions, not observed test values, are appended to the history. This produces one genuine 806-step forecast trajectory directly comparable with ARIMA.

## Small candidate set

Three configurations are deliberately predeclared for this mini-project:

| Max depth | Learning rate | Trees |
|---:|---:|---:|
| 2 | 0.05 | 200 |
| 3 | 0.05 | 300 |
| 3 | 0.10 | 200 |

The configuration with the lowest recursive validation MAE is selected. This is a limited, explainable search—not exhaustive tuning.

## Observed final output

The selected configuration was max depth 2, learning rate 0.05, and 200 trees. Its training-only recursive validation MAE was 3.7467.

The final refitted model produced one forecast per fixed final-test timestamp in `data/processed/xgboost_holdout_forecast.csv`.

| Metric | XGBoost result | ARIMA(2,1,2) reference |
|---|---:|---:|
| MAE | 0.7578 | 0.7671 |
| RMSE | 1.0601 | 0.9763 |
| MAPE | 1.9489% | 1.9966% |

These results apply only to this one 806-observation holdout. XGBoost has lower MAE and MAPE here, while ARIMA has lower RMSE; therefore the results do not support a blanket claim that either model is superior. LSTM evaluation remains pending.

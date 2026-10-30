# Phase 3 Model-Comparison Protocol

## Purpose

This protocol ensures that the planned XGBoost and LSTM forecasts can be compared fairly with the Phase 2 ARIMA baseline. It defines the evaluation rules before fitting advanced models, rather than changing them after seeing test results.

## Fixed dataset and evaluation period

- **Series:** `ec2_cpu_utilization_5f5533.csv` from NAB `realAWSCloudwatch`.
- **Training period:** 3,226 observations, 2014-02-14 14:27:00 through 2014-02-25 19:12:00.
- **Final test period:** 806 observations, 2014-02-25 19:17:00 through 2014-02-28 14:22:00.
- **Frequency:** five minutes.

The final test period is fixed and will not guide model or hyperparameter selection. ARIMA has already been evaluated on this same period.

## Shared forecasting rule

Both advanced methods will initially use only past CPU-utilization values. Lag features or sequences are built from the training partition. For the 806-step test forecast, each model begins with the final training history and then uses its own preceding predictions to make subsequent forecasts. Observed test values are reserved solely for the final metrics.

This recursive approach is directly comparable to ARIMA's multi-step held-out forecast. It is more demanding than one-step-ahead evaluation with actual test values fed back into a model, but it avoids that form of leakage.

## Training-only transformations

- XGBoost will use lag features; no fitted transformation will use test values.
- LSTM scaling parameters will be fitted on training values only. Test values may transform only with those already-fitted parameters and are not used while producing the recursive prediction sequence.
- Any validation subset for hyperparameter choices must be carved chronologically from the training partition. The final 806 observations remain unseen until evaluation.

## Planned evaluation

The model output will have one forecast per final-test timestamp. Each model will report MAE, RMSE, and MAPE (valid only while actual values are nonzero), using the existing `regression_metrics` function. Results will be tabulated next to ARIMA without claiming general superiority from this one short series.

## Limitations retained in Phase 3

This approximately two-week, univariate series may include level changes and does not establish seasonality. Advanced models have a real overfitting risk on this amount of history. Results will therefore be presented as an educational comparison on one fixed holdout, not a production capacity-planning guarantee.

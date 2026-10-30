# Phase 2 Stationarity Diagnostics

## Scope and leakage safeguard

All results below use only the 3,226-observation training partition defined in `reports/phase2_data_preparation.md`. The 806-observation held-out test period was not used for testing, differencing decisions, plots, parameter selection, or model fitting.

## Tests used

- **Augmented Dickey-Fuller (ADF):** the null hypothesis is that the series has a unit root (is non-stationary).
- **KPSS level-stationarity test:** the null hypothesis is that the series is level-stationary.

Using both tests provides complementary evidence. The reported KPSS p-values are bounded by the test's lookup table: `0.01` means the actual p-value is at most 0.01, while `0.10` means it is at least 0.10.

## Raw training series

| Test | Statistic | p-value | Decision at 5% | Interpretation |
|---|---:|---:|---|---|
| ADF | -0.2412 | 0.9334 | Fail to reject the unit-root null | Evidence against stationarity. |
| KPSS | 6.5949 | <= 0.01 | Reject the level-stationarity null | Evidence against stationarity. |

The two tests agree: the raw training series is not stationary. This aligns with the Phase 1 plot, which showed a change in level during the observed period.

## First-differenced training series

| Test | Statistic | p-value | Decision at 5% | Interpretation |
|---|---:|---:|---|---|
| ADF | -17.1429 | 7.03e-30 | Reject the unit-root null | Strong evidence for stationarity after one difference. |
| KPSS | 0.0195 | >= 0.10 | Fail to reject the level-stationarity null | Consistent with level stationarity after one difference. |

## Modelling implication

The Phase 2 ARIMA baseline should begin with one non-seasonal difference (`d = 1`). This is a diagnostic decision, not a claim that differencing solves every structural change or spike.

No seasonal structure is established. The dataset contains only about two weeks of observations, and Phase 1 daily/weekly autocorrelations were insufficient to demonstrate seasonality. SARIMA will remain conditional and will not be fitted unless later training-only diagnostics provide stronger support.

## Next task

Use training-only ACF/PACF evidence and a small transparent ARIMA candidate grid with `d = 1`. Select a candidate using training information only, then produce one final forecast for the unchanged held-out test period.

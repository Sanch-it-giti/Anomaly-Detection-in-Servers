# M4A fixed-model forward DEVELOPMENT comparison

Run: `m4a-development-20261031-001`, 31 October 2026. Only three original development primaries and indices **[1152,1612)** were evaluated. These are development findings; no confirmation or final-test result is reported.

The fixed models are ARIMA (1,1,1) and XGBoost C1 (depth 2, 100 trees, learning rate 0.05, separate direct h=1/h=12 regressors). Checkpoints fitted on [0,864) and selected using [864,1152) were reused without fitting, scaler changes or reselection. Horizons predict a genuine five-minute CPU-bin mean ending 5 or 60 minutes after the origin.

## Identical expert-origin comparisons

For each machine/horizon, intersect scored (origin timestamp, exact target timestamp) pairs where both learned experts actually issued expert predictions and persistence issued its reference. All three policies are compared on this identical set. Missing targets never enter errors. CPU errors are percentage points.

The following are **equal-machine means of per-machine MAE and RMSE**, not pooled RMSE. All three machines have support. Total counts are descriptive denominators, not weights.

| Policy | h=1 MAE | h=1 RMSE | h=12 MAE | h=12 RMSE |
|---|---:|---:|---:|---:|
| Persistence | 4.125690 | 5.424773 | 7.133119 | 9.324500 |
| Fixed ARIMA | 3.901195 | 5.104576 | 6.797972 | 8.788959 |
| Fixed XGBoost | 4.396641 | 5.801670 | 6.937706 | 9.025295 |

Common counts: h=1 **1,297** (429, 434, 434); h=12 **1,272** (417, 432, 423), in machine order m_505, m_1426, m_3028.

| Machine | Horizon | Common n | Persistence MAE / RMSE | ARIMA MAE / RMSE | XGBoost MAE / RMSE |
|---|---:|---:|---:|---:|---:|
| m_505 | 1 | 429 | 4.026449 / 5.336539 | 3.765395 / 4.921844 | 3.941375 / 5.090962 |
| m_505 | 12 | 417 | 6.442680 / 8.499691 | 6.069862 / 7.915405 | 6.165309 / 7.879401 |
| m_1426 | 1 | 434 | 4.343090 / 5.858206 | 4.205338 / 5.595001 | 4.536271 / 6.026882 |
| m_1426 | 12 | 432 | 7.923529 / 10.460706 | 7.695167 / 9.835368 | 7.510281 / 9.705130 |
| m_3028 | 1 | 434 | 4.007533 / 5.079574 | 3.732851 / 4.796884 | 4.712277 / 6.287166 |
| m_3028 | 12 | 423 | 7.033149 / 9.013103 | 6.628887 / 8.616105 | 7.137528 / 9.491354 |

ARIMA has the lowest observed macro MAE/RMSE at both horizons. XGBoost has worse macro h=1 errors than persistence, although its h=1 error is lower on m_505. XGBoost's h=12 macro errors are lower than persistence, but both its h=12 MAE and RMSE are worse on m_3028. On m_1426, XGBoost has lower h=12 errors than ARIMA. There is no universally best learned expert for every machine/horizon/metric.

## Complete fixed policies, including fallback

These errors include history-gate persistence fallback. Do not compare them against a different expert-only denominator. All three policies happen to have identical complete-policy target support in this block; that is measured, not assumed.

| Policy | h=1 MAE | h=1 RMSE | h=12 MAE | h=12 RMSE |
|---|---:|---:|---:|---:|
| Persistence | 4.120591 | 5.438665 | 7.140607 | 9.347145 |
| ARIMA with fallback | 3.908631 | 5.138632 | 6.823330 | 8.841859 |
| XGBoost with fallback | 4.377595 | 5.804142 | 6.953960 | 9.069516 |

Per-policy complete counts: h=1 **1,373** (457,458,458); h=12 **1,340** (446,447,447). All per-machine complete-policy MAE/RMSE, own expert counts, availability and pending counts are in [forward_metrics.csv](forward_metrics.csv) and its JSON equivalent; [macro_metrics.csv](macro_metrics.csv) contains both scopes explicitly.

## Descriptive comparison with M3B-2

M3B-2 selected these settings using its own inner validation. Its selected errors are tuning-period descriptions. M4A subsequently evaluated the frozen choices on a different development block, with no reselection.

| Policy | Inner h=1 MAE / RMSE | Forward h=1 MAE / RMSE | Inner h=12 MAE / RMSE | Forward h=12 MAE / RMSE |
|---|---:|---:|---:|---:|
| Persistence | 4.454725 / 6.037374 | 4.125690 / 5.424773 | 7.809454 / 10.067045 | 7.133119 / 9.324500 |
| ARIMA | 4.184956 / 5.652008 | 3.901195 / 5.104576 | 6.538153 / 8.640194 | 6.797972 / 8.788959 |
| XGBoost | 4.458352 / 6.099749 | 4.396641 / 5.801670 | 6.612528 / 8.823394 | 6.937706 / 9.025295 |

Both blocks favor ARIMA on macro errors. Absolute h=1 errors decrease in the forward block, while h=12 learned errors increase and persistence errors decrease. These are different periods and supports (inner h=1/h=12 totals 696/670; forward 1,297/1,272). They do not establish drift, statistical significance, or a causal performance change. Settings remain unchanged regardless of these observations.

Sources: this run's immutable ledgers and metrics; [original M3B-2 comparison](../../m3b2_v1/m3b2-development-20261030-001/comparison.md). No NAB test result was used.

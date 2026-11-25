# M3B-2 model selection — DEVELOPMENT VALIDATION

No independent final-test or DAF-R improvement claim. Winners are designated only after all candidate replays.

| Family | Selected candidate | Macro h=1 MAE | Macro h=1 RMSE |
|---|---:|---:|---:|
| arima | C3 | 4.184956 | 5.652008 |
| xgboost | C1 | 4.458352 | 6.099749 |

All h=12 results use those same settings. AIC was recorded but not used to select ARIMA.

See validation_metrics.csv for per-machine/horizon expert-only matched accuracy, persistence on identical origins, common-gate policy accuracy and complete-policy availability.

A failed fit is excluded from global promotion; its fallback ledger remains in the tables. Candidate plots include complete common-gate policies, including fallback, so a rejected fit can resemble persistence and is not an accepted ARIMA result.

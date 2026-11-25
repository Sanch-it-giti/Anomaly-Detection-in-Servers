# M6B runtime and memory

Measured saved run, synthetic registered backends only,7 November2026.

| Scope | Seconds |
|---|---:|
| sustained,280 ticks |18.729638|
| gaps_failures,450 ticks |25.022620|
| update_failure,180 ticks |11.486426|
| Whole run including synthetic checkpoint build and saved-ledger audits |56.808664|
| Full341-test suite |138.452000|

Whole-run peak process high-water RSS:369655808bytes = **352.53125MiB**. The configured guard is4GiB on an8GB Mac; replay checks it every tick. This is process high-water RSS, cumulative across backend loading, paired enabled/disabled runs and audits, not incremental drift-state memory or a complete OS memory profile. Tests run separately and their peak is not included. Per-case values exclude checkpoint build and later audits. Detector state remains32 normalization values, max288 recent timestamps and constant PH statistics per horizon. Audit/source ledgers are retained in memory for this small capped harness; production storage/long-duration behavior is not validated.

The pre-replay fixture build uses96 generated genuine observations: actual ARIMA(1,1,1) filtering with known coefficients, plus two small native direct-horizon XGBoost fits. During all910 replay ticks there were zero fitting attempts. Historical models are hashed only and never refitted. Parameters and synthetic checkpoint files remain unchanged. No TensorFlow installation or new dependency is required. These figures establish small-run engineering feasibility, not real-data accuracy or a production latency guarantee.

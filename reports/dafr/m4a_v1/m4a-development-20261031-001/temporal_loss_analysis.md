# M4A exploratory chronological loss description

This analysis uses only errors already matured against genuine exact targets inside [1152,1612). It does not validate a drift detector, choose a selector or authorize adaptive switching.

Before opening this block, the execution configuration fixed two descriptions: three grid partitions [1152,1305), [1305,1458), [1458,1612), and a trailing 48-grid-tick (four-hour) MAE with at least 12 common genuine scored targets. Windows are based on elapsed grid positions and target arrival times. They are never centered, never compress gaps, and never use future errors. Early insufficient-support windows are left blank. Overlapping windows and h=12 forecasts are dependent.

## Equal-machine matched MAE by exact-target partition

| Target partition | h | Counts m_505 / m_1426 / m_3028 | Persistence | ARIMA | XGBoost |
|---|---:|---|---:|---:|---:|
| [1152,1305) | 1 | 122 / 152 / 152 | 4.31953 | 4.03087 | 4.58245 |
| [1305,1458) | 1 | 153 / 153 / 153 | 3.41604 | 3.23006 | 3.48437 |
| [1458,1612) | 1 | 154 / 129 / 129 | 4.72315 | 4.52253 | 5.22055 |
| [1152,1305) | 12 | 110 / 141 / 141 | 7.49073 | 7.02213 | 7.33802 |
| [1305,1458) | 12 | 153 / 153 / 153 | 5.63235 | 5.61913 | 5.70592 |
| [1458,1612) | 12 | 154 / 138 / 129 | 8.43022 | 7.87668 | 7.86125 |

Counts apply equally to all policies within each machine/partition/horizon. The first partition lacks forecasts for the first 1 or 12 target positions, and missingness/history gating removes further targets. Partitions have 153,153,154 grid bins; unequal supported counts are displayed instead of silently treated as equal information. Full per-machine MAE/RMSE and counts are in [temporal_descriptive.csv](temporal_descriptive.csv).

Loss levels vary visibly: the middle partition has lower macro errors than the earlier and later partitions at both horizons. ARIMA remains best by h=1 macro MAE in every partition. At h=12, XGBoost has a slightly lower final-partition macro MAE than ARIMA (7.86125 versus 7.87668), while ARIMA is lower in the first two partitions. The final-partition difference is small and has no demonstrated statistical significance. The whole-block h=12 macro still favors ARIMA.

The past-only m_1426 h=12 plot also shows changing local relative losses. In contrast, m_3028 h=1 contains conspicuous XGBoost errors around CPU peaks. These are descriptive observations from the frozen-model run, not identified concept-drift events. CPU-pattern changes, model bias, finite-sample noise, correlated workloads and differing support can all contribute.

## Figures and interpretation limits

Six forecast/error plots and six trailing-loss plots are saved locally under `data/processed/dafr/m4a_development_v1/m4a-development-20261031-001/<machine>/private_figures/`. These directories are ignored by Git because they display derived machine traces. The public aggregate comparison image contains only summary errors.

Forecast/error plots retain genuine CPU gaps and display complete-policy predictions above expert-matched errors. A prediction may appear over a missing target because target availability was unknown when issued; no error exists there. Recovery-gated learned predictions remain explicitly attributed to persistence fallback in ledgers. Rolling lines are summaries, not live policy decisions.

Only 38 hours 20 minutes of grid duration and three correlated same-cluster machines are represented. Four isolated missing bins do not test sustained outages. No change to orders, trees, history gate, window lengths or selection settings was made after seeing these plots. Future experiments require separate design/authorization and cannot treat this now-inspected development block as an untouched confirmation set.

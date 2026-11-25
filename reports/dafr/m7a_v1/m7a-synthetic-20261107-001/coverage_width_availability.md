# M7A coverage, width and availability — synthetic engineering diagnostics only

All ten predefined fixtures are retained. No interval setting was optimized after seeing these outcomes. These serially dependent synthetic errors do not establish real-world calibration or formal exchangeability-based coverage.

The following overview is the **complete adaptive policy**, including its own fallback centers. It is not a performance comparison or an independent DAF-R experiment. The CSV contains all160 rows: four separate policies × two horizons × two nominal levels × ten fixtures. Fixed experts are shadow mocks, not trained ARIMA/XGBoost models.

Coverage uses only genuinely observed targets with an available interval. The support column reports that count / all genuine matured centers; unavailable intervals are neither counted as covered nor silently assigned zero width. Width below is the mean raw width at issuance, including available intervals still pending at stream end. Mean genuine-scored width, interval score, median width, missing/pending/fallback/unissued counts and both availability denominators are provided in the CSV.

| Fixture | h | Available / genuine matured | Coverage90 | Coverage95 | Mean issued width90 | Mean issued width95 |
|---|---:|---:|---:|---:|---:|---:|
| stable | 1 | 259 / 359 | 89.96% | 94.98% | 1.355893 | 1.367286 |
| stable | 12 | 237 / 348 | 90.30% | 94.51% | 3.446284 | 3.474963 |
| growing_variation | 1 | 259 / 359 | 57.53% | 66.41% | 3.170767 | 3.485990 |
| growing_variation | 12 | 237 / 348 | 56.12% | 64.14% | 8.081442 | 8.871156 |
| shrinking_variation | 1 | 259 / 359 | 100.00% | 100.00% | 4.464976 | 4.817898 |
| shrinking_variation | 12 | 237 / 348 | 97.47% | 99.58% | 11.932068 | 12.478390 |
| abrupt_change | 1 | 259 / 359 | 71.81% | 81.47% | 3.382704 | 3.833177 |
| abrupt_change | 12 | 237 / 348 | 64.56% | 74.26% | 8.573570 | 9.744603 |
| isolated_extreme | 1 | 259 / 359 | 89.96% | 94.98% | 1.356551 | 1.367696 |
| isolated_extreme | 12 | 237 / 348 | 89.45% | 94.09% | 3.450954 | 3.476935 |
| short_gaps | 1 | 255 / 355 | 90.20% | 94.90% | 1.356724 | 1.367680 |
| short_gaps | 12 | 233 / 344 | 89.70% | 94.42% | 3.448809 | 3.475898 |
| long_gap_recovery | 1 | 140 / 340 | 90.00% | 95.71% | 1.355941 | 1.367320 |
| long_gap_recovery | 12 | 103 / 325 | 87.38% | 93.20% | 3.445519 | 3.472613 |
| insufficient_support | 1 | 0 / 59 | Unavailable | Unavailable | Unavailable | Unavailable |
| insufficient_support | 12 | 0 / 48 | Unavailable | Unavailable | Unavailable | Unavailable |
| numerical_failures | 1 | 259 / 359 | 89.96% | 94.98% | 1.355893 | 1.367286 |
| numerical_failures | 12 | 237 / 348 | 90.30% | 94.51% | 3.446284 | 3.474963 |
| calibration_expiry | 1 | 389 / 489 | 90.49% | 95.37% | 1.356347 | 1.367714 |
| calibration_expiry | 12 | 367 / 478 | 90.74% | 94.82% | 3.447435 | 3.476153 |

Stable errors produce coverage near the nominal targets; this is an engineering observation, not a guarantee. Growing variation produces substantial undercoverage (57.53% /56.12% at90% nominal, h1/h12). Abrupt changes also under-cover. Shrinking variation is conservative, with100% h1 coverage in this fixture and larger residual-window widths. No result is retuned or removed. The isolated extreme remains a genuine error, not an anomaly label to be excluded.

The insufficient-support fixture has59 /48 genuine adaptive targets at h1/h12 and no available intervals. Long gaps reduce availability and reset support; old-era forecasts may still score without contributing to new calibration. Prolonged expert failure makes fixed shadow calibration expire, while the adaptive complete policy can continue learning its own persistence-fallback errors. That supported adaptive interval is explicitly policy-level, not a calibrated interval for an unavailable expert.

Across all fixtures there are27440 source point decisions and54880 interval attempts (two nominal levels each). Source accounting:24905 issued centers,24303 genuine targets,104 missing targets,498 pending and2535 unissued attempts. Interval accounting:30786 genuinely scored available intervals,17820 genuine interval-unavailable outcomes,208 missing-target outcomes,996 pending issued-center intervals and5070 center-unavailable interval attempts. These reconcile to54880. Available intervals at issuance total31834; do not confuse this with the30786 whose genuine targets have arrived.

All22 genuinely scored old-era policy errors in the long-gap fixture remain auditable but are excluded from new-era support. All unobserved/pending targets have null or absent coverage outcomes. No raw interval endpoint extended outside[0,100] in these particular saved fixtures; the implementation does not clip, and a unit test explicitly verifies out-of-range raw endpoints remain visible. Zero unbounded intervals were created; insufficient support is represented by unavailable/null bounds, not infinite or zero widths.

Full per-policy/horizon/nominal results: [coverage_width_availability.csv](coverage_width_availability.csv). Authoritative summaries/audits: [verification.json](verification.json).

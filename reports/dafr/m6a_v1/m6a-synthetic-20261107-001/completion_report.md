# M6A completion — SYNTHETIC ENGINEERING VERIFICATION ONLY

Completed 7 November 2026. Run `m6a-synthetic-20261107-001`. **M6A is complete; stop here.** No real-data drift analysis or DAF-R forecasting improvement is established.

## Detector choices

Implemented a separately versioned, one-sided Page–Hinkley-style monitor of **genuinely matured fixed-persistence absolute errors**, independently for h=1/h=12. Source/version is `persistence/rule_v2`. The source is fixed regardless of any selector; no model fitting, selector callback or automatic intervention exists.

The [frozen design](../../m6a_drift_detection_design_v1.md) specifies equations and ordering. Its new engineering choices are: first **32 errors** for current-era median/MAD normalization, scale floor **0.1 CPU percentage points**, MAD multiplier 1.4826, normalized clipping ±4, PH tolerance **0.05**, warning/alarm thresholds **4/8**, minimum **64 recent genuine errors**, a **288-grid-tick** support bound, and **24 elapsed ticks** of cooldown. These were frozen before saved experiments and not tuned on M4A/M5B-2 or changed after synthetic results.

Alerts log availability time, source/version, horizon, genuine support, statistic, threshold, telemetry era, source forecast/outcome identifiers and cooldown state. A level change, an error-behavior change, missing telemetry, statistical alarm and selector switch remain distinct. A statistical reference-error alarm does not prove concept drift.

The original research proposed both CPU-level and error channels plus potential watch/selector responses. M6A implements only the error-monitoring branch. CPU-level monitoring, cross-channel confirmation, selector response and refitting remain deferred. Original M5A/M5B thresholds and all unfavorable M5B-2 results remain byte-identical.

## Measured synthetic alarms, false alarms and delays

All values below are **SYNTHETIC ENGINEERING VERIFICATION ONLY**. Delay is the first post-intervention alarm's exact-target tick minus the fixture's known intervention tick. Multiply ticks by five for minutes. The labels describe constructed interventions, not real concept-drift ground truth. Repeated post-change alarms are not independent drift events.

| Predefined fixture | h=1 alarms | h=12 alarms | First delay h=1 / h=12 (ticks) | False/pre-change alarms h=1 / h=12 |
|---|---:|---:|---|---|
| Stable errors | 0 | 0 | — / — | 0 / 0 |
| Sustained error increase | 5 | 5 | 2 / 2 | 0 / 0 |
| Isolated outlier | 0 | 0 | — / — | 0 / 0 |
| Gradual change | 4 | 5 | 30 / 12 | 0 / 0 |
| Abrupt CPU-level step | 0 | 1 | Missed / 2 | 0 / 0 |
| Short missing observations | 0 | 0 | — / — | 0 / 0 |
| Leading/long/trailing four-tick resets | 0 | 0 | — / — | 0 / 0 |
| Delayed h=12, 40 ticks | 0 | 0 | — / — | 0 / 0 |
| Early change, insufficient support | 0 | 0 | Missed / missed | 0 / 0 |
| Declared reference forecast failure | 0 | 0 | — / — | 0 / 0 |
| Persistent-change cooldown stress | 6 | 7 | 4 / 2 | 0 / 0 |

There are **33 statistical alarms and 37 warning entries** in total. No statistical alarm occurs in a labeled no-change/outlier fixture or before a labeled intervention. This is an observed count over deterministic fixtures, not a real-world false-alarm probability or calibrated statistical guarantee.

Four warning entries occur without a sustained-change label: one per horizon for the isolated outlier, and two at h=12 for short missing runs. Genuine reference errors can change because telemetry gaps make persistence stale; those warnings are not treated as proof of workload drift. Missing targets themselves never produce detector samples.

The h=1 abrupt-level step creates a single large absolute-error impulse. Clipping and accumulation keep it below the alarm threshold; the error-only channel therefore misses that fixture intervention. At h=12, persistence sees multiple affected targets and alarms after two ticks (10 minutes). The gradual-change delays are 150 and 60 minutes. These limitations are retained rather than changing thresholds or adding a posthoc level detector.

The insufficient-support fixture ends with only 49 h=1 and 38 h=12 genuine errors, so it correctly suppresses alarms despite the early slope change. In the cooldown stress fixture, alarms occur at h=1 ticks 124,152,180,208,236,264 and h=12 ticks 122,148,174,200,226,252,278. Spacing respects the 24-tick suppression interval plus the time needed to rebuild PH. The same persistent increase can produce repeated alarms because normalization is deliberately not re-fitted on alarm.

Full exact counts/timestamps, clipping, warnings, accepted/ignored errors and delays are in [detection_summary.csv](detection_summary.csv) and [synthetic_summary.json](synthetic_summary.json).

## Causality, missingness and audit accounting

The new driver reveals a five-minute tick, resolves previously issued exact-target reference forecasts, applies the fourth-missing telemetry reset, advances independent clocks, feeds only genuine matured errors, emits monitoring records, then issues future persistence forecasts. h=12 feedback begins only when origin+60 minutes arrives. Future values/masks do not affect prefix outputs. Alerts never alter source predictions, expert identity, model parameters or selector state.

Four long/leading/trailing gap boundaries in the reset fixture occur at ticks **3,148,223,279**. Each creates one telemetry era and two horizon-specific detector reset receipts. Normalization/PH/support/warning/cooldown clear; historical records and lifetime counts remain. Twenty old-era h=12 errors subsequently score but are marked ignored for new active support. There are no old-era h=1 residuals in that fixture. Final support is zero after the trailing reset.

Across the eleven fixtures: **2,610 ticks**, **5,220 reference decisions**, **5,013 genuine scored targets**, **42 missing-target outcomes**, **141 boundary-pending predictions**, **24 abstentions**. The latter include six declared forecast failures (three origins × two horizons); the other eighteen are missing/stale-source abstentions. All decisions reconcile. No failure or missing target supplies a fabricated zero error or coverage result. Source ledgers retain the twenty ignored old-era genuine errors; detector acceptance counts exclude them.

The normalization window never reads future errors. Clipping is logged, including during cooldown; heavy h=12 clipping occurs in the sustained/gradual/stress fixtures and limits magnitude information. A value numerically just above the bound due to floating arithmetic counts as clipped under the declared exact comparison. The current-era normalization stays fixed, while PH re-arms on alarms/support loss. This does not establish scale suitability for real CPU streams.

## Tests, preservation and costs

**315 tests passed: all 273 previous tests plus 42 new M6A tests**, zero failures/errors, 47.338 seconds. New tests verify normalization/recurrence, genuine-support boundaries, input/source identity, clipping, warning/cooldown, delayed feedback, exact targets, missingness, resets/old-era exclusion, bounded state/support aging, forecast parity, immutable events, future-suffix invariance, isolation from real data/models, no-overwrite and saved-ledger tamper rejection. The final gated source/configuration/design hashes still match. No M6A threshold or fixture was changed after the saved experiments.

All **571 protected historical SHA-256 values** match, including the complete M5B-2 diagnostic and its unfavorable errors. Selected historical checkpoint fingerprints also remain unchanged. Existing regression fixture reads and opaque historical hashing are permitted verification only; no real observation/error stream is fed to the new detector. Source profiles and normalization use deterministic synthetic CPU only.

The eleven saved-ledger audits pass: they check exact source forecasts/outcomes, event ordering, genuine-only reference input, alert support/threshold/cooldown/source-time provenance, side-ledger consistency and decision reconciliation. Successful/failed output IDs are protected; actual reuse of this saved run is rejected and its files remain unchanged. See [verification report](verification_report.md) for the final receipts.

Sum of measured per-case run times is **4.616 seconds**, including reference generation, detector work, ledger writing and summary calculation, excluding later audits/preservation work. Maximum RSS recorded in case summaries is **49.62 MiB**, cumulative across cases and preceding audits, below the 4 GiB per-tick guard on the 8 GB Mac. Stable initial-case peak was 26.50 MiB. Final audit-phase peak is not separately recorded. Working detector state is bounded by 32 normalization values, 288 target timestamps and a few scalars per horizon; the capped synthetic source audit ledger remains in memory.

## Created files and stopping point

- `configs/dafr_m6a_synthetic_v1.json`.
- `src/dafr/drift_contracts_v1.py`, `drift_v1.py`, `drift_streaming_v1.py`, `drift_fixtures_v1.py`, `run_m6a_v1.py`.
- `tests/test_dafr_drift_v1.py` (42 new tests).
- `reports/dafr/m6a_drift_detection_design_v1.md`, `m6a_preservation_v1.json`, `m6a_synthetic_gate_v1.json` and the separate `m6b_integration_readiness_plan_v1.md`.
- This versioned report directory: synthetic alarm/delay/false-alarm tables, summaries, ledger/preservation/output/final verification, completion/verification reports and artifact inventory.
- Eleven local ignored scenario directories under `data/processed/dafr/m6a_synthetic_v1/m6a-synthetic-20261107-001/`, each with manifest, immutable master event/forecast/outcome/detector-update/alert/telemetry-reset ledgers, summary and completion receipt.

No Alibaba analysis, real-data detector tuning, confirmation/warm-up/final access, ARIMA/XGBoost retraining, LSTM, intervals or dashboard work occurred. No automatic response or expert switch was implemented. Unresolved research decisions include real-data scale/threshold validity, first-window contamination, clipping versus level-step sensitivity, repeated alarms/rebaselining, CPU-level channel integration, false-alarm budgets and future independently evaluated policy responses. They do not block this synthetic milestone, but they do prevent treating the component as a validated real-world drift detector. **M6B has not started; all research execution locks remain unchanged.**

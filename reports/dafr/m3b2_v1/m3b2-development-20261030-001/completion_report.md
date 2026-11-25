# M3B-2 completion report — DEVELOPMENT VALIDATION
Completed 30 October 2026. Run ID: m3b2-development-20261030-001.

## Outcome

Implemented registered real ARIMA and XGBoost adapters, performed the frozen **27 parameter fits**, and completed **18 chronological candidate validation replays**. All nine ARIMA fits and all eighteen XGBoost horizon fits passed their prescribed acceptance checks. No captured convergence warnings, rejected fits or numerical update/forecast failures occurred.

The global h=1 development rule selected:
- **ARIMA C3: (1,1,1)**, no trend, fixed fitted parameters during replay.
- **XGBoost C1: max_depth=2, n_estimators=100, learning_rate=0.05**, with separate direct h=1 and h=12 models.

AIC did not choose ARIMA. h=12 is secondary and uses the same selected settings. Candidate selection was recorded only after every replay ended; no earlier forecast was relabeled or replaced by a hindsight-selected winner.

These are development-validation findings, not independent final-test results or evidence that the proposed DAF-R system improves forecasting. Drift detection, adaptive selection and reliability guidance were not implemented.

## Authorization and data access

The user's attached M3B-2 request explicitly authorized this development-prefix fitting step. New configuration:
`configs/dafr_m3b2_execution_v1.json`.

Only that new scoped configuration enables training. All historical execution/training locks remain unchanged, and confirmation_execution_allowed=false remains in the new configuration and all relevant historical manifests.

New fitting/validation code admits only m_505, m_1426 and m_3028 through exact source hashes and canonical prefix paths. Fit is [0,864), inner validation [864,1152), including missing grid positions. No reserve was fitted or pooled; no later original research validation/test block, real confirmation observations, encrypted suffix or key was opened. Existing regression tests retain their prior development-prefix qualification fixtures.

The original M2B strict-v1 rejection and later development-only qualification records are preserved. Data and model files remain in ignored local versioned directories; no Git commit, upload or remote operation was performed.

## Files created

Engineering files:
- `configs/dafr_m3b2_execution_v1.json`
- `src/dafr/real_adapters_v1.py`
- `src/dafr/real_streaming_v1.py`
- `src/dafr/run_m3b2_v1.py`
- `tests/test_dafr_real_backends_v1.py`
- `reports/dafr/m3b2_backend_gate_v1.json`
- `reports/dafr/m3b2_preservation_v1.json`

Versioned results directory:
`reports/dafr/m3b2_v1/m3b2-development-20261030-001/`.

It contains model_selection.md, comparison.md, runtime_resource_report.md, this report, selection.json, metrics.json, fit_diagnostics.json, runtime.json, validation_metrics.csv, runtime_metrics.csv, verification.json and two actual comparative figures matched_mae_h1.png/matched_mae_h12.png.

Private fitted artifacts:
`models/dafr/m3b2_development_v1/m3b2-development-20261030-001/`
contains **81 files** across 18 candidate bundles: native XGBoost JSON models, ARIMA parameter JSON, identity-scaler/feature specifications and metadata with file hashes, training data/target hashes, fit cutoffs, versions, dependency versions, seeds, warnings, likelihood/AIC/root diagnostics and resource measurements.

Private streaming artifacts:
`data/processed/dafr/m3b2_development_v1/m3b2-development-20261030-001/`
contains **92 files**: the scoped execution manifest and completion receipt, plus each candidate's bootstrap receipt, full event/prediction ledgers, summary and fitted-artifact reference receipt. Each trial has a run identifier incorporating the parent run, machine and candidate.

## Backend gate and engineering decisions

All **130 existing tests plus 17 new backend tests passed before Alibaba fitting**. An initial synthetic preflight exposed a serialization mismatch: sklearn's XGBoost saver adds a scikit_learn wrapper attribute not present in the in-memory native booster. Saving with the native booster API aligned persistence with the registered native loader while retaining strict byte/artifact fingerprints. A failure-injection test also needed to patch statsmodels' delegated instance method rather than the wrapper class. These issues were corrected and the full gate rerun before any real-data fit. No fingerprint guard or candidate setting was relaxed.

The preflight tests cover fixed-parameter sequential ARIMA versus batch filtering with missing observations, at declared rtol/atol 1e-9; missing-tick measurement-skip checks at atol 1e-10; fixed parameters; forecast purity at h=1/h=12; XGBoost feature/scalar shape; model/scaler tamper rejection; fit/checkpoint bootstrap; duplicate assimilation rejection; numerical fallback and stale abstention; exact missing targets and delayed h=12 feedback; suffix-perturbation invariance; no future training targets; scope guards; no-overwrite; memory guards; and selection tie/failure rules.

The real factory accepts artifact references, verifies metadata/source/fit/model/scaler/feature fingerprints and loads only registered backend types. Previous mock-only admission code remains unchanged. Synthetic mock metadata is not reused as real-artifact provenance.

The common CPU input gate remains 24 consecutive genuine grid bins. Every adapter consumes genuine/missing ticks, even while gated. Persistence is available through genuine-value age three; stale or absent inputs lead to explicit abstention. Failed updates would quarantine state, without hidden refitting or skipped-tick recovery. All intervals remain not implemented with null bounds; support counts are scaffolding only.

Bootstrap preloads 23 fit-history slots into causal context without passing them through the live model update again. ARIMA checkpoint reconstruction filters the fit block once with saved fixed parameters in a fresh results object; this is state reconstruction, not optimization/refitting or appending fitted rows twice. The first new state update is validation index 864. Initial telemetry era/streaks are derived solely from the preceding fit mask and logged; no scoring state is seeded with in-sample fit errors.

Offline source event time is distinguished from actual wall-clock model-build time. Candidate checkpoints were prebuilt before validation replay. Their logical replay readiness at the fit cutoff does not imply that training physically happened at the source's synthetic UTC dates or that online fitting latency was tested.

## Development findings and denominators

The matched genuine target counts are:
- h=1: m_505 206, m_1426 236, m_3028 254.
- h=12: m_505 204, m_1426 224, m_3028 242.

Equally weighted macro metrics on those identical target sets:

| Model | h=1 MAE / RMSE | h=12 MAE / RMSE |
|---|---:|---:|
| Persistence | 4.454725 / 6.037374 | 7.809454 / 10.067045 |
| Selected ARIMA C3 | 4.184956 / 5.652008 | 6.538153 / 8.640194 |
| Selected XGBoost C1 | 4.458352 / 6.099749 | 6.612528 / 8.823394 |

Errors are CPU percentage points; macro RMSE is the mean of per-machine RMSE, not a pooled RMSE. Selected ARIMA has lower observed h=1 macro error than persistence. Selected XGBoost's h=1 macro error is slightly worse than persistence, including an unfavorable m_3028 result. Both selected models have lower observed h=12 macro error than persistence. These statements are limited to the inspected development period.

Each selected model issued 704 expert and 160 history-gate fallback predictions over 864 origins, separately at each horizon; zero abstentions. Complete-policy scoring includes more genuine targets: 851 at h=1 and 818 at h=12 over the three machines. The detailed [comparison](comparison.md) and validation_metrics.csv report expert-only matching and complete-policy availability separately; do not cross their denominators to claim gains.

Across all 18 replays, including repeated persistence references, 20,736 immutable issued decisions reconcile exactly into:
- 20,028 genuine scored forecast-target pairs.
- 240 target-unavailable events, with null actual/error/coverage.
- 468 boundary-pending predictions.
- Zero abstentions.

Pending targets were not opened in later blocks. Repeated candidate and baseline records are not independent workload samples.

## Runtime and verification

All **147 tests passed again after fitting**, zero failures/errors, in 4.470 seconds. The pre-training source-hashed gate remains valid for the exact implementation used.

An independent saved-ledger audit reloaded all **18 artifact bundles**, checked their fingerprints, verified exact target/horizon joins and issue-before-arrival order, checked missing outcomes and error arithmetic, and confirmed identical causal context digests across all candidates at all **864 machine/tick combinations**. Attempting the existing run ID was refused before fitting; every existing output byte hash remained unchanged.

All **103 protected historical artifact SHA-256 values** and the **three selected source-prefix hashes** match. The full old inventory is in m3b2_preservation_v1.json; output/checkpoint audits are in verification.json. Historical ARIMA/XGBoost outputs and all earlier milestones remain unchanged.

Serial execution finished in **191.8276 seconds**, including plotting and integrity work. Peak process RSS was **217,497,600 bytes (207.42 MiB)**, below the 4 GiB stop budget. Maximum per-trial p95 adapter forecast duration was **0.015703 seconds**; whole-tick p95 including audit I/O was not separately measured. See [resource report](runtime_resource_report.md) for scope and cumulative-RSS caveats.

Matplotlib automatically used a permitted temporary cache when its default user cache was unwritable. Both generated charts were visually checked and no figure-generation error remains. TensorFlow and Keras remain absent; no dependency was installed.

## Limits and stopping point

- One inner-validation day and three shared-cluster machines provide limited, correlated evidence; no independent test or statistical significance claim.
- Hyperparameters and winners were selected on this same development validation, so selected errors are optimistic estimates of future performance.
- Missingness can be informative, and the relatively complete validation segment differs in coverage from parts of fitting.
- Only three configurations per family and one XGBoost seed were tested; no broad optimality claim.
- Real validation did not contain the synthetic stress tests' long outages. Gap behavior is supported by backend/regression fixtures, not established robustness to every telemetry regime.
- LSTM remains deferred; this is a two-expert fixed-model pilot, not completed DAF-R.
- Drift detection, adaptive switching, prediction intervals, global confirmation settings and final confirmation qualification/execution remain future separately authorized work.
- Replay checkpoints are prebuilt offline; model loading/retraining under real deployment latency and end-to-end issuance p95 remain unverified.

M3B-2 is complete within its authorized scope. Stop here; no M4 or confirmation experiment starts automatically.


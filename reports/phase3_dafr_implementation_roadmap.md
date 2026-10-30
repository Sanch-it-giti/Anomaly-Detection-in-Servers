# DAF-R: Implementation Roadmap

Prepared 29 October 2026. Planning artifact only. Read alongside `phase3_dafr_research_design.md`, which contains the audit, hypotheses, source links, and exact chronological rules. This roadmap extends the existing university project; it does not establish a new algorithm or a performance improvement.

## 1. Current state and preservation rule

ARIMA and XGBoost have comparable historical fixed-origin point forecasts on the same 806 targets. Those inspected metrics remain historical evidence, not a DAF-R tuning target. TensorFlow/Keras are absent; LSTM implementation and results are absent. Five existing tests passed. No new training, package installation, dashboard work, or historical code/result edits occurred in this planning step.

The audit documented two corrections before any future changes: (a) past test observations can legitimately be used after arrival in streaming evaluation, contrary to a blanket sentence in the older protocol; (b) the existing unconstrained ARIMA candidate grid has order-dependent likelihood burn-in. Convergence and finite/root checks are additional audit gaps, not demonstrated historical fit failures. The historical selected order and metrics must not be silently relabeled as corrected results.

Preserve original scripts and outputs. Future fixes use versioned modules and experiment paths with a correction note, old/new configuration, and new hashes. Existing scripts overwrite their forecast CSV paths when executed; do not run them as part of a new streaming experiment. Store future outputs under new run-specific directories, not the historical filenames.

### Historical output SHA-256 at audit

| Artifact | SHA-256 |
|---|---|
| `data/processed/arima_212_holdout_forecast.csv` | `3cbf0922294bcd0206b1e1ab6d6d22f404c69c3807da8c7f919d7ee0506c669b` |
| `data/processed/xgboost_holdout_forecast.csv` | `83296f5e23265ff0e3f1bbf8d66cd45ceb3839601b0647b1444943c0f8ce884d` |
| `data/processed/ec2_cpu_utilization_5f5533_phase2.csv` | `f0d180812da8d8a4bc11117f49ee2cb006fb8d38cf7af002101e49281ae0d64b` |

Relevant code hashes: `src/classical_models.py` = `eb9ac2739f92a3a4c95f42acfbfa6b182d7a7d585cef1902082713a156cda4c9`; `src/run_arima_baseline.py` = `c3da7993d759752f5dcc3ec464a58485bf820dd27e8f79f9e7c1881f42eed7c8`; `src/run_xgboost_forecast.py` = `be44b7fcee8cc91facc23296f20fef32288e05900ecebbf07b23f5b8ec586155`; `src/advanced_preparation.py` = `1d47cc77b02e68414c398bca0e0004146e60b5a0b70872b61b7626b0eff7ec3b`.

## 2. Ordered milestones and acceptance criteria

### M1 — Chronological harness and provenance contract (next implementation milestone)

**Deliverable:** a small offline stream simulator with deterministic stub/persistence forecasts, immutable issued-forecast records, delayed target scoring, and a configuration/manifest format. This milestone does not need TensorFlow or a learned model.

Proposed files, not created in this planning step:

- `src/dafr/contracts.py`: input validation, forecast-record and model-version contracts.
- `src/dafr/streaming.py`: causal observation release, pending targets and horizon-aware scoring.
- `tests/test_dafr_chronology.py`: causal invariance and ledger tests.
- `configs/dafr_protocol_v1.json`: partition, horizon, warm-up, policy and resource choices frozen before confirmation.

Forecast record fields: dataset/machine/run IDs, observation cutoff, origin timestamp, target timestamp, horizon, expert/model version, fit cutoff, scaler cutoff, prediction, interval bounds/status, selected expert or weights, selector-context timestamp, detector state, calibration-score count/latest target timestamp, actual-arrival timestamp, and score availability. Keep issued values immutable; arrival/scoring events are linked records.

**Acceptance:**

1. Perturbing or appending an unrevealed suffix leaves every earlier forecast, interval, selection, and drift state unchanged.
2. No h=12 residual enters any loss/calibration buffer before its target is revealed. Check boundary cases around warm-up and the final origin.
3. A decision scoring target `t` was logged before `y_t` arrived; a forecast for later targets may use `y_t` only after its arrival.
4. Train/scaler/version cutoffs cannot exceed the forecast origin, and target timestamps match cadence/horizon.
5. Saved metrics pair forecasts and observations by keys, not pandas positional/index assumptions; reject duplicates, empty arrays and nonfinite values. Fractional/nonpositive lags are rejected.
6. Missing-data/fallback rules yield the same common scored-origin set for compared methods. No policy silently drops its poor outcomes.
7. Historical artifact hashes remain unchanged. The runner refuses an existing run directory rather than overwriting it.

**Exit:** inspect the ledger and test results before connecting forecasting models. Chronology is the first research requirement; no performance claim is expected at this stage.

### M2 — Independent data manifest and frozen development plan

Inventory all previously inspected NAB files as exploratory. Plan independent machine-series IDs from an external official CPU trace such as Alibaba 2018, subject to release-specific terms/access and schema verification. Do not download a complete cluster into 8 GB RAM. Estimate sizes first, process sequential chunks, and keep each machine separate.

Declare deterministic development/confirmation machine assignment, quality rules, temporal overlap/duplicate checks, units, cadence, source hashes, and the 50/20/10/remainder split before suffix plotting. Aim for at least six confirmation machines if access permits. Shared-cluster dependence is disclosed. The existing NAB test results cannot select detector thresholds, lag sets, memory lengths, or calibration settings. Whole-series-screened NAB alternatives cannot be called untouched.

**Exit:** traceability and holdout manifest established; if external data cannot be obtained, explicitly downgrade claims to exploratory rather than inventing independence.

### M3 — Versioned expert adapters and LSTM environment gate

Implement adapters exposing `forecast(history, horizon)`, observation/state update, model/scaler version and fit cutoff. Use common rolling-origin development folds at h=1 and h=12. Keep a persistence reference.

For ARIMA, log every candidate's common likelihood/burn convention, convergence, finite objective and roots; select future candidates by the common development forecasting criterion. Do not refit merely to replace historical numbers. For XGBoost, keep past-only features with explicit integer lags and documented validation horizons. For LSTM, first separately install a compatible TensorFlow version into `.venv`, verify import and a tiny tensor operation, record versions and CPU memory; only then build the small sequence model proposed in the design. Fit scaling within each development fold, not once on all data before validation. Refit final model/scaler on the permitted prefix only. Freeze epoch count from development; no evaluation-suffix early stopping.

**Exit:** all experts share timestamp/horizon semantics, invalid forecasts trigger logged fallbacks, and the LSTM has a verified runtime. Until then, any two-expert pilot must explicitly say it is incomplete. No inference that installation succeeded from `requirements.txt` alone.

### M4 — Fixed-model streaming benchmarks

Run fixed ARIMA, XGBoost, LSTM and persistence through the same harness. For the primary experiment, update available history and ARIMA state after arrivals but keep fitted parameters fixed. Log h=1 and h=12 separately. Use future versioned paths, keeping the old 806-step experiment distinct.

**Exit:** identical scored targets/information availability, finite valid outputs, per-model error/runtime tables, and a development-chosen fixed reference. Do not choose a baseline by which model wins the final suffix.

### M5 — Adaptive selection without drift

Implement trailing-context summaries, per-expert/horizon matured-loss scores and selection hysteresis. Start with the hard-selection policy in the design, score all shadow experts, and log decisions. Freeze memory/margins/dwell on development streams. Optional soft weights are a separate later ablation.

**Exit:** timing/invariance tests pass; stable ties and unavailable-expert behavior are documented; switch rate and inference overhead measured. Compare A with the fixed baselines without interpreting an observed gain as a proof of DAF-R.

### M6 — Drift response without automatic retraining

Add Page–Hinkley monitoring of CPU level and the selector-independent persistence error. Implement the explicit watch/confirmation/short-memory/cooldown state machine. Record whether each alarm is level-only or error-confirmed. Choose threshold and normalization on development/stress streams only; document reset behavior. Evaluate abrupt, gradual, variance, recurring and no-change controls with declared seeds/change points.

**Exit:** D-versus-A ablation and known-change detector diagnostics can be computed; late alarms, repeated alarms and missed changes are retained. No retraining is triggered in the primary experiment. Add ADWIN only as a prespecified detector comparison if resources allow.

### M7 — System calibration and reliability guidance

Implement per-policy/horizon rolling absolute-error quantiles with discrete finite-sample rank and support/status handling. Seed buffers from out-of-sample chronological warm-up. Score and store the residual of the actual issued system center, not an in-sample or hindsight-selected expert forecast. Maintain each expert's shadow reliability state for the proposed eligibility gate. Add degraded mode if all experts fail the gate.

Tests must cover a switch, an unavailable expert, a model-version change, h=12 feedback delay, insufficient scores, a requested quantile rank beyond support, and interval width/availability reporting. Compare D versus Full and A versus R to isolate the coverage gate. ACI, if subsequently implemented, is a separate calibration ablation with documented endpoint/projection behavior; empirical coverage claims remain qualified for dependent data.

**Exit:** coverage, interval score, width and availability computed together; no infinite or unavailable interval is silently treated as successful narrow coverage. Report if better coverage is purchased with unusable width.

### M8 — Controlled retraining extension and final independent experiments

Only after M1–M7, consider the capped serial retraining policy. Compare identical scheduled refits across corresponding variants and include a matched periodic baseline. Track fit cutoffs/completion timestamps and replace experts only after successful completion. Use no change-triggered unlimited hyperparameter search.

Freeze the full configuration, primary hypothesis/metric, confirmation IDs and seeds, then run independent confirmation streams once. Repeat small LSTM seeds (e.g., three) as stochastic sensitivity, not as extra independent workloads. Aggregate per-series/horizon results and machine-cluster uncertainty where justified. Separate no-refit primary results from retraining extensions and historical NAB replays.

**Exit:** complete P/F/A/D/R/Full ablation tables including failure cases, null/negative findings, dependence limitations and actual memory/latency cost. No novelty/performance assertion beyond the measured evidence.

## 3. Resource controls and stopping rules

- Execute one series and one candidate fit at a time, with numeric threads limited to 1–2.
- Pilot LSTM: 24-step input, 16 units, batch 32, at most 30 development epochs; measure rather than assume memory use.
- Keep bounded loss/calibration/history buffers and bounded logs flushed to disk. Use a small trace subset before expanding machines.
- Proposed measured goals: peak process resident memory below 4 GB and p95 forecasting issuance under 5 seconds on the user's Mac. Record OS memory pressure as well as process memory when available.
- Optional refitting: trailing 2,016 observed values, at least 576 fresh arrivals between refits and at most two events per series-day. Count all candidates and all expert fitting costs.
- On numeric/backend/memory failure, retain the preceding valid model or use the declared fallback, log the event, and include it in aggregate reporting. Do not hide an unsuccessful LSTM run or declare the full bank complete.

## 4. Experiment artifacts planned for later

Use a manifest plus separate immutable forecast and observation/score events for each run. Store raw metrics, horizon-specific summaries, drift/switch/retraining logs, hardware/runtime versions, and policy configurations. Include release/license provenance and machine assignment. A final research report should explain what was fixed before confirmation, what was learned on development data, and any deviation.

Suggested future paths: `data/processed/dafr/<run_id>/`, `reports/dafr/<run_id>/`, and `models/dafr/<run_id>/`, with appropriate ignored model/data artifacts. These are planned locations only; no new directories/modules/checkpoints were created for them during this planning task.

## 5. Scope of this completed planning step

Created only `reports/phase3_dafr_research_design.md` and this roadmap. Existing code, requirements, forecasting metrics, test datasets and forecasts are preserved. Sources and audit limitations are in the companion design. The next concrete implementation milestone is **M1: the chronology/provenance harness with deterministic stub forecasts and causal-invariance tests**. Model training, dashboard work and independent final experiments follow only after that foundation is verified.

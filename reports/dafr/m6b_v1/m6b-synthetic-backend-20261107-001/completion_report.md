# M6B completion — synthetic real-backend engineering verification only

7 November 2026. Run `m6b-synthetic-backend-20261107-001`. **M6B is complete and stopped.** No real-data drift performance, independent generalization or DAF-R improvement is claimed. Confirmation remains disabled.

## Integration delivered

The separate `RealBackendDriftStreamV1` composes the unchanged registered ARIMA/XGBoost adaptive backend with the unchanged M6A persistence-error detector. It has no drift response, fitting callback, model injection interface or selector mutation path. Original backend forecast/outcome contracts and records remain immutable. The wrapper accepts the existing synthetic fixture registry only; historical checkpoint execution remains disabled.

The reference remains **persistence/rule_v2 absolute genuine exact-target error**, not ARIMA, selected-policy or fallback-policy error. A typed bridge retains original backend records and validates their links before creating a declared M6A-compatible view. The only version mapping is the backend envelope version to the unchanged actual persistence algorithm version. Original forecast/outcome IDs, values, context, timestamps, sequence and telemetry era are preserved. No original ledger is edited or relabelled.

Both horizons keep first32 genuine-error median/MAD normalization, scale floor0.1, clipping±4, minimum64 errors in288 elapsed ticks, PH delta0.05, warning4/alarm8 and24-tick cooldown. Fourth-missing era resets and old-era exclusion remain unchanged. Frozen M5A selection settings are untouched.

Every backend tick completes reveal → exact-target scoring → telemetry/support/selector feedback → real state updates → shadow/selection/persistence issuance. Only then are external detector clocks, genuinely matured reference errors and alerts recorded. A separate monitor sequence and backend barrier make this ordering auditable. The monitor receives no later target value and cannot change current issuance. Enabled and disabled monitoring produced **identical full backend steps and forecast ledgers**, including selected centers, availability, causal state hashes, selection and outcomes.

## Measured synthetic verification

| Fixture | Ticks | Decisions | Genuine scores, all policies | Missing-target outcomes | Pending | Unissued attempts | Alarms h1/h12 | Warnings h1/h12 |
|---|---:|---:|---:|---:|---:|---:|---|---|
| sustained |280|2240|2188|0|52|0|5 / 5|5 / 5|
| gaps_failures |450|3600|2820|144|14|622|0 / 2|3 / 11|
| update_failure |180|1440|1085|27|24|304|0 / 0|0 / 6|
| Total |910|7280|6093|171|90|926|5 / 7|8 / 22|

Decisions reconcile:6093 genuinely scored +171 missing targets +90 pending +926 unissued =7280. Unissued attempts include history-gated expert shadows, numerical/unavailable shadows and stale/absent policy abstentions; they are not all policy abstentions. There are1710 linked genuine persistence outcomes before old-era filtering. Full detector counters, clipping, support and ignored-old-era counts are in `verification.json`.

Sustained-change alarms at both horizons occur at relative ticks162,188,214,240,266, the same reference-error behavior as M6A: first delay2 ticks (10minutes), then repeated alarms after cooldown. These are known generated interventions, not real workload/concept-drift labels. The gap fixture emits two h12 alarms and fourteen warning entries; it is not defined as validated real-world drift ground truth, so no false-alarm-rate claim follows. Drift alarms are not forecast failures, telemetry resets or proof of concept drift.

The gap fixture has four telemetry resets and one ordinary frozen-selector loss-based switch. The update-failure fixture has one telemetry reset and no expert switch. Five resets produce ten horizon-specific detector reset receipts. The single selector switch is identical with monitoring disabled; **zero switches/refits/parameter changes were caused by drift**.

Controlled faults reach actual backends: one ARIMA h1 and one XGBoost h12 numerical forecast failure in `gaps_failures`; one ARIMA state-update numerical failure at tick40 in `update_failure`. The latter causes honest persistent unavailability:139 later unavailable update receipts and278 unavailable horizon attempts, in addition to two failed horizon attempts on the failure tick. No hidden state catch-up or refit occurs; independent persistence monitoring continues.

## Tests, independent audit and integrity

**341 tests passed:315 existing +26 new, zero failures/errors,138.452seconds.** Command: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v`. The new source/config/design gate was frozen after these tests and before saved execution. The initial24-test integration run also passed; the final suite includes two additional isolation/no-overwrite checks.

New tests cover exact reference/provenance links, registered backend admission, delayed h12, matching horizons, causal issuance barriers, future-suffix value/mask invariance, enabled/disabled parity, missing targets, fourth-missing resets, old-era feedback, normalization/support, repeated alarms/cooldown, numerical/update failures, immutable records, no observation-file reads by the integration, existing-directory refusal and saved-ledger tamper rejection. All original315 tests retain their existing regression-only fixture access; the new monitoring runner uses only generated observations, never real outcome-ledger analysis.

All three saved-ledger audits pass. The auditor reconstructs detector clocks, normalization, errors and alerts from original linked persistence forecasts/outcomes; verifies the complete eligible error set, source identity, exact targets, arithmetic, output hashes, event sequencing, issuance barriers and forecast parity. See `chronology_and_provenance.md` for an example.

**690 protected historical SHA-256 entries match**, extending the prior571 with M6A artifacts and inventory. The original historical registry verifies **six checkpoint bundles /27 files** without observation loading or historical model execution. Synthetic fixture checkpoint files also retain their pre-replay hashes. Actual retry of this run ID was rejected before generation; all35 then-existing run/report files remained byte-identical. Original code/configurations/results are unchanged; `git diff --stat` is empty. Newly generated caches are not research artifacts and are not included in this protection statement.

## Resources and files

Total saved execution including checkpoint generation/audits: **56.808664seconds**, peak process high-water RSS **352.53125MiB**. Case times18.729638 /25.022620 /11.486426seconds. These include both enabled/disabled model runs, with small audit ledgers in memory; they do not benchmark production latency or isolated detector memory. See `runtime_memory.md`.

New implementation/configuration:

- `configs/dafr_m6b_synthetic_backend_v1.json`
- `src/dafr/drift_real_streaming_v1.py`
- `src/dafr/run_m6b_v1.py`
- `tests/test_dafr_drift_real_v1.py`
- `reports/dafr/m6b_integration_design_v1.md`
- `reports/dafr/m6b_preservation_v1.json`
- `reports/dafr/m6b_backend_gate_v1.json`
- `reports/dafr/m7_reliability_interval_readiness_plan_v1.md`

New immutable synthetic checkpoints, manifests and three case ledgers are under `data/processed/dafr/m6b_synthetic_backend_v1/m6b-synthetic-backend-20261107-001/`. Each case saves backend events, forecasts, disabled forecasts, outcomes, monitor events, summary and hashes. Public verification, chronology, runtime, protection and completion reports are under this report directory. A final SHA-256 inventory records delivered files and excludes itself.

## Limitations and next step

M6A's missed abrupt h1 level step, early-support limitations, warnings after benign changes, clipping and repeated alarms remain limitations; no threshold/channel was retuned or added. The monitor detects worsening persistence error, not proven concept drift. Real-data robustness, scale validity, contaminated initial normalization, false-alarm budgets, rebaselining and useful alarm responses remain research questions. M5B-2's lack of adaptive improvement remains unchanged.

Synthetic XGBoost fixture boosters were trained only before replay; ARIMA used stored known coefficients with real filtering, not parameter optimization. There was **no real-data training, no replay fitting attempt and no new Alibaba observation/confirmation access**. No interval, CPU-level detector, LSTM or dashboard was implemented. The synthetic calendar uses the existing artificial2000 epoch and is not execution wall time.

The recommended next step is separate review/authorization of the M7 reliability-interval design and synthetic verification scope. M7 and real-data drift evaluation have not started; historical locks and confirmation restrictions remain in force.

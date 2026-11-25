# M7B completion — synthetic real-backend engineering verification only

Run `m7b-synthetic-backend-20261107-001`,7 November2026. **M7B is complete. Stop after M7B.** Confirmation remains disabled. No Alibaba evaluation, real-world coverage guarantee, independent confirmation or DAF-R performance improvement is claimed.

## Integration and frozen rules

New typed real-backend interval contracts retain actual BackendForecastV1, RealVersion, registered checkpoint/parameter/state hashes, training/scaling/availability cutoffs and original forecast/outcome IDs. No real forecast is cast into mock metadata, and original contracts, code, configurations and artifacts are unchanged. A separate M7B configuration/provenance gate admits only the registered generated-data checkpoint recipe.

The M7A rules remain frozen: both90%/95%, exact ceil((n+1)×nominal_percent/100)-th absolute-error order statistic, minimum100 genuinely matured own-policy errors, capacity288,288-grid-tick age, raw unclipped center±radius, null cold-start/insufficient bounds and exact h1/h12 targets. Independent buffers belong to fixed ARIMA shadow, fixed XGBoost shadow, complete adaptive policy and persistence. Fixed shadows are honestly unavailable when their expert fails; they are not silently relabelled as full fixed-expert-plus-fallback policies. Adaptive intervals calibrate its own actual selected/fallback predictions across ordinary switches, never a different policy's or chosen expert's residuals. Model/version/checkpoint changes are rejected rather than silently transferring calibration.

The new driver preserves the point backend's advance implementation with explicit pre-state support and issuance hooks. The causal order is reveal → prior exact-target scoring → telemetry/selector/drift/calibration support → one genuine/missing observation update per real backend → fixed expert shadows → unchanged selection/persistence → corresponding90/95 intervals. Fourth-missing resets occur once per long gap. Old-era targets can score their original immutable bounds but cannot seed new support. Missing/unissued/pending forecasts never receive fake errors or coverage. Intervals/drift have no selection/refit/parameter-changing callbacks.

## Parity and independent verification

Every tick is compared across intervals-enabled M7B, intervals-disabled M7B and the original unchanged M6B driver. **Full point/backend steps, centers, selections and source event ledgers match exactly. All drift `(kind,record)` payloads match exactly.** The new integration timeline records support before observation-state updates, as requested; M6B's legacy monitoring barrier/envelope was after issuance and is not misrepresented as having the same orchestration position. No detector or selector scientific rule changed.

All four independent saved-ledger audits pass. The unchanged M7A dictionary/deque auditor reconstructs calibration support/expiry/era, exact ranks, original links and interval outcomes without calling either interval engine. The separate M7B auditor additionally checks real-model provenance/cutoffs, source/legacy parity, pre-state chronology, drift payload replay and nesting. **5659 available95/90 interval pairs satisfy nesting**, with identical support per pair. Every available95% interval contains its90% counterpart.

**409 tests passed:381 existing +28 new**, zero failures/errors,182.178seconds. The final source/config/design gate was frozen after this run and before saved execution. The initial27-test integration suite also passed. New tests exercise actual adapters, both nominal levels, exact quantiles, delayed h12, separate policy/horizon support, minimum/expiry, missing targets, numerical/update failures, fallback/abstention, a real loss-driven switch retaining complete-policy calibration, long-gap resets, suffix invariance, no new observation reads, coverage/score arithmetic, immutable records, registered provenance, checkpoint preservation, controls and no-overwrite/tamper rejection.

Command: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v`.

## Measured coverage and availability

The four fixed synthetic fixtures are continuous420 ticks, growing variation360, gaps/failures450 and update failure180. Checkpoints use96 generated fit values: actual ARIMA(1,1,1) fixed known-coefficient filtering and two small direct native XGBoost fits before replay. There is no real-data fitting or replay refitting. These small fixtures are not research model-selection evidence.

Complete adaptive-policy diagnostics at90% nominal; widths are mean raw issuance width in CPU percentage points:

| Fixture | h1 coverage (available / genuine matured) | h12 coverage (available / genuine matured) | Width h1 / h12 |
|---|---|---|---|
| continuous |89.97% (319 /419)|93.27% (297 /408)|1.886335 /8.586516|
| growing |81.08% (259 /359)|68.35% (237 /348)|1.997735 /11.987619|
| gaps_failures |93.65% (126 /419)|89.81% (108 /409)|2.082831 /8.856210|
| update_failure |79.45% (73 /173)|86.27% (51 /162)|2.376225 /9.017157|

Growing variation also undercovers at95% nominal:87.64% /78.06%, h1/h12. All unfavorable results remain, without retuning. Earlier M7A growing-variation undercoverage (57.53% /56.12% at90% nominal) remains an unchanged **different mock-fixture result**, not a baseline against which this new real-backend fixture proves improvement. Dependent/nonstationary/switching residuals do not provide automatic exchangeability-based or conditional guarantees.

Both nominal levels and all four policies are retained in the64-row [own-policy table](coverage_width_availability.csv), including mean/median width, genuine-scored width, proper interval score, support/availability, fallback/unissued counts, missing/pending and coverage gap. The separate64-row [common-target table](common_target_comparisons.csv) uses matching original origins, horizons, targets and contexts across all policies. Common h1/h12 sample counts are319/297,259/237,49/31 and0/0 respectively. Update-failure common comparisons are **unavailable**, not zero error or coverage: fixed ARIMA fails before it accumulates100 errors. Its absence is not hidden by adaptive-only results. See the [coverage/availability report](coverage_width_availability.md).

Source accounting across1410 ticks:11280 point attempts =10041 genuine scores +171 missing outcomes +142 pending +926 unissued attempts. The latter include gated/failed expert shadows and policy abstentions, not926 equivalent abstentions. Two nominal levels yield22560 interval attempts =10900 genuine available interval scores +9182 genuine interval-unavailable outcomes +342 missing outcomes +284 pending +1852 center-unavailable attempts. Available intervals at issuance total11318; pending/missing targets do not acquire retrospective coverage labels. No unbounded interval or endpoint clipping is used; no raw endpoint was outside[0,100] in these fixtures.

The controls contain three ordinary loss-driven expert switches, five telemetry resets and eighteen statistical alarms. They remain separate events. None is caused by interval availability or a new drift response; point and monitor payloads match the original M6B controls. No interval-based expert gating, drift-triggered calibration reset, automatic refit or ACI was added.

## Preservation and resources

**882 protected historical hashes match**, extending739 with all142 M7A inventoried files plus its final inventory. The six historical selected checkpoint bundles /27 files match without historical model refitting. Newly generated synthetic checkpoint hashes match before/after all cases; they are isolated in the new versioned run, never promoted to the historical registry. Original ARIMA/XGBoost outputs, M1–M7A artifacts, scientific settings and execution locks remain unchanged. `git diff --stat` is empty; no commit/push was performed.

An actual retry of this run ID was rejected before generation; all80 then-existing saved files remained unchanged. See `overwrite_protection.json`, `preservation_verification.json` and final hashes. New source/interval/provenance hashes are verified separately from original historical artifacts.

Whole saved execution including checkpoint build, three controls, writing and independent audits: **160.846943seconds**. Peak cumulative process high-water RSS: **729448448bytes =695.65625MiB**, below the4GiB guard on the8GB Mac. Per-fixture times are50.583673,42.841418,41.652014 and19.192149seconds. These are engineering harness costs, not isolated calibrator latency or measured production p95 issuance latency. Small capped audit ledgers are kept in memory; production long-duration storage remains untested. No dependency/TensorFlow installation occurred. See `runtime_memory.md`.

## Created files

- `configs/dafr_m7b_synthetic_backend_v1.json`
- `src/dafr/interval_real_contracts_v1.py`
- `src/dafr/interval_real_v1.py`
- `src/dafr/interval_real_streaming_v1.py`
- `src/dafr/audit_m7b_v1.py`
- `src/dafr/run_m7b_v1.py`
- `tests/test_dafr_intervals_real_v1.py`
- `reports/dafr/m7b_integration_design_v1.md`
- `reports/dafr/m7b_preservation_v1.json`
- `reports/dafr/m7b_backend_gate_v1.json`
- `reports/dafr/m8_research_evaluation_submission_readiness_plan_v1.md`

New immutable synthetic checkpoints/manifests and four case ledgers are under `data/processed/dafr/m7b_synthetic_backend_v1/m7b-synthetic-backend-20261107-001/`. Cases include authoritative and control source/drift events, original predictions/outcomes, intervals/calibration scores/interval outcomes, timeline, manifests, summaries and hashes. This public report directory contains own/common CSVs, measured verification, coverage/availability, parity/chronology/provenance, runtime, preservation, completion and final artifact inventory. No historical file is overwritten.

## M8 readiness and restrictions

The [M8 plan](../../m8_research_evaluation_submission_readiness_plan_v1.md) documents intended partitions and current evidence: development fit[0,1152) was inspected, with actual historical fitting[0,864) and inner validation[864,1152); original validation[1152,1612) is inspected M4A/M5B-2 evidence. Warm-up[1612,1842) and final[1842,2304) remain restricted. Confirmation suffixes remain sealed. Neither existing inspected results nor new final outcomes may be used to tune interval settings and then claim unbiased improvement on those same targets.

**Zero confirmation machines have verified full V2 qualification.** Published prefix metadata already show m_1878 and m_3836 fail75% coverage; seven others pass that aggregate gate only, with run/history/origin/target-pair checks unknown. No confirmation observation or fresh mask was inspected to fill those unknowns. Development-only qualification does not transfer. A separately authorized value-blind confirmation-prefix check, unchanged thresholds, original nomination/reserve order and a frozen globally scoped manifest are prerequisites to independent confirmation, followed by explicit execution authorization.

M8 also needs a separately verified real-data driver/typed admission boundary, actual checkpoint/replay/warm-up policy and final-origin scoring convention. Current M7B accepts synthetic registries only; its guards must not be disabled to run real data. Full reliability-guided selection/CPU-level drift response/LSTM are not implemented. The minimum honest submission can instead report the verified two-expert engineering/development framework and negative findings, without claiming full DAF-R efficacy or independent confirmation.

M6A's missed abrupt h1 step, early-support limits and repeated alarms; M7A/M7B undercoverage; mixed-policy calibration, missingness, small effective sample size and scarce common support remain limitations. M5B-2's lack of adaptive improvement is preserved. There was no new Alibaba observation, restricted calibration/final/confirmation access, real-data refit, LSTM or dashboard work. **M8 is conditionally planned, not started or authorized.** Stop after M7B.

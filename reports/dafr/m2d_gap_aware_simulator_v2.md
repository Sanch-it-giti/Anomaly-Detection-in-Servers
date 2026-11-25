# M2D — Finalized gap-aware engineering pilot and missing-event simulator
Completed 30 October 2026. Scope: Option B engineering pilot with deterministic stubs and persistence only.

## 1. Outcome and authorization boundary

The separate V2 simulator is implemented and verified. M1 source and behavior are unchanged. M2B still has zero qualified machines under strict v1; M2C remains an unchanged feasibility/design record. No nominee was newly qualified or promoted. No Alibaba observations, suffix payloads, encrypted keys, forecasting outcomes or real model artifacts were used for the synthetic demonstration.

The user's M2D instruction approves the specified engineering behavior. It does not approve a final DAF-R research protocol, M3 training or confirmation evaluation. Both `confirmation_execution_allowed` and `m3_training_allowed` remain false, in the new configuration as well as the original manifests. Option C is disabled. No dependency installation was needed.

## 2. Created implementation and configuration

- [Final engineering configuration](../../configs/dafr_engineering_pilot_v2.json): fixed V2 engine settings, development-informed prefix screens, decision semantics, resource caps and unresolved research decisions.
- [V2 contracts](../../src/dafr/contracts_v2.py): frozen ticks, causal contexts, forecast/abstention records, target outcomes, support snapshots, telemetry resets and ordered event bundles.
- [V2 simulator](../../src/dafr/streaming_v2.py): exact-target ledger, fixed stubs, history gate, persistence/abstention, era resets, support aging and exclusive output writer. CLI generates synthetic data only; no external dataset loader exists.
- [V2 tests](../../tests/test_dafr_missingness_v2.py): 31 new automated tests, including causal invariance, metadata validation, missingness, support and historical preservation.
- [Preservation inventory](m2d_preservation_v1.json): 69 baseline SHA-256 values covering the 66 previously protected artifacts plus all three M2C deliverables.
- This report: `reports/dafr/m2d_gap_aware_simulator_v2.md`.

New synthetic outputs are confined to:
`data/processed/dafr/missing_data_v2/m2d-synthetic-20261030-001/`.

That directory contains ten files: `manifest.json`, `completion.json`, `summary.json`, and `ticks.jsonl`, `forecasts.jsonl`, `abstentions.jsonl`, `outcomes.jsonl`, `states.jsonl`, `resets.jsonl`, `events.jsonl`. Existing data ignore rules keep generated run outputs local.

## 3. Exact engineering decisions

### Clock and observation availability

Require aware UTC timestamps exactly aligned to five-minute boundaries, including seconds/microseconds checks. Every successive tick must be exactly 300 seconds later. Missing positions are explicit null-valued events with an identifier-style reason such as `quality_failed`. Genuine CPU must be finite in [0,100], including genuine zero CPU. Duplicate, backward, skipped, off-grid and ambiguous value/reason events are rejected before changing state.

Historical replay assumes measurements are available at their grid label/right edge, with zero extra delivery delay. Late arrivals/revisions are unsupported and rejected; no retroactive scoring or state update is inferred from Alibaba measurement timestamps.

### Event ordering

At every tick:

1. Reveal the genuine or missing event and append its original grid position.
2. Resolve all previously issued predictions whose exact target matches this timestamp. Genuine targets create linked scores; missing targets create linked `target_unavailable` events with null actual/error/coverage fields.
3. On the fourth consecutive missing tick, start the new telemetry era and clear active support once. Add eligible genuine matured errors, and expire support outside the elapsed-time window.
4. Snapshot causal state, then issue future decisions for h=1 and h=12 before any subsequent tick is revealed.

All log sequences increase globally within a run. Targets are origin + 300 seconds or origin + 3,600 seconds. Missing targets are finalized unavailable at their own timestamp, never moved to the next genuine value. Forecasts targeting beyond the stream remain pending. Abstentions never enter pending-target or error buffers.

### Shared history gate and fallback attribution

Every learned-style stub uses the same 24-consecutive-genuine-bin gate and receives the same immutable causal context object. The bounded window preserves missing positions. Its digest and last-genuine cutoff/age are stored in every decision. Forecasting never consults future target availability.

The persistence reference is independently available when its latest genuine value is at most three ticks old. Other fixed stub policies use exactly that reference as fallback when their history gate fails or their stub declares itself unavailable. At the fourth stale tick, or before any genuine measurement, they explicitly abstain with null prediction/source. Recovery makes persistence available immediately; the learned gate requires 24 new consecutive genuine positions.

The requested policy ID/version remains fixed. A fallback is attributed to that policy's own issued center, with `selected_expert=persistence`, its source version and the reason logged separately. When the stub becomes available again, this is source recovery, not adaptive model selection. Each policy accumulates only its own genuine matured errors, including errors from its own fallback decisions; it never borrows the reference policy's buffer.

Training/scaling/version-availability cutoffs are null for these unfitted rules. Contract validation rejects any non-null fitted-data cutoff after its origin, or a model-availability time preceding its fitting/scaling data. Decisions are immutable; score events retain the original prediction.

### Telemetry-era convention

Start at era 0. A missing streak of exactly four increments the era once, including a leading four-tick gap. Further missing ticks in the same gap do not reset again. A genuine arrival ends the missing streak but retains the new era. A later long gap can create the next era.

Reset provenance records the triggering tick, event sequence, timestamp, previous/new era and reason. It clears active support, not the audit ledger, pending forecasts or fixed model parameters. Old-era forecasts are still scored against genuine exact targets, but their errors do not seed new-era support. Lifetime genuine-score counts remain available.

This is a telemetry-quality reset, not a drift alarm or evidence of workload/concept drift. No detector is instantiated.

### Support scaffolding, without calibration or selection

Buffers are keyed by fixed policy ID, policy version and horizon; the active era is explicit. Store genuine matured errors only, at most 288. At issue index i, retain target indices j satisfying **i−287 ≤ j ≤ i**, additionally requiring the forecast to have been issued in the current era. Age by target time on the original grid, including missing ticks.

`support_ready` means only that at least 100 such errors exist. It does not certify calibrated intervals, activate a reliability gate, or choose an expert. All interval statuses remain `not_implemented`, all bounds are null, and coverage outcomes are null even after support becomes ready. There is no quantile estimator, drift detection, loss-based switch or refitting.

The policy/version namespace is fixed during each run. Model-version replacement and real adapter state updates are deliberately deferred rather than inventing research semantics.

### Prefix screens and research partitions

The new pilot configuration retains the M2C screens: at least 500 genuine prefix bins, 75% observed coverage, a 48-bin longest genuine run, 40% eligible learned origins, and 400 potential genuine-target pairs separately at h=1 and h=12, using the original fixed prefix. These are frozen **development-informed engineering choices**, not validated optimal thresholds or proof of model/data sufficiency. Original per-bin quality rules and nomination order remain unchanged.

M2D does not run qualification, inspect confirmation prefix masks or execute fit/validation/warm-up/final partitions. Existing research boundaries remain fit [0,1152), validation [1152,1612), warm-up [1612,1842), final [1842,2304), counting missing grid positions. All synthetic ticks are engineering events, not a held-out research evaluation.

### Output protection and lightweight implementation

Only the standard library is used. The pilot keeps at most 24 history slots and 288 errors per policy/horizon; only unresolved issued targets remain pending. It caps a run at 2,304 ticks and eight stub policies because the immutable audit ledger remains in memory. These resource guards are engineering limits, not dataset-selection criteria.

The writer reserves a unique directory with exclusive creation, rejects symlinked output ancestors and traversal identifiers, and opens every artifact exclusively. It never updates an existing run, including a failed run. An immutable initial manifest is paired with a separate completion/failure receipt; it is not rewritten. Failed runs retain their partial audit and reserved ID. The manifest includes fixed engine settings, their digest, and stub identities/versions.

## 4. Synthetic demonstration and actual event ledger

Synthetic grid: 180 slots beginning 1 January 2026 at 00:00 UTC, with values defined by a deterministic arithmetic fixture. Missing zero-based slots are 0–1, 28, 56–58, 88–93 and 176–179: leading, one-tick, three-tick, six-tick and trailing four-tick gaps. These are invented fixtures explicitly identified as synthetic, not Alibaba measurements.

Policies: persistence, `stub_last`, and `stub_offset` (fixed offset 0.25 per horizon tick). No policy is trained.

| Measurement | Saved result |
|---|---:|
| Grid ticks / genuine / missing | 180 / 164 / 16 |
| Eligible learned origins | 72 (40% of all grid positions) |
| Policy/horizon decisions | 1,080 |
| Issued predictions / abstentions | 1,044 / 36 |
| Genuine scored forecast-target pairs | 933 |
| Missing-target outcomes | 78 |
| Boundary-pending predictions | 33 |
| Telemetry resets | 2 |
| Demonstration elapsed time | 0.1761 seconds |
| Peak process RSS on this Mac | 23,379,968 bytes (22.30 MiB) |

Counts of outcomes combine three policies and two horizons; they are not 933 independent CPU timestamps. Every issued prediction is accounted for: 933 + 78 + 33 = 1,044. Every decision is accounted for: 1,044 + 36 = 1,080. This is an availability/chronology demonstration, not forecasting performance evidence. RSS is the Python process high-water mark from macOS `resource.getrusage`, not whole-system memory or future model cost.

For each learned-style stub and each horizon, the ledger has 72 expert predictions, 102 persistence fallbacks and six abstentions. h=1 yields 162 genuine scores and 12 unavailable targets; h=12 yields 149 genuine scores, 14 unavailable targets and 11 pending predictions per policy. The trailing long gap clears active support to zero in era 2, while lifetime counts remain intact.

The following rows are drawn from the saved ledger, restricted to `stub_last`. Times are synthetic UTC on 1 January 2026.

| Record ID | Origin | h | Exact target | Era | Issue status / value | Later outcome |
|---|---|---:|---|---:|---|---|
| decision-185 | 01:20 | 12 | 02:20 | 0 | Fallback / 47 | target_unavailable; no error |
| decision-338 | 02:15 | 1 | 02:20 | 0 | Expert / 40 | target_unavailable; no error |
| decision-352 | 02:20 | 1 | 02:25 | 0 | Fallback / 40 | Genuine actual 42; absolute error 2 |
| decision-1192 | 07:20 | 1 | 07:25 | 0 | Fallback / 46 | target_unavailable |
| decision-1220 | 07:30 | 1 | 07:35 | 0 | Fallback / 46 | target_unavailable |
| decision-1235 | 07:35 | 1 | 07:40 | 1 | Abstained / null | No pending forecast |
| decision-1268 | 07:50 | 1 | 07:55 | 1 | Fallback / 44 | Genuine actual 45; absolute error 1 |
| decision-1581 | 09:45 | 1 | 09:50 | 1 | Expert / 40 | Genuine actual 41; absolute error 1 |

At 07:35, reset-1 (sequence 1231) occurs on tick-92, the fourth missing tick, before new-era decisions. At 14:55, reset-2 (sequence 2446) occurs on tick-180. The earlier 02:20 h=12 forecast is never retrospectively scored against 02:25.

Reproduce using a **new** run ID:

```bash
PYTHONPATH=src .venv/bin/python -m dafr.streaming_v2 --demo --run-id m2d-synthetic-NEW-ID
```

Reusing `m2d-synthetic-20261030-001` must raise FileExistsError and preserve all ten files.

## 5. Verification

Command:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

**84 tests passed: all 53 previous tests and 31 new V2 tests**, with zero failures/errors. The completed full run reported 1.226 seconds.

New tests cover leading/trailing/all-missing streams; 1/3/4-tick gaps; 24-genuine-bin recovery; fallback expiry; genuine zero CPU; exact h=1/h=12 missing targets; delayed feedback; one reset per long gap; old-era score exclusion from active support; future suffix value/mask/length perturbations; identical immutable expert contexts; event order; fallback attribution; support minimum/cap/elapsed-time expiry; no intervals even with ready support; invalid inputs/cutoffs; duplicate/revised ledger entries; output no-overwrite, symlink/traversal/failure protection; and all 69 preservation hashes.

The hash inventory matched before and after testing and the saved demonstration. It includes M1 source/configuration/saved outputs, M2/M2B manifests/reports/code, M2C artifacts, and historical ARIMA/XGBoost forecast CSVs. Sealed ciphertext payloads were not reopened or decrypted; their existing seal receipt is among the protected hashed files.

## 6. Remaining research decisions and readiness

No unresolved choice blocks this **synthetic engineering pilot**. Decisions that materially affect research remain disabled rather than silently fixed:

- Expert adapters, genuine-data training windows, common rolling validation, ARIMA missing-state updates and XGBoost/LSTM feature/scaler provenance.
- Model-version replacement and its effect on policy calibration histories.
- Drift thresholds/normalization, genuine-update warm-up, watch/cooldown and telemetry-reset interactions.
- Adaptive loss weighting, minimum support, hysteresis/dwell and fallback-to-expert fairness.
- Actual interval construction, coverage monitoring/reliability gates and sensitivity to reset-induced loss of support.
- Value-blind confirmation-prefix structural qualification, reserve replacements, sufficient independent machines and full research settings freeze.
- Explicit future permission for confirmation execution; it is not granted here. Option C feature parity also remains deferred.

The chronology foundation is ready to support a **future separately scoped expert-adapter milestone**. The current engine intentionally accepts only deterministic stub types and has no real-model observation-update hook; integration requires an explicit adapter contract, causal state-update tests and model-specific failure tests before any model is connected. It is not ready for production-scale streaming, training or final confirmation evaluation.

No DAF-R improvement, novelty, seasonality, drift-detection accuracy or interval calibration result is claimed. Work stops after M2D.


# M3B-1 — Real-adapter implementation design v1
Prepared 30 October 2026. Design only: no real adapter, model fitting or confirmation execution implemented.

## Preservation and entry point

M3A's interface/mocks and the approved M2D configuration remain unchanged. A future M3B-2 implementation must create a separately versioned real-adapter module and development-only driver. Do not make the mock factory accept arbitrary objects, relabel a real artifact as synthetic, or replace historical fixed-origin model outputs.

Required real-backend lifecycle: validated checkpoint/version metadata → bootstrap history-only context → one genuine/missing observation update → nonmutating exact-horizon forecast → immutable issue → later exact-target scoring. Fitting/scaler estimation must remain outside replay.

Current [development admission](../../configs/dafr_m3b_development_manifest_v1.json) covers only the selected three primaries' first 1,152 bins. It is not executable training permission. A new execution configuration must explicitly allow the approved development fitting task while retaining confirmation=false; no original lock is edited in place.

## Causal bootstrap and shared information

The model is fitted through index 863. Initialize its filtered state through that same index, then preload the common context with the last 23 fit grid events **without calling adapter update on them again**. First new observation is index 864. The first h=1/h=12 decisions target indices 865/876. This avoids both double-assimilation and using a model fitted after its forecast origin.

M3A's fresh mocks start with empty histories; this real-checkpoint bootstrap is new infrastructure to implement and test, not behavior already supported by the mock runner. The planned count utility assumes correct history bootstrap, so any implementation must reproduce those counts before fitting experiments are accepted.

At each validation tick retain M2D/M3A order: reveal; resolve old exact targets; update era/error-support state; update all adapters with identical observed/missing event; snapshot; issue both horizons using the common 24-genuine-bin gate. CPU histories, masks and cutoffs are identical across families; ARIMA's filtered summary and ML feature representations can differ.

No calendar/day-of-week features are planned. The synthetic UTC reference labels are bookkeeping for elapsed Alibaba time, not evidence of actual calendar dates or seasonality.

## ARIMA backend

Use the prespecified nonseasonal SARIMAX candidate representation from the training protocol. After candidate fitting, retain fixed parameters and its filtered—not future-smoothed—state at index 863.

A proposed implementation uses one `extend` step with a single explicitly indexed new observation, or a single NaN for a failed bin. Verify that the backend advances one grid position, skips missing measurement correction and retains exactly identical parameter values. Do not drop rows, refit, forecast-and-assimilate a substitute value, or repeatedly re-filter the entire history during every tick.

For h=1 and h=12, calculate forecasts from the same assimilated state, take the exact final requested step and validate one finite scalar. Hash model parameters and state snapshots before/after forecasting to prove no mutation. Internal future forecast propagation is a temporary calculation, not advancement of the live observation clock.

Before any Alibaba fitting, future backend tests should compare a fixed-parameter synthetic sequential filter with equivalent regular-grid batch filtering, including missing ticks, and check forecast purity, ordering, output shape and failed updates. A fixed-parameter filter test is not parameter training; none was run here.

Official [SARIMAXResults.extend documentation](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAXResults.extend.html) describes filtering consecutive new data without re-filtering the original series. Actual NaN behavior and retained fixed parameters still require installed-backend tests.

## XGBoost backend

Fit two separate direct regressors per candidate/machine on the genuine horizon-specific examples. Use six features at origin-relative offsets 0,1,2,5,11,23 from the common intact window. A missing or incomplete window makes the learned expert unavailable, never a shorter compressed feature row.

Update only the bounded observed/missing input history during replay. Do not call fit, partial_fit, or a scaler fit. Forecast uses a shape-checked row and exactly one finite scalar from the requested horizon's prefit model. The h=12 model never receives CPU observations arriving between origin and target.

Use native model JSON plus feature-order/specification metadata and SHA-256, retaining separate h=1/h=12 model hashes. Scaler provenance is an explicit identity transform, not an unrecorded fitted scaler. Output array shape and backend exceptions must be tested; an unavailable horizon does not invalidate a separately functioning horizon's fixed state.

## Planned LSTM backend

Deferred from the recommended initial pilot. A later approved backend would use the same oldest-to-newest genuine 24×1 window, a genuine-fit-only frozen scaler and stateless inference. Do not carry hidden state across discontinuous supervised windows or pass observed future target CPU into a direct forecast.

Weights, scaler and input specification must be immutable during replay, with horizon-specific artifacts and recorded seeds. TensorFlow installation/import, tiny tensor execution, deterministic inference and actual process-memory checks are prerequisite work for that later scope, not completed here.

## Version, cutoffs and two clocks

Each checkpoint needs:
- Dataset/machine ID, original prefix SHA-256, quality-mask hash, schema/bin-quality version and allowed interval.
- Ordered fit origin/target hashes for each horizon, largest target timestamp actually used in fitting and scaler source interval/hash.
- Expert/model/scaler/feature versions; candidate settings and random seed; dependency/runtime versions; artifact and parameter hashes.
- Training cutoff and filtered-state cutoff; optional scaling cutoff; model availability, hyperparameter-selection cutoff and checkpoint readiness.
- Warning/convergence/root diagnostics, wall-clock build start/end and duration, runtime memory and failures.

Distinguish **source event time** from **wall-clock build time**. Alibaba timestamps are elapsed seconds with an arbitrary UTC reference. In offline replay, each prespecified candidate is constructed before the validation loop and treated as preavailable at its fit cutoff under an explicit prebuilt-checkpoint assumption. Actual build completion timestamps and duration are recorded separately; do not pretend training physically completed in the source's synthetic year 2000 or claim an online fitting latency guarantee.

The winner is selected only after validation ends at index 1151. Its selection/availability metadata must reflect that later knowledge. Do not use the winner's retrospective designation to fabricate an earlier deployed forecast ledger. A subsequent new fit/refit or forward block needs separate authorization and a new artifact/version.

Timestamps and hashes validate declared provenance, not the truth of an arbitrary fitted object's training history. Validate a versioned factory/registry, approved machine/window, expected source and target hashes, backend type, finite arrays and artifact spec before accepting it. Preserve fixed model identity and the M3A state/purity checks.

## Failure and resource policy

A failed fit is logged and cannot be promoted as a complete expert; a complete-policy persistence ledger may still be reported. During replay, numerical forecast failures create logged fallback/abstention using unchanged age-three rules. An update failure quarantines the affected state; no silent skipped-step recovery, automatic refit, or source replacement is planned. Metadata/causality violations abort a run.

Use serial fitting, one machine/candidate at a time, numeric threads at most 1–2 and XGBoost n_jobs=1. Future budget goals remain peak process RSS below 4 GiB and p95 issuance below five seconds; these are limits to measure, not achieved real-model results. Keep private model/checkpoint files and raw traces out of Git, using the existing ignored models/data namespaces.

## Required pre-training acceptance tests

1. Exactly reproduce the planned genuine fit/validation counts and input/target hashes without model fitting.
   Perturb outer-validation values and verify candidate parameter/scaler hashes remain unchanged; this backend test cannot be certified by mask counts alone.
2. Verify source-grid bootstrap and first model-ready origin, including gaps crossing the fit/validation boundary.
3. Verify real ARIMA fixed-state updates through genuine/missing events and both nonmutating forecasts.
4. Verify XGBoost scalar shape/feature order, genuine windows, immutable weights and direct h=12 labels.
5. Retain future-suffix perturbation invariance, exact missing-target outcomes, era/support behavior and no-overwrite tests.
6. Preserve all historical hashes and retain confirmation=false and all old execution locks unchanged.

M3B-1 is ready to support a separately approved ARIMA/XGBoost M3B-2 pilot once these new adapters and execution guards are implemented. It does not itself make the current mock-only engine ready to train or accept real model objects.


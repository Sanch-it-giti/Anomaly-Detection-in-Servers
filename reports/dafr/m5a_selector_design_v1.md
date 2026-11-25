# M5A — Causal adaptive selection: frozen synthetic engineering design v1

31 October 2026. Scope: design, deterministic mock integration and synthetic verification only. No real-data adaptive benchmark or tuned selector is authorized. DAF-R remains an experimental framework without an established novelty or improvement claim.

## Sources and boundaries

Read the original `reports/phase3_dafr_research_design.md` and implementation roadmap; M2C protocol options, M2D missing-event report/configuration, M3A adapter report/contracts, M3B-1 training/validation protocol, M3B-2 completion/validation reporting, and M4A completion report. Prior aggregate evidence motivates the **initial fixed ARIMA incumbent only**. No M4A prediction/outcome ledger is parsed or searched for selector settings. Historical ledgers are opaque bytes during preservation hashing.

The user explicitly approved regression-only reads of previously approved prefix fixtures and preservation hashes, resolving the existing 166-test suite's real-data dependencies. That exception does not authorize any real-data selector execution, new partition access, model fitting or M4A-based tuning. No suffix, calibration/warm-up, final or confirmation period is opened. Existing model artifacts and configurations remain unchanged.

New configuration: `configs/dafr_m5a_synthetic_v1.json`. All real-data execution, training, confirmation, M5B, drift and interval flags are false. The CLI accepts only named built-in synthetic generators, not a CSV path or fitted artifact. Only exact registered deterministic M3A mock specifications for ARIMA and XGBoost are accepted; their names describe lifecycle placeholders, not real fitted algorithms.

## Frozen selector rules — engineering choices, not optimized thresholds

| Item | Frozen choice |
|---|---|
| Clock/horizons | Original five-minute grid; h=1 and h=12 independently |
| Default | Fixed ARIMA, chosen from earlier aggregate development evidence |
| Evidence | Both genuine shadow forecasts issued at the identical origin, horizon, exact target, telemetry era and context digest; genuine target has since arrived |
| Loss | Unweighted mean absolute error, CPU percentage points |
| Capacity/age | At most 288 matched pairs per horizon; target indices in [current−287,current] |
| Minimum | **100 matched pairs per horizon** before any loss-based switch; each pair contains one genuine error from each expert |
| Hysteresis | Challenger loss lower by at least max(0.1 percentage points, 5% of incumbent mean loss), with 1e−12 numerical tolerance |
| Dwell | At least 24 elapsed grid ticks (120 minutes) since initialization, last loss-based switch or telemetry reset |
| Tie | Retain incumbent within 1e−12; fixed expert order ARIMA then XGBoost is the secondary ordering; no randomization |
| Insufficient support | Hold incumbent, even if age expiry reduces a previously adequate buffer |
| Current expert availability | Require both current shadows to be valid for a loss-based switch |
| Unavailable incumbent | Retain incumbent identity; age-three persistence fallback, then abstention; never force an unsupported emergency switch |
| Long-gap reset | Clear active support once at the fourth missing tick; reset incumbent to ARIMA and restart dwell, with a distinct telemetry-default-reset event |

These constants are frozen for this engineering milestone, not selected from M4A errors or claimed optimal. One hundred matched pairs means **100 distinct genuine exact targets per horizon**, 200 shadow errors, not 100 ticks since initialization. Dependence between errors is retained; no effective statistical sample-size claim follows. Earliest possible support on an all-genuine stream with no prehistory is at zero-based tick 123 for h=1 and 134 for h=12: first expert origin 23, first target 24/35, then 100 arrivals.

The original research document proposed exponentially weighted losses and provisional observation-based dwell. This separately versioned M5A design instead uses an auditable bounded unweighted matched window and elapsed-grid dwell, as requested for a lightweight synthetic selector. It does not silently replace the original research protocol or approve these choices for final experiments. Drift-dependent memory, context-conditioned weighting and reliability gating remain deferred. There is no learned gate beyond the preserved genuine-history gate.

## Exact causal event order

1. Validate and reveal one genuine or explicit missing tick. Keep every original position; genuine zero is data, missing is null.
2. Resolve all previously issued shadow, adaptive and persistence forecasts targeting this timestamp. Genuine exact targets create immutable linked losses; missing targets create `target_unavailable` outcomes with null actual/error/coverage. Late targets beyond the supplied stream remain pending. No retroactive revisions/late arrivals are supported.
3. If this is the fourth consecutive missing tick, increment telemetry era once. Clear active matched and policy support; reset incumbents to ARIMA and restart dwell. Keep all forecasts, outcomes and lifetime counters. A later genuine arrival retains the new era.
4. Form matched shadow pairs from just-matured genuine expert outcomes. Log old-era pairs for accounting but exclude them from current-era active support. Age every buffer by exact target time, including missing ticks, and enforce capacity 288.
5. Update both fixed mock adapters once on the identical current context, including missing ticks. Snapshot genuine streak, elapsed input age, context digest, era and each policy's support.
6. When the 24-consecutive-genuine-bin gate permits, generate both experts' immutable shadows for both horizons. Log gated/unavailable/numerical attempts with null predictions. No persistence prediction is mislabeled as a shadow expert prediction.
7. For each horizon separately, choose from past matured matched losses and **current** shadow availability. Record support bounds, mean losses, margin, elapsed dwell, reason and incumbent. Log a distinct expert-switch event only on a loss-based incumbent change.
8. Issue the actual adaptive forecast by linking/copying the selected immutable shadow value. If unavailable, use age-three persistence or explicit stale/no-history abstention. Issue a separate persistence reference. Record configuration SHA, model/mock identity/version and declared cutoffs, exact target and shared context. Do not inspect any future value/mask.

The original M2D/M3A drivers and fixed-policy contracts are not changed. New adaptive contracts are needed because V2 deliberately prohibits an adaptive policy's source expert differing from its policy ID. New immutable records enforce exact target/horizon, causal cutoffs, layer attribution and links to selected shadow centers; V2 target-outcome validation is reused for arithmetic and issue < arrival < outcome ordering.

## Missingness, failure and accounting

All learned-style issuance requires 24 genuinely observed consecutive bins ending at the current origin. Persistence uses only the latest genuine value, age ≤3 elapsed ticks. Gaps are never compressed or imputed. On genuine recovery, persistence is immediately available; learned issuance waits for the full gate.

Shadow expert numerical/unavailable attempts are recorded but never invent a loss. Successfully issued shadows receive a loss only at a genuine exact target. If only one expert issued successfully at that origin/horizon, its individual loss remains auditable but **neither expert gets a matched comparison entry**. This conservative complete-pair approach prevents a selectively available expert from comparing its easier subset against another expert's full history; it does not eliminate informative-missingness bias from the remaining shared subset.

Actual adaptive-policy errors include its actual fallback centers and remain separate from shadow errors. They do not enter expert ranking. Each policy/shadow retains its own bounded current-era support and lifetime genuine-score counts. The shared support minimum of 100 is only scaffolding; no prediction interval, coverage estimator or reliability gate is activated. Missing targets have no interval success/failure outcome.

Forecast-only mock failures are retryable next tick. Failed updates use the preserved M3A invalid-state latch; there is no silent catch-up/refit. Identity/context/version/parameter mutation or forecast-state mutation is a contract violation that aborts replay rather than becoming an apparently normal missing forecast. Model versions stay fixed within each run.

Telemetry resets, adaptive loss-based switches and future drift-detector alerts are separate event types. Returning from persistence to an expert after gate recovery is source recovery, not an incumbent switch. A reset to default ARIMA may change identity but is counted as an era-default restart, not an accuracy-driven switch. No workload/concept drift detector exists.

## Synthetic verification plan and outputs

Built-in fixtures are prespecified mechanical stresses: stable constant CPU (400 ticks), stable→alternating→stable CPU (900), a gentle linear ramp (400) producing different mock horizon rankings, and leading/short/long/trailing gaps with declared forecast failures (600). All use deterministic arithmetic, synthetic UTC dates and registered fixed mock forecasts. They are not Alibaba workload simulations or empirical performance benchmarks.

Tests cover delayed h=12 feedback, exact missing targets, matched evidence, cold start, minimum support, ties, margins/dwell, separate horizons, failure/fallback attribution, old-era accounting, buffer expiry/capacity, immutable forecasts, suffix perturbation, shared contexts, input/type/provenance rejection and no-overwrite. All 166 existing tests must also run using only the separately approved regression fixtures.

Outputs use exclusive versioned `data/processed/dafr/m5a_synthetic_v1/<run_id>/` directories. Each stores the immutable manifest, event ledger, all shadow/policy decisions (including unissued attempts), outcomes, matched pairs, selector snapshots, switches, telemetry resets, summary and completion/failure receipt. Existing or failed IDs cannot be overwritten. Run length is capped at 2,304 ticks; CPU/history/loss working buffers are bounded while this small pilot keeps an audit ledger in memory. A 4 GiB process RSS guard remains in the synthetic runner.

Expected outcomes are engineering assertions, not desired forecasting gains. No parameter is adjusted to produce a favorable synthetic switch count. Final measured counts, tests, preservation hashes and failures are recorded separately in the completion report. M5A stops before any M5B execution.

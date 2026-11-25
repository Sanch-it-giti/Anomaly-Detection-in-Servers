# M2C — Protocol options and missing-event design
Date: 30 October 2026. Status: proposed v2 design only. Original v1 qualification remains unchanged.

## 1. Three options

| Dimension | A — Strict completeness, alternative dataset | B — Gap-aware genuine history (recommended) | C — Bounded causal input imputation |
|---|---|---|---|
| Data rule | Retain all-grid completeness; independently acquire and qualify another source | Preserve all grid slots and original bin-quality mask; learned issuance requires 24 consecutive genuine bins | Preserve grid and mask; carry last genuine input for ≤3 ticks; require 24 defined input slots, ≥18 genuine |
| Leakage risk | Low with chronological splits, independent nomination and source audit | Low if gates use past only, filtering stays causal and exact targets are matched | Higher implementation risk: no backfill, two-sided interpolation, future gap-length decisions or full-series scaler |
| Fairness | Same complete history for all models; still need aligned origins and training budget | Common genuine-window gate and target mask for all learned experts/policies | Same carry limit, windows and target mask; masks/age are shared information, not a hidden advantage for one model |
| Sample sufficiency | Unknown until source is audited; existing Alibaba v1 yields zero eligible machines | 507–566 eligible origins; 477–560 genuine pairs per horizon in development prefixes | 674–832 eligible origins; 628–791 genuine pairs per horizon; not equivalent to independent training samples |
| Drift behavior | No gap-specific behavior, but workload changes remain possible | Missing events produce no CPU or residual updates; recovery can reveal an old change late | Flat carried inputs could hide a change; do not feed them to raw-level/error detectors as genuine measurements |
| Calibration | Standard chronological genuine-error buffers, still dependent data | Real errors only; long gaps leave little or stale support; intervals can be unavailable | Real errors only, stratify input missingness and stale origins; imputation can understate uncertainty |
| Computational cost | New download/storage and licensing audit; not measured | Small masks and fixed-size buffers; future ARIMA missing-state adapter required | Small additional mask/age vectors; more preprocessing/model-interface tests |
| Main limitation | No verified replacement is acquired in this milestone; another dataset may also be short/gappy | Intermittent service and observed-target selection bias; learned models abstain through gaps and history recovery | Imputation assumptions alter the task and can smooth workload changes; does not recover missing truth |

All options keep h=1 = five elapsed minutes and h=12 = sixty elapsed minutes. None may compress gaps. C is not proposed as the default merely because it yields more eligible pairs. Compare B and C only with declared denominators, a common-origin intersection accuracy comparison, and their separate availability measures. The larger C scoreable set cannot establish better accuracy.

## 2. Recommendation and comparison scope

Use B for the initial missing-data pilot, with an explicit persistence fallback and abstention states. It changes the dataset-level completeness requirement while preserving the already audited definition of a genuine bin. It avoids inventing CPU history and makes the loss of forecast service visible.

Retain A if the academic objective requires continuous forecasts across the full timeline. Evaluate C later as a prespecified single-factor ablation, not an unreported replacement for B. No strategy has been experimentally shown superior. The draft numeric gates are justified as minimum pilot opportunity, not model adequacy or statistical power.

Each experimental policy (persistence; fixed ARIMA/XGBoost/LSTM; selection; drift-aware; reliability-only; full DAF-R) must use the same missing-data wrapper. Within B, log separate expert shadow predictions whenever the common genuine-history gate permits them. A model-specific numerical failure must not silently remove that target from its results. Use the prespecified common fallback for that policy and count the failure; report expert-only and complete-policy metrics separately.

## 3. Clock, provenance and partitions

Keep the original 2,304 positions labelled b=300,600,…,691,200 seconds and synthetic UTC reference. Retain fit [0,1152), validation [1152,1612), warm-up [1612,1842), final [1842,2304), indexed by grid positions including missing ones. Never recompute fractions using only observed rows.

M2C reads only the six development first-half prefixes. A future approved development phase may use development validation; confirmation data use remains governed by the original sealed-data authorization and a frozen new manifest. No current permission to open suffixes is created. Existing NAB test outcomes remain exploratory and cannot tune this protocol.

At every grid tick retain: bin label, genuine-observation flag, original quality reasons, last genuine timestamp, elapsed age, eligible-window status, input-only imputation flag/version if C, and processing/arrival time. CPU absence is null, never zero CPU or zero error. C needs both a genuine-value mask and elapsed age from the last genuine value; a copied value remains marked non-genuine.

Future immutable forecast records need the protocol/missingness-policy ID, origin and exact target timestamps, horizon, expert/model version, fit/scaling cutoffs, last genuine input cutoff, gate/fallback status, detector/selector state snapshot, and interval support/cutoff/era. Existing M1 records and files are not rewritten. New missing outcomes require new versioned event contracts, not weakened v1 validation.

Alibaba contains measurement timestamps, not actual delivery-latency logs. Proposed replay assumes a bin becomes available at its right edge, with zero additional delay. A quality-failed bin is finalized missing at that tick. Delayed-arrival semantics cannot be inferred from this source. A future late-data policy would require a new version: process an exact-target genuine arrival only at its real arrival time, never backdate feedback or revise a forecast.

## 4. Mandatory event order at each tick t

1. **Reveal availability.** Advance exactly one five-minute grid step; close [t−300,t). Reveal a genuine CPU mean or an explicit missing event with quality reasons. Append the genuine or missing slot to the chronological history.
2. **Resolve previous targets.** Locate immutable pending predictions by dataset, policy, origin, horizon and exact target t. If the target is genuine, append a linked score event. Otherwise append a target-unavailable event with no residual or coverage outcome. Do not move the target to the next genuine timestamp. Predictions beyond the data boundary stay pending.
3. **Update causal feedback.** Feed only matured genuine-target residuals into policy-specific loss/calibration/coverage buffers. Update CPU-level detectors only from genuine CPU; update persistence-error detectors only from genuine matured baseline errors. During missing ticks, update availability/age state and expire stale support by the declared wall-clock rule, without inserting fabricated feedback.
4. **Update eligibility and issue.** Apply history, reliability, dwell/cooldown and fallback rules using state now available through t. Issue h=1 and h=12 to t+300 and t+3,600 seconds, respectively, without consulting their future target masks. Log point/interval availability and all cutoffs before advancing again.

For example, an h=12 forecast issued at elapsed 6,000 targets exactly 9,600 seconds. A missing 9,600 target produces no error, even if 9,900 is genuine. An observed 9,600 target matures only at that arrival event, never during intervening gaps. Nothing overwrites the original forecast.

## 5. Origin and model-history behavior

**B learned gate:** all last 24 original grid positions genuine, including the current bin. Until then, learned experts are unavailable under the shared comparison gate, even if a particular library can technically forecast with less history.

**Fallback:** issue persistence from the latest genuine mean only when its elapsed age is ≤3 ticks (15 minutes), recording the stale input cutoff. After that, abstain explicitly for that origin/horizon. At a genuine recovery bin the fallback becomes available immediately; learned experts wait for 24 consecutive genuine positions. No negative value, carry forever, or fake ground truth is permitted. Count abstentions and missing target events independently.

ARIMA's future state-space adapter must propagate one transition per grid tick, skip the measurement update on a missing slot and retain fixed parameters during the primary experiment. It may retain pre-gap state; do not squeeze observed values together, run a smoother using future values, or refit merely because a gap occurred. The [official statsmodels missing-data example](https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_sarimax_internet.html) supports investigating this interface; the current project adapter has not been validated for it.

XGBoost and LSTM must consume the same declared causal lag information. Under B, train supervised examples only where required genuine history and genuine training targets exist, with all target timestamps inside the permitted fit block. ARIMA likelihood can use genuine observations on the full regular fit grid, skipping missing measurements; document that its likelihood training set differs from supervised windows. Equal information cutoffs do not imply identical estimators or fitted sample counts.

**C input rule:** at a missing tick use only the last genuine CPU value, and only for its first three subsequent grid slots. This applies even if the eventual gap is longer; no future gap-end knowledge is consulted. Leave leading or older missing inputs undefined. Require all 24 inputs defined and ≥18 genuine slots before learned issuance. Preserve both mask and elapsed-age context. Training/scaling use only permitted past data; fit scaler bounds from genuine fit observations, not filled or future values. Never train on an imputed target. ARIMA must still skip measurement updates for filled slots. If masks/age are additional predictive covariates for ML, either provide a prespecified exogenous equivalent and label it ARIMAX, or explicitly report that information/architecture difference. This unresolved choice must be frozen before C is run.

Training failure or too few actual supervised examples is a separate future feasibility failure; passing prefix gates must not force a model to fit.

## 6. Drift, selection and reliability during gaps

Treat missingness alarms as data-quality events, distinct from workload/concept-drift claims. There is no workload ground truth inside an unobserved gap. Detectors receive no carried CPU, zero residual, or interval “miss” for a missing target. Maintain wall-clock age and genuine update count separately. Never improve an expert's loss score because it had no scored forecasts.

Proposed common recovery convention: after >3 consecutive missing grid slots, start a new telemetry era once, at the fourth missing tick; do not repeatedly reset during the same gap. Preserve old records for audit; mark detector and reliability state cold, suspend statistical drift alarms until their future frozen minimum genuine support is met, and clear active selection/calibration support for the new era. Old forecasts still get their eventual genuine-target scores for overall evaluation, but forecasts issued before the new era do not seed its active calibration/selection buffers. This deliberate conservative reset may reduce interval availability substantially; report it. Apply the same telemetry reset to every ablation, including fixed/persistence policies where applicable, so it cannot be credited as DAF-R drift detection.

Without sufficient new loss feedback, retain the globally development-selected expert when its input gate allows issuance; otherwise use fallback. Subsequent selection needs a frozen minimum feedback support, hysteresis and deterministic tie policy. Dwell/cooldown durations should be expressed in elapsed grid ticks, with switching decisions only at eligible issuance events. Detector warm-up is counted in genuine updates. Exact timer/reset thresholds and interactions with the original drift state machine require approval and future synthetic tests.

Proposed calibration: separate policy/horizon/version-aware buffers of the actual issued center's absolute error; at most 288 matured scores and minimum 100, as in the research design, with an additional proposed **288-grid-tick recency bound** and telemetry-era restriction. Expire scores by target timestamp, never substitute one day of observed samples for one elapsed day. For nominal 90%/95%, use the ceil((n+1)(1−alpha))-th order statistic; if support/rank is inadequate, interval status is unavailable, with null bounds. Do not fill a narrow interval to conceal absent support. Source-policy fallback errors cannot be pooled with unrelated shadow-expert errors.

The recency/era constraints are new draft amendments, not previously frozen settings. Prefix structural pair counts do not prove sufficient support after resets. If 100 recent errors cannot be accumulated, continue points/fallback with unavailable intervals and report that reliability-guided behavior cannot yet be assessed. Do not reduce support retrospectively to improve availability. [Zaffran et al. (2022)](https://proceedings.mlr.press/v162/zaffran22a.html) study adaptive conformal methods for dependent series; neither that work nor ordinary conformal theory establishes coverage for this proposed reset/missingness wrapper.

## 7. Required reporting and failure cases

Report separately for every machine, policy and horizon:

- Genuine/missing grid counts and missing runs; eligible learned origins divided by all grid positions.
- Issued points, fallback forecasts, abstentions and numeric failures; no forecast drop after seeing its target.
- Genuine exact-target score count, missing-target count and boundary-pending count.
- MAE/RMSE on genuine targets; MAPE only on valid nonzero denominators with its exclusion count.
- Matched-origin comparisons across policies and B/C, plus their separate complete-policy availability. Conditional accuracy alone cannot establish continuous-service quality.
- Interval availability, empirical coverage and width on genuine scored targets with available intervals; also show the denominator of all genuine scored targets and unavailable intervals.
- Genuine-input, short-gap, recovery and long-gap strata defined using information available at issue time; drift alarms, switches and resets with elapsed-time and genuine-update denominators.
- Per-era support, reset counts, inference/runtime/peak memory, model failures and any inability to evaluate the planned ablations.

Anticipated failures include informative missingness, apparent drift on recovery, stale or unsupported intervals, over-resetting so calibration never matures, unstable selection with few common losses, unavailable LSTM training windows, and fallback dominating the results. Long gaps must not trigger automatic repeated parameter training; primary evaluation still forbids parameter refits. Original CPU-series dependence, short span and uncertain seasonality remain.

## 8. Approval checklist and next milestone

Freeze the draft thresholds, B gate and fallback, C inclusion and feature parity, zero-delay replay assumption, missing-target event semantics, telemetry-era reset, calibration age/support, detector/selection warm-up/timers, and common reporting masks. Complete authorized value-blind confirmation-prefix structural qualification, preserve nomination order and record any replacements in a new approved manifest. Do not inspect confirmation outcomes or alter historical v1 reports. Require a globally frozen configuration and explicit execution authorization before opening any sealed confirmation data.

Next implementation task, only after approval: a separately versioned **stub/persistence missing-event simulator and tests**, preserving M1 behavior. Test suffix perturbations, leading/trailing/all-missing inputs, gaps of 1/3/4 slots, exact h=12 target absence, 24-slot recovery, input-only C fills, late/boundary event handling, calibration expiry/era provenance, model-specific failures, and no-overwrite/hash preservation. This document does not implement that engine or authorize M3 training.


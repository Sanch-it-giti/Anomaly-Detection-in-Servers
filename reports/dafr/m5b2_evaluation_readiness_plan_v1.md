# M5B-2 evaluation-readiness plan v1 — planning only

6 November 2026. This document does not authorize M5B-2 execution, new observations, research model fitting or confirmation access. All existing locks remain unchanged. The following requirements must be reviewed before a separately scoped real-data adaptive evaluation.

## Engineering evidence versus research readiness

M5B-1 connects the existing real ARIMA/XGBoost backend types to the frozen selector using controlled synthetic checkpoint fixtures. It verifies causal state and feedback mechanics. Synthetic gains, switches or failure recovery do not demonstrate adaptive CPU forecasting improvement, suitable scientific thresholds or final confirmation eligibility. Synthetic fixture checkpoints must never replace historical research checkpoints.

Before any real-data run, approve an execution configuration with exact machines, checkpoint/source fingerprints, version readiness/selection cutoff, permitted reconstruction prefix, first issuance origin, scoring boundary and immutable output namespace. Real checkpoint admission requires a new explicit scope; the current M5B-1 factory deliberately rejects it. Do not weaken source hashes, use mock metadata for a real checkpoint or backdate selection/availability. Verify no duplicate assimilation of fitted observations and preserve existing historical results.

## Can 100 matched losses accumulate during warm-up?

The original eight-day grid has fit [0,1152), development validation [1152,1612), calibration/warm-up **[1612,1842)** and final evaluation [1842,2304). Warm-up therefore has **230 five-minute positions** (19 h 10 min). No current values or masks from warm-up/final/confirmation have been opened for this analysis. The counts below are mathematical upper bounds for hypothetical complete, failure-free streams, not measured support.

| Fresh-selector start condition | Maximum warm-up h=1 matched pairs | Maximum h=12 matched pairs | First possible 100th-pair tick, relative to warm-up start (h=1 / h=12) |
|---|---:|---:|---|
| 23 genuine trailing history positions already available; first origin 0 eligible | 229 | 218 | 100 / 111 |
| No qualifying prehistory; first origin needs 24 genuine bins (index 23) | 206 | 195 | 123 / 134 |

For W ticks, the complete-stream upper bound is W−h when the gate is initially ready, or max(0,W−23−h) without usable prehistory, capped by 288 storage/recency. A matched pair contains two expert errors at one genuine exact target; two shadows do not double the target count. h=12 cannot mature early just because h=1 has scored. The 24-tick dwell does not bypass the 100-pair minimum.

Thus 230 positions can be sufficient in an ideal complete stream, but adequacy is **not guaranteed**. Missing exact targets, 24-bin gate recovery, selective numerical failures and telemetry resets reduce actual common support. Coverage percentage alone does not bound the number of consecutive genuine windows. Active evidence also ages on the grid; absent/newly failed shadows cannot retain an artificially favorable old loss indefinitely.

After a long gap, let R be the relative index of the first genuine recovery tick. The learned gate first reopens at R+23; the first possible 100th matched pair arrives at R+123 (h=1) or R+134 (h=12). With a last warm-up index of 229, this requires recovery no later than R=106 or R=95, respectively, even without any further missingness/failure. Another reset clears support again. These are best-case bounds, not evidence about sealed data.

Prespecify cold-start behavior if support is insufficient at the final boundary: retain ARIMA when available, otherwise persistence/abstention; continue accumulating only genuine delayed exact-target evidence under the frozen rule. Report support/eligibility and when adaptation actually becomes available. Do not reduce 100, compress gaps, impute ground truth, seed support with fitted residuals, or inspect final outcomes to extend warm-up/select an easier start date. A run with little/no supported adaptation may be an informative feasibility failure rather than an adaptive-accuracy experiment.

Any future interval-calibration warm-up is a different requirement: it must collect errors of the actual deployed policy centers, including declared fallback, not substituted expert losses. Having 100 matched shadow pairs does not implement or prove interval calibration. Intervals remain outside this milestone.

## Evidence independence and inspected periods

M3B-2 inner validation [864,1152) selected the model configurations. M4A [1152,1612) was then inspected and discussed. M5A/M5B-1 are synthetic engineering. None of these now-inspected real-data outcomes can be presented as an independent final test of a subsequently designed adaptive selector.

The adaptive protocol and ARIMA-default rationale were developed after M4A was inspected through index 1611. Their logical information-availability cutoff must therefore be at least 1611 for a later historical replay, with prospective issuance starting no earlier than 1612 under separate authorization. Do not reuse the earlier model-candidate selection cutoff 1151 as if the later adaptive design existed then. Distinguish source event time, logical replay information availability and actual wall-clock artifact construction in the manifest.

If separately authorized, replaying M4A with the new selector is retrospective development/engineering analysis only. Do not search it for favorable memory, margins, dwell or startup choices, or relabel its result as confirmation. Any changed settings require a new version, a declared development rationale and later untouched evaluation; the current M5A constants must not silently change.

The untouched later development periods, if separately opened after freezing, could provide chronological forward evidence on the same development machines. That is not independent-machine confirmation and shares cluster/workload dependence. Opening them consumes their untouched status. Predeclare which results are exploratory, forward development and final independent confirmation before execution.

For final confirmation, retain original independent machine roles/reserve order and complete separately authorized V2 structural qualification without using confirmation forecasting outcomes. Original M2B rejected every nominee under strict v1; preserve that finding. Development V2 qualification does not automatically qualify confirmation machines. Require frozen protocol, source/license audit, causal preprocessing, sufficient support, prespecified exclusions/availability metrics and explicit confirmation authorization before any sealed suffix is opened.

## Proposed controlled comparisons and reporting

Use the same checkpoint versions, chronological origins, exact targets and common history/fallback/era wrapper for persistence, fixed ARIMA, fixed XGBoost and the frozen adaptive policy. Preserve expert shadows at every eligible origin even when unselected. No refitting during primary streaming evaluation; specify any future offline fit/reconstruction permission separately.

Report per machine/horizon: common expert-matched MAE/RMSE and counts; complete-policy MAE/RMSE with its own support; genuine/missing bins; eligible origins; expert/fallback/abstention counts; unavailable/pending targets; failures/stale-state cutoffs; active support and reset/default-restart/switch counts; runtime/memory including all shadow inference. Use equal-machine macro means and do not pool different target subsets to claim gains. Preserve runs with insufficient adaptation and unfavorable results.

Synthetic tests provide no significance threshold or improvement hypothesis result. Any statistical comparison, ablation, selector sensitivity analysis or retraining policy needs a separate prespecified design using development evidence and later untouched confirmation. Drift detection, reliability gating, prediction intervals and LSTM remain separate milestones, not implicit features of this two-expert selector.

## Readiness decision and required authorization

Engineering readiness is conditional on the M5B-1 tests, saved-ledger audits and protected hashes passing. Research execution readiness additionally requires an approved data scope, qualified independent evaluation machines, exact real-checkpoint initialization, a frozen global experiment manifest, sufficient chronological evidence or an honest insufficient-support fallback plan, and explicit authorization. No empirical warm-up sufficiency claim can be made without permitted observations, which this milestone does not authorize.

M5B-2 should first review these choices and identify genuinely unexamined, permitted evaluation evidence. **Do not execute M5B-2, open new blocks, train on Alibaba or unlock confirmation from this plan.**

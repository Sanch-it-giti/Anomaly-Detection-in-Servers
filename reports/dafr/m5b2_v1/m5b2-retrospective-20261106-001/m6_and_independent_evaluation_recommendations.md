# RETROSPECTIVE DEVELOPMENT DIAGNOSTIC — recommendations after M5B-2

This document is planning only. M6, M7, M8, new observations and confirmation execution are not authorized by it.

## What the current result supports

The software can replay a frozen adaptive rule causally from complete immutable expert shadows, including exact h=12 feedback, fair matched losses and explicit fallback. The measured adaptive errors equal fixed ARIMA at h=1 and are worse at h=12. The result provides no evidence that adding adaptation improves this project, and no evidence that adding a drift detector will repair it.

Preserve this unfavorable result and retain fixed ARIMA as a strong control. Three switches are not drift ground truth. CPU variation, concept drift, telemetry gaps and model-selection changes are distinct phenomena. Neither these switches nor NAB anomaly annotations should be treated as validated drift labels for forecasting evaluation.

## Recommended separately scoped M6 work

Begin, if separately requested, with detector design and synthetic verification. Prespecify the monitored signal and its units, initialization/warm-up, threshold/normalization, false-alarm accounting, reset behavior and interaction with the unchanged selector. A persistence-error signal can remain independent of which expert is currently selected; otherwise a selection-induced loss change can masquerade as drift. This is a design consideration, not an implemented or validated detector choice.

Use controlled synthetic changes and unchanged/no-change controls to test delay and false alarms. Include gaps and recovery, delayed h=12 feedback, genuine-only updates, long-gap telemetry resets and repeated alarms. Missing telemetry must not become zero CPU, zero residual or a workload-drift alarm. Distinguish genuine-update warm-up from elapsed-time dwell and expire support on the original grid.

Keep fixed persistence, fixed ARIMA, fixed XGBoost and frozen adaptive-only policies as controls with identical origins, target rules, history/fallback/era wrapper and reporting masks. If a later drift-aware policy changes loss memory or other frozen behavior, document it as a separate prespecified ablation/version; do not edit M5A/M5B-2 outcomes. Test failed/unavailable experts and include their fallback/abstention cost. No automatic retraining should be inferred from an alarm.

Do not choose M6 thresholds or declare a success criterion by searching this M4A replay. Engineering reuse of inspected records must remain labeled retrospective. Any future sensitivity study requires declared development data and later untouched assessment, with every attempted setting/cost reported. Intervals/reliability guidance and a dashboard remain separate M7/M8 work.

## Independent evaluation requirements

M3B-2 selected expert settings using [864,1152); M4A [1152,1612) was inspected before the adaptive rule was designed. This replay is therefore not an independent test even though the simulated decisions use only matured past errors. The adaptive design/default cannot be backdated to the earlier model-candidate selection cutoff. Record algorithm availability separately from model training/readiness and actual wall-clock build dates.

Before opening another real period, obtain a separate scope with exact machine IDs, source/checkpoint hashes, permitted reconstruction history, first issuance time, scoring boundary and output namespace. Warm-up [1612,1842), final [1842,2304) and confirmation suffixes remain unopened. Untouched later periods of these same machines could provide prospective-in-time development evidence after freezing, but they are not independent-machine confirmation and share cluster dependence.

For stronger evidence, retain an independently nominated confirmation machine set with preserved roles/reserve order and separately authorized value-blind structural qualification. Original strict-v1 Alibaba rejection remains unchanged; development V2 qualification does not automatically qualify confirmation machines. Freeze global model/selector/detector settings, exclusion rules, support sufficiency behavior and comparison masks before any confirmation forecasting outcomes are inspected, then require explicit confirmation execution authorization.

The 230-tick planned warm-up has ideal upper bounds of 229/218 matched h=1/h=12 targets with genuine prehistory, or 206/195 without it. Actual support is not known for sealed periods and may be inadequate after gaps/failures/resets. This diagnostic's readiness times cannot be assumed to recur. Retain the 100-pair rule: if support is insufficient, report default ARIMA/fallback behavior and inability to evaluate meaningful adaptation rather than reducing the minimum or extending warm-up after looking at final errors.

Report per-machine/horizon matched expert-only and complete-policy MAE/RMSE, own and shared genuine counts, missing/pending/failed outcomes, expert/fallback/abstention availability, support and switch/reset/alert counts, and all model/detector compute. Use equal-machine macro averages, preserve negative results, and do not pool different target subsets to claim gains. Statistical significance/generalization claims require a separate justified design beyond these three correlated short streams.

**Next eligible activity is a separately authorized M6 design/synthetic milestone or independent-evaluation planning. No such work is started here.**

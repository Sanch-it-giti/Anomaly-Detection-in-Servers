# Server Resource Utilization Forecasting Using Time Series Analysis and Machine Learning

## DAF-R extension: chronological two-expert forecasting and monitoring — research report draft

**Evidence status:** engineering and inspected development study. Independent confirmation is not available. Student name/ID, guide, institution, department and submission date remain placeholders. This draft does not claim completion of every original advanced-phase objective.

## Abstract

This project studies short-horizon CPU-utilization forecasting with explicit chronological information boundaries. A proposed DAF-R framework combines fixed-parameter ARIMA and XGBoost experts, a recent-loss selector, persistence-error drift monitoring and policy-specific residual prediction intervals. The implementation preserves missing five-minute grid positions, immutable forecast provenance and delayed exact-target scoring at five and sixty minutes. Alibaba trace acquisition was feasible on an8GB Mac, but every nominated machine failed the original complete-prefix rule. A separately versioned gap-aware pilot admitted three development machines. A retrospective diagnostic on inspected development forecasts found no adaptive improvement over fixed ARIMA: h1 results were identical and h12 error increased. Synthetic drift tests exposed missed changes and repeated alarms; synthetic interval tests exposed substantial undercoverage under growing variation. Real-backend integration verified parity and interval nesting without authorizing new research blocks. Confirmation-machine qualification remains incomplete. The contribution is a reproducible engineering framework and transparent negative findings, not demonstrated algorithmic novelty, independent forecasting superiority or guaranteed uncertainty calibration.

## 1. Problem statement

Server CPU demand varies over time, and delayed capacity preparation can affect resource use and service quality. The forecasting task is to estimate a future CPU value from information genuinely available at the forecast origin. Reactive thresholds and predictive planning are complementary; existing cloud systems can already offer forecasting, so the project does not presume that all prior systems are purely reactive. The research challenge is to compare fixed and adaptive methods fairly when data are missing, feedback arrives after different horizons and uncertainty may fail under changing workloads.

## 2. Objectives and scope

The university project originally proposed EDA, classical ARIMA/conditional SARIMA, XGBoost/LSTM comparisons and a dashboard. The current DAF-R extension focuses on causal simulation, registered ARIMA/XGBoost models, frozen hard selection, an independent persistence-error monitor and90/95 residual intervals. The implemented bank has two trained model families, not LSTM. SARIMA was not justified by established seasonality. A dashboard, CPU-level drift response, reliability-based expert gating and controlled retraining remain unimplemented. Every later result is labelled development, retrospective or synthetic; no independent confirmation result is supplied.

## 3. Literature background

Calheiros et al.[1] motivate ARIMA workload prediction for cloud applications. Hyndman and Khandakar[2] provide background on systematic ARIMA forecasting procedures; their work is not a guarantee that automatic identification solves this project's missingness or state issues. Chen and Guestrin[3] describe XGBoost, whose lag features here must remain causal. Gibbs and Candès[4] and Zaffran et al.[5] motivate studying prediction intervals under distribution shift and time dependence. The present frozen rolling absolute-error buffer is not an implementation of every guarantee or adaptive method in those papers. The original project also reviewed foundational LSTM work, but no trained LSTM result is included. References are reused from previously verified project literature and research-design records, not newly invented or newly claimed re-verifications.

## 4. Dataset selection and challenges

Initial NAB EDA selected `realAWSCloudwatch/ec2_cpu_utilization_5f5533.csv`:4032 observations on a five-minute grid, no missing/duplicate timestamps in the verified EDA. It is an approximately two-week, already inspected series; seasonality and cross-workload generalization were not established. Its historical806-step fixed-origin experiment is distinct from later repeated h1/h12 forecasting and cannot now be called untouched confirmation.

Alibaba2018 machine usage was processed sequentially rather than loading the8.38GiB CSV into memory. The verified archive SHA-256 matched, and M2B reported112.64MiB ingestion-process peak RSS. All15 nominees failed strict complete-prefix qualification:1152 grid positions were present, but not every bin was a valid observed CPU mean. Missing/quality-failed positions must not be treated as genuine zeros. This negative result motivated a separately versioned protocol rather than silent threshold relaxation.

Under frozen V2 development screens, m_505,m_1426,m_3028 were qualified for a development pilot. Their genuine prefix bins were946,920,946; longest genuine runs224,192,382. These development-informed screens do not prove model adequacy or confirmation eligibility. No confirmation machine has full verified V2 qualification: m_1878 and m_3836 fail75% coverage, while seven others lack authorized structural-mask evidence. Shared cluster provenance and an eight-day grid further limit independence and seasonal inference. Source evidence: [dataset selection](../../../synopsis/dataset_selection.md), [M2B](../../m2b_qualification_report_v1.md), [M3B-1](../../m3b1_development_qualification_v1.md).

## 5. Gap-aware methodology

Keep every300-second position, with a genuine value or explicit missing event. Learned issuance requires24 consecutive genuine positions through the origin. Persistence uses the latest genuine value only if at most three ticks old, otherwise the policy abstains. Missing targets are not scored, shifted to the next value or imputed as ground truth. On the fourth consecutive missing tick, one telemetry era begins; active support resets once, not repeatedly during a long gap. Old issued intervals/predictions remain immutable and may score at genuine exact targets, but old-era errors do not populate new active buffers. Late revisions or extra delivery delays are outside the current zero-delay replay assumption.

## 6. Chronological simulator and provenance

At each tick, reveal the current event, score prior exact-target forecasts, update telemetry/support and matured feedback, update fixed model observation states, issue expert shadows, apply the frozen selector and attach causal intervals. No h12 loss enters before its sixty-minute target arrives. Beyond-stream targets remain pending. The ledger records run/dataset/machine identities, exact origin/target/horizon, source/model version, training/scaling/state cutoffs, checkpoint fingerprints, context, availability and later outcome links. New versions and exclusive output directories preserve historical artifacts. Suffix perturbation, no-revision, exact-target and saved-ledger checks establish engineering chronology, not statistical independence.

## 7. ARIMA and XGBoost forecasting

Completed M3B-2 training used[0,864) of each development prefix with common chronological inner validation[864,1152). Across three primaries,27 parameter fits and18 candidate replays selected ARIMA C3=(1,1,1), no trend, and XGBoost C1: depth2,100 trees, learning rate0.05. Selection used equal-machine h1 validation MAE, not AIC or h12 outcome shopping. The ARIMA candidate likelihood convention retained the same grid/burn24 and checked convergence/finite parameters/roots. ARIMA advances fixed filtered state at each tick and skips measurement correction for missing values. XGBoost uses offsets[0,1,2,5,11,23], genuine24-bin gating and separate direct h1/h12 regressors. Identity scaling and registered parameter provenance remain fixed. No refit on all1152 or combined1612 positions is implied by those existing artifacts. See [M3B-2](../../m3b2_v1/m3b2-development-20261030-001/completion_report.md).

## 8. Adaptive selection

M5A freezes independent horizon states, ARIMA initial incumbent,100 minimum matched genuine expert loss pairs,288 maximum pairs and288 elapsed ticks of target recency. A challenger must improve mean absolute loss by max(0.1 CPU points,5%) after24-tick dwell; ties retain the incumbent. Failed/gated incumbents use explicit persistence/abstention, not an undocumented emergency switch. Only matched ARIMA/XGBoost expert errors rank experts; policy fallback errors are separate. The adaptive policy's own actually issued centers determine its forecasting and calibration outcomes.

## 9. Drift detection

M6A implements a one-sided Page–Hinkley-style persistence absolute-error monitor, independent of selected expert. Per era/horizon, the first32 genuine errors freeze a median/MAD scale with floor0.1, multiplier1.4826 and clipping±4. PH delta0.05, warning4/alarm8,64 recent genuine errors,288-tick support and24-tick cooldown are frozen engineering choices. A statistical alarm does not prove concept drift. CPU-level detection, cross-channel watches and alarm-driven selection/retraining are absent. M6B integrates the observer with real backends on generated streams; M7B records support before state updates without changing original drift payloads or point behavior.

## 10. Prediction intervals

For n genuine matured absolute residuals of the same complete policy/version/horizon/current era, the radius is the ceil((n+1)p/100)-th order statistic for p90/95. Minimum100, capacity288 and288 elapsed-target recency are enforced. Bounds are raw center±radius, not clipped; insufficient support leaves null bounds with the center retained. Each policy uses its own actual selected/fallback errors, never a chosen expert's or another policy's buffer. Fixed shadow experts have no fallback interval when unavailable. Coverage is measured only on available intervals at genuinely observed exact targets, with separate availability and width/score reporting. This dependent, drifting policy system has no automatic exchangeability-based conditional or local coverage guarantee.

## 11. Experimental protocol and evidence domains

M4A inspected development origins[1152,1612), three original primaries, with original fitted parameters unchanged. M5B-2 then replayed the frozen selector on those archived outcomes, so it is a **retrospective development diagnostic**, not a new independent test. M6A–M7B uncertainty/drift experiments use deterministic generated streams and, where specified, generated-data real-backend fixtures. Restricted warm-up[1612,1842), final[1842,2304) and sealed confirmation suffixes remain closed.

The [proposed final protocol](proposed_final_evaluation_protocol.md) defines P/F-A/F-X/A comparisons, exact final-origin scoring, cold causal warm-up, own/expert/common-policy masks and equal-machine macro aggregation. It is a frozen review proposal with all execution flags false. Confirmation qualification, adopted per-machine fit scope, real-data typed integration and explicit execution authorization are unresolved go/no-go gates, not results.

## 12. Verified development results

From the preserved M5B-2 report, equal-machine macro expert-matched MAE / RMSE in CPU percentage points:

| Policy | h1 MAE / RMSE | h12 MAE / RMSE |
|---|---|---|
| Persistence |4.125690 /5.424773|7.133119 /9.324500|
| Fixed ARIMA |3.901195 /5.104576|6.797972 /8.788959|
| Fixed XGBoost |4.396641 /5.801670|6.937706 /9.025295|
| Frozen adaptive |3.901195 /5.104576|6.896834 /8.827642|

The common counts are1297 at h1 and1272 at h12 across the three machines. Macro RMSE means the arithmetic mean of three per-machine RMSEs, not pooled RMSE. **Adaptive selection equals fixed ARIMA at h1 and is worse at h12**, with three h12 switches. Expert-matched h12 macro differences are+0.098862 MAE and+0.038683 RMSE. Complete-policy comparisons including actual fallback likewise show no gain: h12 ARIMA6.823330 MAE versus adaptive6.915697, with common1340 targets; h1 values are equal at3.908631 MAE over1373 targets. No significance or generalization follows from this inspected diagnostic. Full machine-level tables and all unfavorable outcomes remain in [M5B-2](../../m5b2_v1/m5b2-retrospective-20261106-001/completion_report.md); these numbers are transcribed existing evidence, not newly computed experiments.

## 13. Synthetic verification results

M6A's11 scenarios produced33 statistical alarms and37 warning entries. There were no statistical false/pre-change alarms under those declared deterministic labels, but four warning entries occurred without a sustained-change label. The abrupt h1 level-step intervention was missed; insufficient support prevented early detection; persistent change produced repeated alarms after cooldown. This is not a real-world false-alarm-rate estimate.

M7A mock growing variation at90% nominal covered57.53% /56.12% at h1/h12. M7B's different generated real-backend growing fixture covered81.08% /68.35%; at95% nominal it covered87.64% /78.06%. The two milestones are different fixtures/backends, not evidence of improvement. All undercoverage is preserved without retuning.

M7B continuous adaptive intervals at90% nominal covered89.97% (319/419 available/genuine matured) at h1 and93.27% (297/408) at h12. Mean issued widths were1.886335 and8.586516 CPU points. In its growing fixture,259/359 and237/348 genuine targets had available intervals, with mean issued widths1.997735 and11.987619. The update-failure fixture had zero all-policy common available-interval targets because fixed ARIMA failed before100 errors; undefined comparisons were not assigned zero coverage.

M7B verified5659 nested90/95 pairs and four independent ledgers, with point forecasts, selection and drift payloads unchanged against controls. Its full409 tests passed in182.178seconds; saved execution took160.846943seconds with695.65625MiB process high-water RSS. These are integration/resource diagnostics, not forecasting latency guarantees or independent reliability evidence. See [M6A](../../m6a_v1/m6a-synthetic-20261107-001/completion_report.md), [M7A](../../m7a_v1/m7a-synthetic-20261107-001/completion_report.md), [M7B](../../m7b_v1/m7b-synthetic-backend-20261107-001/completion_report.md).

## 14. Limitations

The study uses a short selected development sample, shared-cluster data and informative missingness. Overlapping horizons and adjacent samples are dependent. Prefix admission does not guarantee long uninterrupted calibration; frequent telemetry resets may keep intervals unavailable. Persistence-error alarms can miss level changes or react repeatedly, and do not establish underlying concept drift. Rolling intervals can under-cover during growing variation or remain too wide during shrinking variation. Adaptive policy mixtures are not expert-conditional calibration. Existing benchmarks and retrospective thresholds are development evidence; no untouched confirmation supports novelty, superiority or significance. LSTM, full drift/reliability response, complete real-data interval policies and a dashboard remain absent. Process RSS is not whole-system memory; production latency, late revisions and long-running storage are unvalidated.

## 15. Future work

First approve a value-blind, prefix-only confirmation mask check and resolve provenance/training-boundary decisions without opening suffixes. Build a separately verified real-data typed driver, preserving frozen rules and complete-policy calibration, before any authorized warm-up/final run. Require independent machine qualification, global freeze and explicit access approval. Reliability-based selection, CPU-level drift response, ACI, LSTM and controlled retraining would be separate tested ablations, not silent additions. A read-only saved-artifact viewer is optional and cannot substitute for missing scientific evidence.

## 16. Conclusion

The project implements a reproducible chronology-first forecasting and monitoring pilot with two real model families. Its strongest evidence is correct information timing, transparent provenance, tested missingness handling and honest negative findings. Current adaptive selection did not improve the inspected development baseline, and synthetic prediction intervals failed nominal coverage under growing variation. Independent confirmation is not yet defensible. An engineering/development submission can accurately present this outcome; broader efficacy claims must wait for qualified data, accepted protocol and authorized evaluation.

## 17. References and local evidence

Previously verified source records are in the [existing literature review](../../../synopsis/literature_review.md) and [original DAF-R design](../../../phase3_dafr_research_design.md). No new bibliographic verification or invented study is claimed in M8A.

1. Calheiros, R.N., Masoumi, E., Ranjan, R., and Buyya, R.(2015). “Workload Prediction Using ARIMA Model and Its Impact on Cloud Applications’ QoS.” *IEEE Transactions on Cloud Computing*,3(4),449–458. [DOI](https://doi.org/10.1109/TCC.2014.2350475).
2. Hyndman, R.J., and Khandakar, Y.(2008). “Automatic Time Series Forecasting: The forecast Package for R.” *Journal of Statistical Software*,27(3),1–22. [DOI](https://doi.org/10.18637/jss.v027.i03).
3. Chen, T., and Guestrin, C.(2016). “XGBoost: A Scalable Tree Boosting System.” *KDD*,785–794. [DOI](https://doi.org/10.1145/2939672.2939785).
4. Gibbs, I., and Candès, E.(2021). “Adaptive Conformal Inference Under Distribution Shift.” *NeurIPS34*. [Official proceedings](https://proceedings.neurips.cc/paper_files/paper/2021/hash/0d441de75945e5acbc865406fc9a2559-Abstract.html).
5. Zaffran, M., Féron, O., Goude, Y., Josse, J., and Dieuleveut, A.(2022). “Adaptive Conformal Predictions for Time Series.” *ICML, PMLR162*,25834–25866. [Official proceedings](https://proceedings.mlr.press/v162/zaffran22a.html).
6. Dataset/program sources: official [NAB](https://github.com/numenta/NAB) and [Alibaba2018 description](https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2018/trace_2018.md), with release/checksum/terms evidence retained in M2/M2B reports. No redistribution licence beyond recorded terms is inferred.

The [evidence catalog](evidence_catalog.json), [status matrix](project_status_matrix.md), [reproducibility guide](reproducibility_demo_guide.md) and [readiness report](readiness_report.md) link claims to the actual preserved artifacts. Student/institution placeholders and final editorial approval remain outstanding; no independent-results section can be filled with fabricated numbers.

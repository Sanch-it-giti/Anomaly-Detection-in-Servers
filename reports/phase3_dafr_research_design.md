# DAF-R: Research Design and Existing-System Audit

Audit date: 29 October 2026. Status: research design only; no new models fitted, dependencies installed, or evaluation results overwritten during this audit.

## 1. Research status and question

**DAF-R (Drift-Aware and Reliability-Guided Forecasting)** is a proposed experimental framework combining drift monitoring, adaptive forecasting, and uncertainty monitoring. Its components have established antecedents; neither novelty nor performance improvement is established. The research question is whether combining these components improves the accuracy–reliability–cost trade-off on independent CPU-utilization streams compared with well-controlled fixed-model and simpler adaptive baselines.

A change in CPU level or variance is a workload-distribution change. A change in the relationship between past measurements and future CPU usage is concept drift. A univariate alarm alone cannot identify the underlying cause or prove concept drift. NAB anomaly labels are not forecasting targets, evaluation labels, or drift ground truth.

## 2. Audit evidence and findings

The audit read `src/data_preparation.py`, `src/stationarity_diagnostics.py`, `src/classical_models.py`, `src/run_arima_baseline.py`, `src/advanced_preparation.py`, `src/run_xgboost_forecast.py`, both test files, and the existing Phase 2/3 reports. It checked installed package metadata, searched for LSTM sources/checkpoints, recomputed metrics from saved CSVs, and ran the existing tests. No training script was run.

### 2.1 Verified data and fixed-origin forecast comparison

Selected series: NAB `realAWSCloudwatch/ec2_cpu_utilization_5f5533.csv`; 4,032 observations; all consecutive intervals are five minutes. The established split is:

| Partition | Count | First timestamp | Last timestamp |
|---|---:|---|---|
| Training | 3,226 | 2014-02-14 14:27:00 | 2014-02-25 19:12:00 |
| Historical test | 806 | 2014-02-25 19:17:00 | 2014-02-28 14:22:00 |

Both saved forecasts match every expected test timestamp and actual value. Numeric columns are finite. Both are issued conceptually at the last training timestamp and forecast steps 1–806 without using subsequent actuals. The last target is **67 hours 10 minutes after the origin**. This is a long multi-step trajectory from one origin, not 806 independent five-minute-ahead forecasts.

| Audit item | ARIMA | XGBoost |
|---|---|---|
| Selection | Nine `(p,1,q)` candidates, `p,q ∈ {0,1,2}`; training AIC | Three declared configurations; recursive validation MAE |
| Differencing/features | `d=1` from training ADF/KPSS | Lags `(1,2,3,6,12,24)`; up to two hours |
| Internal validation | No common forecast-validation fold | First 2,581 training values fit; last 645 validate |
| Final fitting | All 3,226 training values | All 3,226 training values |
| Forecast path | Statsmodels multi-step forecast | Recursive own-prediction feedback |
| Intervals | Nominal model-based 95% intervals | None |
| Saved MAE | 0.7671155578 | 0.7577892849 |
| Saved RMSE | 0.9763183635 | 1.0600859653 |
| Saved MAPE | 1.9965567413% | 1.9489404752% |

**Conclusion:** the point forecasts are genuinely comparable for the historical fixed-origin task and reproduce the reported metrics. Their training-selection procedures and information summaries differ, so this is not an equal-tuning-budget experiment. Differences in MAE/RMSE do not establish statistical or general superiority. Their uncertainty is not comparable: only ARIMA has intervals, and their empirical coverage was not established by the earlier reports.

### 2.2 Verified corrections and methodological limitations

These findings are recorded here before any future correction. Existing code and historical artifacts remain unchanged.

1. **Incorrect blanket leakage statement in the older protocol.** `reports/phase3_model_comparison_protocol.md` describes feedback of actual test observations into one-step evaluation as leakage. That is only leakage if the observation was unavailable when the forecast was issued. In chronological streaming evaluation, yesterday's observed test value may legitimately inform today's forecast. It would change the task relative to the historical 806-step forecast, so comparisons must use the same origin, horizon, and information availability. This document supersedes that statement for future DAF-R work.
2. **ARIMA AIC comparability defect.** With the installed statsmodels and the existing `enforce_stationarity=False` settings, unfitted candidate construction shows `loglikelihood_burn` values of 2, 3, or 4 depending on order. Thus candidates omit different initial likelihood contributions. This weakens the interpretation of the lowest AIC as a clean like-for-like ranking. It does not invalidate the saved forecasts or prove a different order would win. Future runs should document a common likelihood convention/burn-in, reject failed fits, and select using the same chronological forecast-validation folds as the other models. A corrected experiment must have a new version and output path.
3. **Warnings are hidden.** ARIMA fitting suppresses all warnings and does not check convergence, finite AIC, or root stability. No saved fit/optimizer log is available, so convergence of historical candidates cannot be certified without a separate future run. Suppression is verified; nonconvergence is not established. Unconstrained roots also make future stability checks necessary.
4. **Incomplete input contracts.** `regression_metrics` checks shape and zeros, but not timestamp alignment, emptiness, dimensionality, or finite inputs. Lag helpers cast lag values to integers, accepting fractional values silently; scaler/recursion checks do not reject every NaN/inf input. The default selected data and saved forecasts pass the relevant checks, so no error in their reported metrics was found. Future streaming APIs need explicit contracts rather than silent coercion.
5. **Model-specific selection and horizon mismatch for the new objective.** XGBoost's 645-step validation and both 806-step forecasts are legitimate for the old task, but do not select for short-horizon streaming performance. New model configurations must be selected on common rolling origins and horizons using development data.
6. **No simple forecast reference.** Add persistence and a development-chosen fixed-model baseline in future experiments. A small improvement over ARIMA alone does not demonstrate practical usefulness.
7. **Historical test is already inspected.** Its metrics and trajectory are known. It cannot now support an untouched confirmatory DAF-R claim. Replaying it is allowed only as exploratory engineering with that label.
8. **Seasonality is unestablished.** No seasonal expert is required merely because SARIMA appeared in the synopsis. Residual autocorrelation does not by itself prove seasonality or drift.

### 2.3 Leakage-test coverage

All five existing unit tests passed on the audit date. They check dataset size/cadence, default train/test ordering, a toy past-lag construction, scalar persistence-style recursion, and scaler behavior using a supplied training sequence. The scaler test demonstrates fixed bounds; it cannot prove that callers supplied training-only data. The recursion test uses a scalar-returning callback and does not directly exercise XGBoost's one-element array return or the full script boundary. No test currently enforces streaming event order, delayed multi-horizon labels, calibration provenance, model-version changes, or selector timing.

### 2.4 LSTM and environment status

The active virtual environment is `.venv` on Python 3.11. Audit package metadata reports XGBoost 3.2.0, scikit-learn 1.9.1, and Streamlit 1.66.1 installed. **TensorFlow and Keras are not installed**: both `pip show` and Python module discovery confirm their absence. Their declaration in `requirements.txt` is not evidence of installation. No LSTM source, `.keras` checkpoint, `.h5` checkpoint, or LSTM forecast artifact was found in the project outside downloaded data and environment internals. The earlier download did not yield an installed runtime. No package installation or LSTM training was attempted in this planning task.

## 3. Proposed strictly chronological evaluation

### 3.1 Separate experiment families

- Preserve the existing fixed-origin results as historical artifacts.
- DAF-R's primary task is **h=1**, predicting five minutes ahead at each rolling origin. The prespecified secondary task is **h=12**, predicting one hour ahead. Score horizons separately; do not mix them into the old 806-step metric.
- A forecast issued after seeing observation `y_t` may use observations through `t` and targets `y_(t+h)`. It may use matured errors only for targets whose observations have arrived by `t`.
- All fixed and adaptive methods receive the same observations, origins, horizon definitions, data-quality decisions, and resource budget. A fixed-model policy keeps its model identity fixed; it may still update its history/ARIMA state as new observations arrive. Parameter refitting is a separate controlled factor.

### 3.2 Data partitions for new, uninspected experiments

For each independent series with `N` observations, declare contiguous blocks: initial model-development fit `floor(0.50N)`, development validation `floor(0.20N)`, calibration/policy warm-up `floor(0.10N)`, and the remaining observations for final streaming scoring. At N=4,032 these are 2,016 / 806 / 403 / 807, deliberately a new experiment rather than the historical 80/20 run.

Use rolling origins within the development blocks to choose model hyperparameters, detector thresholds, selector settings, calibration window, and retraining rules. Restrict every development training target to its available prefix, including multi-step targets. Freeze configuration before warm-up and final evaluation. Refit initial experts on the combined fit+development blocks with those frozen choices. Fit their scalers only on that prefix. Warm-up runs the actual deployed policies chronologically to create out-of-sample errors and calibration state. It must not tune configurations. Its observed values may update allowed online state.

The final evaluation suffix permits only prespecified online updates using revealed observations. Global policy design cannot be revised after inspecting that suffix. If revised, label the run exploratory and reserve new series for confirmation. Offline preprocessing cannot use future interpolation, centered rolling statistics, whole-series normalization, or end-of-series regime boundaries. Timestamp checks may reject invalid streams; gap handling must use a predeclared causal rule or exclude the affected origins consistently across all methods.

### 3.3 Exact event order and delayed feedback

At the point just before `y_t` arrives, the ledger contains forecasts for target `t` issued earlier; their centers, intervals, and selection choices are immutable.

1. Reveal `y_t` once. Score all ledger entries targeting `t`, including separate h=1 and h=12 forecasts. These forecasts were generated without `y_t`.
2. Update per-expert loss histories, drift detectors, coverage trackers, and policy-specific calibration buffers using only those matured predictions. A forecast from origin `u` at horizon `h` contributes only when `u+h ≤ t`. Do not score unobserved targets or retrospectively rebuild predictions with current models.
3. Update causal context from the observed prefix through `t`. Apply detector decisions, selector hysteresis, and any permitted completed refit for forecasts issued next. Fit/scale through `t` only; record the exact training cutoff and version. A refit that finishes later becomes available only at its logged completion time.
4. Every available expert forecasts from origin `t` to the same targets. Select or weight experts using state known through `t`, and form intervals from matured calibration scores. Log forecasts before revealing any later observation.
5. Continue. At the stream end, leave targets beyond available data unscored and use the common valid origin set for all compared methods at each horizon.

This is predict-then-observe evaluation: scoring `y_t` precedes any use of it for forecasts of later targets. It is acceptable to update a future decision with `y_t`; it is unacceptable to alter the decision whose target was `y_t`.

## 4. Proposed lightweight architecture

`causal data stream → expert forecasts → selector/weights → system interval → immutable ledger → delayed scoring → drift/reliability updates → next decision`.

The expert bank contains ARIMA, XGBoost, and eventually one small LSTM. Persistence is a required reference/fallback. All experts produce shadow forecasts so their later losses are observable even when not selected. This is full-information expert selection; a bandit is unnecessary for three cheap point-forecast experts. Shadow inference cost counts toward the framework's runtime.

### 4.1 Drift monitoring

**First implementation candidate: Page–Hinkley**, with separate two-sided monitoring of standardized CPU level and one-sided monitoring of worsening absolute error of the persistence reference. This costs only a few running statistics. Use a reference independent of selector identity so switching alone cannot manufacture a drift signal. The exact detector implementation, centering, forgetting, threshold, and reset convention must be versioned; River documents a two-sided implementation [R2].

Fix robust normalization from the initial fit prefix, with a positive scale floor. Monitor clipping frequency if normalizing/clipping detector inputs; do not silently interpret heavy clipping as stability. A CPU-level alarm indicates workload change; a worsening-error alarm indicates forecast difficulty, not proven causal drift. Raw-signal autocorrelation and isolated spikes can produce false alarms. Tune sensitivity only on development/stress streams.

Proposed response: a level alarm opens a 24-observation watch period; a persistence-error alarm during that watch, or a standalone persistence-error alarm, confirms a performance-change event. The event starts a 24-observation selection cooldown and uses a shorter loss-memory setting for subsequent decisions. No refit is automatic in the first experiment. These watch/cooldown lengths are provisional, prespecified settings to resolve on development data. **ADWIN** is a later detector ablation, not a second default detector stacked into an unbounded alarm system [R1, R3]. No detector's published assumptions are assumed to hold for correlated CPU measurements.

### 4.2 Context-aware adaptive selection

Use a small, auditable context: recent CPU mean/volatility, recent slope, and drift-watch state, all computed from trailing observations. No calendar seasonality is assumed. Initially use recent volatility and watch state to select between normal and short loss-memory regimes; slope is logged for analysis rather than used in an untrained complex gate.

Maintain per-expert, per-horizon exponentially weighted absolute errors from issued shadow predictions. Normal-memory half-life proposal: 48 observations; confirmed-change half-life proposal: 12 observations for the next 24 arrivals. Standardize errors by a fixed initial-training scale for cross-series reporting. The adaptive-only baseline uses the normal half-life throughout.

For hard selection, propose a switch only if the challenger's score is at least 5% lower and the incumbent has been active for at least 12 observations. Evaluate these constants on development data before freezing. On a confirmed change, shorten memory for all policies containing drift; do not retrospectively reset only an inconvenient model's history. If insufficient feedback exists, keep the development-selected expert. Use the same deterministic tie rule. The first version uses hard selection to simplify attribution.

Optional later weighting uses normalized `exp(-eta * loss_score)` weights with a floor and a development-fixed temperature. Prediction is a convex combination; prediction intervals must be calibrated around the combined center, not formed by naively averaging expert interval endpoints. Do not claim this custom context/discounting rule inherits a particular regret theorem.

### 4.3 Reliability guidance and prediction intervals

Maintain separate 90% and 95% intervals and monitoring state for each policy and horizon. Start with an absolute-error sliding-buffer calibrator, proposed maximum 288 matured errors and minimum 100. These are initial design values to freeze on development data; 288 is one day of five-minute observations, a storage choice rather than evidence of seasonality.

For `n` prior scores and nominal miscoverage `alpha`, choose the `ceil((n+1)(1-alpha))`-th smallest absolute error and issue `center ± q`. Use a discrete order statistic, not an interpolated sample quantile. If the rank exceeds `n` or support is insufficient, flag the interval as unavailable/unbounded according to the frozen policy and count that outcome; do not silently drop difficult cases. Warm-up exists to reduce such cases.

Each calibrator stores the residual of the **forecast that its own complete policy actually issued**. An adaptive center must be calibrated using its historical adaptive predictions; taking a chosen expert's in-sample residuals, or recomputing old ensemble predictions under new weights, is invalid. Model/horizon/version are logged. Changing a model may make old errors stale; do not silently erase the calibration buffer and then claim full coverage. Report post-change support and interval availability.

Reliability guidance is more than attaching intervals: monitor each expert's own shadow-interval coverage on matured targets. In the full framework, an expert becomes temporarily ineligible when supported trailing coverage is below nominal minus 5 percentage points on at least 100 outcomes. It re-enters after recovery under the same frozen rule; shadow forecasts continue while ineligible. If all experts are ineligible, select the minimum past-loss expert with an explicit degraded-reliability flag. The policy's final interval is still calibrated on its own issued residuals. This heuristic can react slowly or wrongly under dependence; test it by ablation.

**ACI-style calibration** is a later alternative: update `alpha_(next) = alpha_current + gamma * (alpha_nominal - miss)` only after the interval's target is observed [R4, R5]. Gamma, endpoint treatment, and any projection into a safe numeric range must be fixed on development data. Clipping or other modifications can change published guarantees. Neither a rolling conformal-style buffer nor a modified ACI wrapper automatically guarantees conditional, short-window, or finite-sample coverage for this dependent, drifting, switching system. Coverage and width are empirical outcomes to measure. ARIMA's existing Gaussian/model-based intervals are separate references, not already calibrated DAF-R intervals.

Report unbounded intervals, numeric failures, and widths explicitly. Do not hide failures through [0,100] clipping unless the metric's physical bounds are verified and the clipping convention is prespecified for all policies.

### 4.4 Apple Silicon, 8 GB RAM feasibility

Run series and candidate fits serially. Keep at most one live small LSTM, one XGBoost model, and one ARIMA per worker; preferably use one worker. Proposed LSTM: sequence length 24, one layer with 16 units and a dense output; batch 32, at most 30 epochs, chronological early stopping on development data and no shuffling. Choose epoch count in development; final refits cannot use the final stream for early stopping. CPU execution is sufficient for the pilot; no GPU plug-in is required. Availability must first be verified in a separate dependency milestone.

ARIMA updates its filtered state as measurements arrive, with fixed parameters in the primary selection experiment. XGBoost/LSTM use current lag histories with fixed fitted parameters. Freeze scaler parameters with the model version. Weight/selector/detector/calibrator updates use small buffers. Set numeric thread limits to 1–2 and measure actual resident memory and wall time; these are proposed resource controls, not measured feasibility results.

First isolate selection and calibration with **no parameter refits during evaluation**. A later controlled retraining experiment may use trailing 2,016 observations, minimum 576 fresh observations between refits, and at most two refit events per series-day; use the same schedule and window for corresponding baseline variants. Train candidate experts serially, retain old experts until successful replacement, and include validation/scaling provenance. Target <4 GB peak process memory and p95 issuance latency <5 seconds for the pilot; report failures against these goals rather than asserting they are already met. Never block a forecast waiting for a refit that would not have completed in deployment.

## 5. Hypotheses, ablations, and metrics

Every claim is testable and may fail. Select the strongest fixed model using development results, not final-test rankings. Also report all individual fixed experts. Prespecify h=1 as primary, h=12 secondary; handle other comparisons as exploratory.

| Variant | Point-policy behavior | Drift response | Interval/reliability behavior |
|---|---|---|---|
| P | Persistence | None | Common rolling calibration reference |
| F-A/F-X/F-L | Fixed ARIMA/XGBoost/LSTM identity | None | Common rolling calibration reference |
| A | Recent-loss selection with hysteresis | None | Common rolling calibration; no coverage eligibility gate |
| D | Same selector | Frozen detector response | Same rolling calibration; no coverage eligibility gate |
| R | Same as A | None | Rolling calibration plus coverage eligibility gate |
| Full DAF-R | Same as D | Frozen detector response | Rolling calibration plus coverage eligibility gate |

Use matched buffers, inference availability, and initial expert versions in each contrast. A common calibrator across variants allows uncertainty comparisons without giving only the full system intervals. Compare raw ARIMA intervals separately. Full-minus-reliability is D; full-minus-drift is R. ACI versus rolling calibration, weighting versus selection, detector type, and optional retraining are secondary one-factor ablations, not unreported extra tuning dimensions.

- **H1 (adaptation):** A has lower macro-averaged normalized MAE than the development-chosen fixed baseline. Null: no reduction. Report raw MAE and paired differences as well.
- **H2 (drift contribution):** D improves post-change MAE relative to A with no more than 5% relative deterioration on controlled no-change segments. Synthetic change times define windows; for real traces report alarm-aligned error descriptively, not true detection accuracy.
- **H3 (reliability guidance):** Full versus D reduces absolute empirical coverage error at 90%/95% levels while not increasing mean interval score; report if guidance merely widens intervals or damages accuracy. R versus A isolates the same effect without drift.
- **H4 (joint trade-off):** Full versus the prespecified fixed baseline provides a better observed accuracy/coverage/cost trade-off while meeting the measured memory and latency goals. Failure to meet any constraint is reported; no single weighted composite hides it.
- **H5 (stability/cost):** hysteresis/cooldown reduces switches per 100 forecasts versus a development-defined no-hysteresis ablation without more than 5% relative MAE deterioration; optional capped retraining is compared with matched periodic retraining on error and compute.

Point metrics: MAE (primary), RMSE, MAPE only away from zero; use training-scaled error or MASE with a positive training persistence-error denominator for cross-series aggregation. Flag zero-denominator constant streams rather than assigning invented scales. Reliability metrics: overall and rolling empirical coverage, absolute coverage gap, mean/median width, interval availability, and interval score `IS_alpha=(U-L)+(2/alpha)(L-y)1[y<L]+(2/alpha)(y-U)1[y>U]`. Count unbounded intervals as such; do not replace infinite widths with zero.

Operational metrics: alarms/day, switches/100 forecasts, refits/day, total training/inference/calibration time, p50/p95 issuance latency, peak memory, failures/fallbacks, and adaptation delay. Detector precision/false-alarm rate/delay require known synthetic change points; use at most the first alarm in a predefined response window for each change and count extra alarms separately. Real trace alarms have no verified truth labels.

Treat series as the replication units. Report per-series results, macro averages, and paired differences. If sufficient independent machines exist, use machine-cluster bootstrap confidence intervals. For within-series exploratory uncertainty use moving blocks, including overlap at h=12; block length is chosen on development data. Do not treat overlapping horizons or adjacent timestamps as independent samples, or interpret LSTM seeds as independent workloads. If the confirmation set is too small, report descriptive intervals and limited power rather than confident significance claims.

## 6. Independent CPU-series experiment plan

1. **Historical case:** `5f5533` and its inspected suffix remain exploratory. Keep their saved results immutable. They may support debugging, demonstrations, and qualified retrospective replay, never parameter confirmation.
2. **Screened NAB replication:** all ten CPU files in `dataset_selection.md` were already inspected for whole-series statistics and shape. Evaluate the remaining nine individually under frozen settings, with EC2 and RDS distinguished and common-host provenance checked. This broadens workload diversity but is still exploratory; file suffixes do not prove statistical independence. Do not concatenate different machines into a fabricated continuous series. Do not select only files that make DAF-R look good.
3. **External confirmation candidate:** Alibaba's official 2018 trace offers machine CPU usage [R7]. It represents additional machines and a different source, not automatically a longer per-machine history. Before download, verify release-specific access/terms, CPU units, cadence, time field, gaps, machine identifiers, and estimated disk/memory cost. No trace was downloaded for this design and no suitability statistics are claimed.
4. **Reserve without peeking:** inventory eligible machine IDs using schema/metadata and prefix-only quality checks. Deterministically assign disjoint development and confirmation machines before plotting/evaluating suffixes. Target at least six confirmation machines if practical, chosen by stable ID hashing rather than outcome. Separate correlated same-cluster machines in analysis and disclose shared provenance. Exclude duplicates/overlap with development machines and record hashes/time ranges. If access or hardware limits prevent this, find another verifiable CPU source or explicitly limit the study to exploratory NAB evidence.
5. **Freeze manifest and protocol:** record release/commit, terms, selection seed, exclusion criteria, machine IDs, chronological boundaries, model/detector/calibrator settings and artifact hashes before opening confirmation suffix results. Run all eligible confirmation machines, including unfavorable outcomes. No post-test retuning; changes require a new confirmation set.
6. **Controlled stress experiments:** on development streams only, simulate abrupt level, gradual slope, variance, and recurring changes plus no-change/noisy controls, with seeds and change times declared in advance. Keep raw and transformed series distinct; never report injected data as real CPU evidence. No NAB anomaly-label-based drift scoring.

## 7. Failure cases and planned safeguards

| Failure | Observable consequence | Planned control and reporting |
|---|---|---|
| Spike/autocorrelation causes false drift | Excess alarms and short-memory resets | Development stress controls; watch/cooldown; count alarms and false positives where truth exists |
| Gradual/variance change missed | Long recovery or undercoverage | Separate level/error diagnostics; report delay; later ADWIN ablation |
| Unstable model switching | High switch rate and erratic errors | Improvement margin, minimum dwell, deterministic ties, missing-model fallback |
| Selector biases its own drift signal | Switching appears as a new regime | Independent persistence-error reference; log expert/version changes |
| Selection invalidates intervals | Good expert coverage but poor system coverage | Calibrate issued system forecasts; per-policy/per-horizon delayed residuals |
| Intervals widen without usefulness | Nominal coverage with excessive width | Interval score, width, availability and coverage reported jointly |
| Small/stale calibration buffer | Unstable quantiles or uncalibrated post-change intervals | Minimum support, status flag, frozen reset policy; no hindsight residual replacement |
| Excess retraining | Latency, memory pressure, overfitting | No-refit primary study; optional budget, cooldown, serial candidates, measured compute |
| LSTM overfits or cannot load | Unstable errors or absent expert | Small architecture, development early stopping, explicit two-expert pilot label |
| Gap, nonfinite values, unavailable expert | Incorrect lags or fabricated scores | Causal quality gate, common valid-origin rules, logged fallback and denominator |
| Zero CPU or near-constant series | Invalid MAPE/MASE | Metric eligibility rules; retain MAE/RMSE and report omitted metric counts |
| Hidden future data or delayed feedback | Artificially strong results | Timestamped ledger, suffix-perturbation tests, target-maturity checks |
| All experts fail in the same regime | Selection cannot help | Persistence fallback and explicit degraded mode; no assumed ensemble benefit |

## 8. Sources and verification

Sources checked on 29 October 2026. Publication details below were verified against publisher/proceedings pages; documentation is an implementation reference. These sources support component choices, not novelty or efficacy of DAF-R.

- **R1:** Albert Bifet and Ricard Gavaldà (2007), *Learning from Time-Changing Data with Adaptive Windowing*, Proceedings of the SIAM International Conference on Data Mining, pp. 443–448. [Publisher DOI](https://doi.org/10.1137/1.9781611972771.42).
- **R2:** River official documentation, [PageHinkley](https://riverml.xyz/latest/api/drift/PageHinkley/). Documents mean-change monitoring and two-sided support; a warning/watch stage in this proposal is an added policy, not a native Page–Hinkley guarantee.
- **R3:** River official documentation, [ADWIN](https://riverml.xyz/latest/api/drift/ADWIN/). Alternative adaptive-window detector; parameters/assumptions must be verified for any chosen installed version.
- **R4:** Isaac Gibbs and Emmanuel Candès (2021), *Adaptive Conformal Inference Under Distribution Shift*, Advances in Neural Information Processing Systems 34. [Official proceedings](https://proceedings.neurips.cc/paper_files/paper/2021/hash/0d441de75945e5acbc865406fc9a2559-Abstract.html).
- **R5:** Margaux Zaffran, Olivier Féron, Yannig Goude, Julie Josse, and Aymeric Dieuleveut (2022), *Adaptive Conformal Predictions for Time Series*, ICML, PMLR 162, pp. 25834–25866. [Official proceedings](https://proceedings.mlr.press/v162/zaffran22a.html).
- **R6:** Statsmodels official documentation, [state-space methods](https://www.statsmodels.org/stable/statespace) and [SARIMAX](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html). The specific 2–4 observation burn-in finding comes from the installed implementation, not a new fit or a claim inferred only from documentation.
- **R7:** Alibaba official [Cluster Trace Program](https://github.com/alibaba/clusterdata) and [2018 release description](https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2018/trace_2018.md). Candidate source only; release-specific permissions and selected-machine quality remain to be checked.
- **R8:** Project-local primary evidence: `reports/synopsis/dataset_selection.md`, `reports/phase2_stationarity_diagnostics.md`, `reports/phase2_arima_baseline.md`, `reports/phase3_xgboost_plan.md`, the audited code/test files, and the two preserved forecast CSVs. No unverified academic citation is used in this design.

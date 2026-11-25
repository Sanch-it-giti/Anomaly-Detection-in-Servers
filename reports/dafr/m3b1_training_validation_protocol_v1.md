# M3B-1 — Real-model training and validation protocol v1
Status: planned development-only pilot; no training executed. Prepared 30 October 2026.

## Scope and clock

Selected machines: m_505, m_1426, m_3028. Fit separately; do not pool machine traces or tune using the unselected reserves. Use the [new manifest](../../configs/dafr_m3b_development_manifest_v1.json), original genuine-bin statuses and source hashes. No NAB test performance informs these settings.

The authorized prefix has N=1,152 grid positions. Use the nested fold **fit [0,864), validation [864,1152)**. This is inside the original research fit block; it is not the original later validation block. Every row, including missing rows, retains its original five-minute position.

A model is fitted offline only on rows/targets available by index 863 (label 259,200 seconds). Bootstrap the last 23 fit slots into the common input-history context **without assimilating them again into the already fitted ARIMA state**. First replay arrival and issuance origin is index 864. That arrival may legitimately inform later predictions. Earliest permitted validation targets are index 865 for h=1 and index 876 for h=12; the first 1 or 12 validation target positions have no earlier pilot-issued prediction.

Each target is a five-minute CPU-bin mean. At h=12 its bin ends sixty elapsed minutes after the origin.

This start rule prevents a serious boundary leak: an h=12 prediction at origin 852 cannot use a model fitted through index 863. Do not include it merely because its target falls in validation.

## Exact examples

For origin i and h in {1,12}, require all 24 input positions [i−23,i] genuinely observed.

- Supervised fit: genuine exact target i+h with i+h<864. All inputs and the target are inside the inner fit block.
- Validation: i≥864, genuine exact target i+h<1152. Origin eligibility uses only information through i; target masks are used retrospectively to count/score exact targets.
- Missing intermediate future positions between i and i+12 do not invalidate a direct-horizon label if inputs and the exact target are genuine. They are never filled, supplied as future inputs or treated as ground truth.
- Missing exact targets create unavailable events, not errors, zero CPU or shifted targets.
- Keep late targets beyond index 1151 pending. Log fallback and abstention even when no score will mature.

Both direct XGBoost and hypothetical direct LSTM use exactly these supervised origin sets. ARIMA is fitted by regular-grid likelihood, not supervised windows, but uses the identical learned gate and validation origin/target set. Model-specific fitting objectives need not have equal sample counts; information cutoffs, available observations and forecast tasks must match.

## Verified fit observations and per-model sample counts

Every model's inner fit spans 864 grid positions. ARIMA's genuine observation count is distinct from its effective likelihood measurement count after dropping the first 24 **grid positions**, including any missing positions in that burn.

| Machine | Genuine fit CPU observations | ARIMA genuine likelihood updates after burn | Genuine inner-validation CPU observations |
|---|---:|---:|---:|
| m_505 | 663 | 646 | 283 |
| m_1426 | 635 | 626 | 285 |
| m_3028 | 660 | 645 | 286 |
| m_3276 | 617 | 603 | 285 |
| m_1029 | 595 | 589 | 285 |
| m_2104 | 609 | 587 | 287 |

The next table applies to XGBoost's direct training rows and LSTM's potential direct sequences. Validation counts are common to ARIMA, XGBoost and LSTM under successful learned issuance.

| Machine | Supervised fit h=1 | Supervised fit h=12 | Common genuine validation h=1 | Common genuine validation h=12 |
|---|---:|---:|---:|---:|
| m_505 | 329 | 314 | 206 | 204 |
| m_1426 | 303 | 284 | 236 | 224 |
| m_3028 | 243 | 223 | 254 | 242 |
| m_3276 | 273 | 262 | 228 | 216 |
| m_1029 | 314 | 297 | 228 | 216 |
| m_2104 | 297 | 280 | 262 | 251 |

Only the first three rows are selected for fitting/tuning. Reserve counts are qualification/support metadata, not authorization to broaden the model search. These are actual mask-based sample counts, not fabricated training results or independent observations. Actual numerical failures could reduce expert availability; complete-policy results must retain the corresponding fallback/abstention records.

## Candidate fitting and common validation

Prespecify three policy configurations per family. For each machine, fit each ARIMA candidate once and each XGBoost configuration's two direct horizon regressors separately. This is **3 ARIMA + 6 XGBoost fits per primary**, or 27 initial fits over three machines. Three policy candidates per family does not mean equal compute cost; ARIMA shares one fit across horizons.

Each candidate is built only from the inner fit block before its own chronological validation replay. Parameters and scaler bounds remain fixed. Do not early-stop XGBoost or update parameters on validation targets. Preserve a separate immutable candidate ledger, all failures, fit warnings and actual resource costs.

After every candidate's validation run completes, choose one global configuration per family by:
1. Mean of the three per-machine genuine common-gate h=1 validation MAEs (equal machine weights).
2. If MAEs differ by at most 1e-9, lower macro h=1 RMSE.
3. If still tied, the listed candidate order.

h=12 is a prespecified secondary comparison, not a posthoc alternative winner. A candidate whose fit is invalid on any selected primary cannot be promoted as a complete global expert; retain its failed-fit record and complete-policy fallback results. Inference failures remain in whole-policy reporting rather than deleting unfavorable rows.

Selection occurs **after index 1151**. Never backdate the winning hyperparameter decision into its own validation ledger. The saved candidate forecasts were causal because their settings were prespecified. Selecting the best ledger afterward is development tuning, not an untouched estimate of the selected model's future accuracy. No refit on all 1,152 rows or replay of a hindsight-selected winner is authorized in M3B-1.

### ARIMA candidate specification

| Order | Trend |
|---|---|
| (1,0,0) | Constant |
| (0,1,1) | None |
| (1,1,1) | None |

Use statsmodels SARIMAX representation with no seasonal terms, simple_differencing=false, stationarity/invertibility enforcement enabled, approximate diffuse initialization variance 1,000,000 and **loglikelihood_burn=24 for every candidate**. Every candidate retains the same 864 positions, genuine mask and likelihood evaluation window. No seasonal structure or d=1 is assumed solely from the historical NAB analysis.

Optimizer: L-BFGS, maximum 200 iterations, no silent alternative-optimizer retry. Capture all warnings. Reject nonconvergence/ConvergenceWarning, nonfinite parameters/likelihood/AIC, nonpositive estimated variance, or nonempty AR/MA root arrays containing nonfinite roots or roots of modulus ≤1+1e-6. Check AR/MA roots rather than rejecting the deliberately specified integration root. These checks are future execution requirements; no convergence claim exists yet.

AIC is logged as a diagnostic, not the selection criterion. This avoids repeating the historical order-dependent burn-in ranking while keeping future candidate selection on common chronological forecasts. Constructor support for common row count, burn and initialization was checked without fitting.

During validation use one causal fixed-parameter filtering update per genuine/missing tick. A missing observation advances the state and skips its measurement correction. Forecast one and twelve steps from a nonmutating state; do not assimilate forecasts or future actuals into that state. Verify fixed parameter hashes and filter-state cutoff after each update.

### XGBoost candidate specification

| Candidate order | max_depth | n_estimators | learning_rate |
|---|---:|---:|---:|
| 1 | 2 | 100 | 0.05 |
| 2 | 2 | 200 | 0.05 |
| 3 | 3 | 100 | 0.05 |

Use objective reg:squarederror, tree_method=hist, n_jobs=1, seed=42, subsample=1, colsample_bytree=1, min_child_weight=1, reg_lambda=1, reg_alpha=0. No fitted scaling is required. No early stopping on the outer validation block.

Feature offsets relative to origin: **0,1,2,5,11,23**. Offset 0 is current genuine CPU; offset 23 is 115 elapsed minutes earlier. The 24-bin window spans two hours of five-minute bins. The old one-step lag names (1,2,3,6,12,24) describe these offsets only for h=1; do not misapply target-relative names at h=12.

### Direct versus recursive h=12

| Choice | Inputs and fitting | Practical trade-off |
|---|---|---|
| Direct, recommended initial pilot | Separate regressor fitted to genuine y(i+12), with the same origin-relative CPU features | Fewer valid fit labels than h=1; one prediction call, no rollout-state mutation |
| Recursive, later single-factor ablation | Fit h=1 once; generate 12 future values from a local copied history, feeding back only its own predictions | Reuses h=1 samples and weights; 12 inference steps and possible error accumulation |

Recommend direct h=12 for unambiguous targets and small inference cost, **not because it has been shown more accurate**. A future recursive comparison must use the same exact validation origins/targets, fit cutoff and tuning budget, and must never consume intervening observed validation CPU values inside one issued rollout. Generated future path values are not observed targets or repairs of past gaps.

### LSTM decision

Defer LSTM from the initial M3B-2 training recommendation. An optional later exploratory architecture is 24×1 input, one 8-unit LSTM and one linear scalar output, 329 parameters, separate direct h=1/h=12 models, batch 32, Adam learning rate 0.001, MSE, 20 fixed epochs, shuffle=false and stateful=false. No dropout or recurrent dropout is proposed for this minimal baseline.

Fit a per-machine min/max scaler on genuine inner-fit values only; freeze its bounds and hash. Do not clip later values to conceal extrapolation. A constant fitted range makes this scaler/model unavailable. Scaler provenance is shared across horizons but fitted labels remain horizon-specific.

Seeds 42,43,44 are a future sensitivity set, not a search for the most favorable seed. All runs must be reported. Do not choose epochs or perform early stopping with the same outer validation values and then claim that retrospectively chosen weights were available at its earlier origins. Nested fit-only early stopping would require a separately declared fold and fresh sample counts. See the resource assessment.

## Performance and availability reporting

Record h=1/h=12 separately, by machine and macro average. Use CPU percentage-point MAE/RMSE on genuine exact targets. MAPE is optional only with genuine nonzero denominators and its exclusion count; no tiny-denominator substitution. Do not report model accuracy from placeholder predictions.

Report all 288 validation origins, shared learned-eligible origins, expert/fallback/abstention counts, genuine score counts, missing-target events, boundary-pending forecasts, numerical failures and model-state failures. Compare expert accuracy on identical valid origin/target sets and complete-policy accuracy/availability separately. Do not selectively remove failures.

Persistence uses the latest genuine CPU only through age three and the same exact-target rules. Its whole-policy scoreable pairs are:
m_505 **282/271**, m_1426 **284/273**, m_3028 **285/274** for h=1/h=12. On the shared learned gate its target counts equal the model-validation table. All three have 288 potential persistence issuances and zero mask-induced abstentions in this inner validation block; no learned model is thereby guaranteed available.

Model-selection results are development findings. No final-test claim, statistical independence assumption, DAF-R improvement, seasonality, drift ground truth, interval coverage or anomaly-label evaluation follows from this pilot.

## Sources and execution boundary

Official [SARIMAX documentation](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html) supports state-space parameterization and documented differencing/constraint options; [extend documentation](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAXResults.extend.html) describes extending filtering to new chronological data. These references do not certify the unimplemented real adapter or prove forecasting performance.

Original research partitions and all existing execution locks remain unchanged. Real adapter implementation, backend tests and training require a separately approved M3B-2 scope and new execution configuration.


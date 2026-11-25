# M8 research evaluation and submission-readiness plan — no execution

7 November2026. This document is a conservative planning deliverable of M7B. It does not authorize M8, new data reads, model refitting, changed scientific rules, final outcomes or confirmation execution. Existing manifests remain unchanged. DAF-R remains an experimental proposed framework; M5B-2 did not improve on fixed ARIMA and M7A growing-variation intervals substantially under-covered.

## Evidence boundaries and actual model provenance

The original generic50/20/10/20 design was instantiated on the2304-bin Alibaba grid as the following half-open blocks. Source: frozen M2/M3B manifests and previously published milestone reports, not a new observation read.

| Block | Intended original role | What is known now / allowed status |
|---|---|---|
| Development fit[0,1152) | Initial model-development prefix | Inspected/qualified for three primaries. M3B-2 actually fitted[0,864) and selected on nested[864,1152); no automatic refit on all1152 is implied. Those checkpoints remain fixed. |
| Development validation[1152,1612) | Forward development/model-policy assessment | Already inspected in M4A and reused retrospectively by M5B-2. It is exploratory development evidence, not untouched final confirmation or a new tuning opportunity for interval constants. |
| Development calibration/warm-up[1612,1842) | Online out-of-sample policy-specific residual/state initialization after settings freeze | Still restricted and not opened in M7B. It must not select hyperparameters, interval thresholds, source versions, masks or resets. Any future access needs separate explicit scoped authorization. |
| Development final[1842,2304) | Frozen forward scoring on the same development machines | Still restricted and uninspected here. It can later be a prospective held-out **development-machine** evaluation under frozen design, not independent-machine confirmation. All genuine observations may update only prespecified causal state; no outcome-driven global retuning. |
| Confirmation machines | Independent machine replication after qualification and global freeze | Original suffixes remain sealed; full V2 qualification has not been established. No execution authorized. Same-cluster machines are not automatically statistically independent workloads. |

Development primaries m_505,m_1426,m_3028 have approved prefix-only V2 development qualification. Reserves m_3276,m_1029,m_2104 remain reserves in their original order. M2B's zero qualified under strict completeness is preserved. Development admission does not qualify confirmation machines or suffixes. Earlier NAB/whole-series inspections remain exploratory and cannot tune a new confirmatory interval procedure.

## Confirmation qualification is not complete

Existing published M2C metadata provide only the following coverage screen; no new confirmation mask or CPU value was read:

| Nominee | Genuine prefix bins /1152 | Coverage | Current verdict |
|---|---:|---:|---|
| m_295 |891|77.34%|Coverage screen only; remaining V2 screens unknown|
| m_66 |926|80.38%|Coverage screen only; remaining V2 screens unknown|
| m_1878 |815|70.75%|Fails75% coverage|
| m_197 |919|79.77%|Coverage screen only; remaining V2 screens unknown|
| m_3836 |812|70.49%|Fails75% coverage|
| m_1022 |935|81.16%|Coverage screen only; remaining V2 screens unknown|
| m_1194 |912|79.17%|Coverage screen only; remaining V2 screens unknown|
| m_1059 |915|79.43%|Coverage screen only; remaining V2 screens unknown|
| m_2502 |872|75.69%|Coverage screen only; remaining V2 screens unknown|

Therefore **zero confirmation machines have verified full gap-aware qualification**, not seven qualified machines. Two already fail a necessary coverage gate; seven have unknown contiguous-run, learned-origin and exact-target-pair criteria. No fresh confirmation-prefix inspection is authorized by this milestone.

A separately authorized **value-blind prefix-mask qualification** must retain the exact five-minute1152-position prefix and original per-bin quality rules, require at least500 genuine bins,75% coverage, longest genuine run48,24-genuine-input origin fraction40%, and at least400 genuine exact-target pairs separately h1/h12. Preserve original roles, primary/reserve order, exclusions, provenance and documented reasons; never select suffixes/results or shorten a favorable window. Target at least six fully qualified confirmation machines as originally planned. If too few qualify, stop and independently nominate more machines or another source under a new frozen plan; do not silently lower gates. Qualification alone does not authorize suffix decryption or evaluation.

## Decisions required before any evaluation request

The M7B factory and forecast schema deliberately admit synthetic registries/machines only. A real-data execution driver, typed records and canonical block/machine allowlist require a separate implementation/verification authorization before any M8 data run. Do not make M8 work by disabling these admission guards or changing a synthetic manifest's scope string.

1. Freeze and review the complete expert registry, parameter/scaler hashes, actual fit cutoffs, model availability, training history reconstruction and replay start. Current historical artifacts use fit864, not an assumed fit1152 or combined1612 refit. Any alternative training scope is a new separately approved experiment, not M8 bookkeeping.
2. Freeze precise policy identities and what fixed expert versus complete expert-with-fallback means. M7B intervals for fixed shadows do not pretend to include fallback. Evaluate persistence, fixed ARIMA, fixed XGBoost and adaptive consistently on expert-only and complete-policy scopes if both are explicitly implemented. Do not relabel a shadow as a full fallback policy after outcomes.
3. Preserve M5A selection, M6A reference and M7A interval settings unless a separate scientific version is authorized before final outcomes. Full DAF-R reliability-based selection, CPU-level drift, drift-triggered switching/retraining, ACI and LSTM are **not implemented by M7B**; either scope the submission honestly to the tested two-expert adaptive/monitoring framework or separately develop/verify these components. Do not call monitoring-only architecture a demonstrated full DAF-R benefit.
4. Specify warm-up entry: causal reconstruction through the prior allowed prefix with the same fixed checkpoint metadata and no forbidden fitting. Declare whether pre-warm-up calibration is empty or imported from an authorized preceding frozen-policy replay. Default recommendation: empty policy calibration at1612; reconstruct required24-bin history and fixed ARIMA state causally from already authorized observations. No retrospective recomputation of earlier adaptive centers/errors under a later policy. Any import must have a separate provenance rule frozen before outcomes.
5. Warm-up observations at origins[1612,1842) may initialize only approved causal state. At final entry1842, preserve legitimate pending warm-up forecasts and state under the same policy, but report scoring-origin scope explicitly. Recommend final metric predictions issued at origins[1842,2304) with exact targets inside the final block. Genuine arrivals at1842 from warm-up origins may update buffers but are excluded from final-origin metrics; targets beyond2303 remain pending. Preserve telemetry eras across the boundary rather than resetting inconvenient support.
6. h1/h12 and policy-specific calibration minimum100 may not be attained within230 warm-up ticks when gaps/resets/learned gates intervene. Report unavailable intervals rather than lower support or pool experts. Freeze window-expiry, own-fallback policy attribution, raw endpoints, model-version rejection and old-era exclusion. Record any post-change failure honestly.
7. Freeze primary h1/secondary h12 metrics, per-machine and equal-machine macro aggregation, own-availability and common genuine-available masks. Report MAE/RMSE, coverage90/95, count/coverage gap, width, interval score, support, fallback/abstention, missing/pending, failure/switch/alarm counts and runtime/RSS. Common available-target comparisons must accompany each policy's own availability; small/highly overlapping samples are not independent observations.
8. Finish confirmation qualification, declare source hashes and schema/units, freeze machine order and all global settings, then request explicit execution authorization. Keep confirmation_execution_allowed=false until approval is concrete. Independent confirmation should run every eligible prespecified machine including unfavorable outcomes. No retuning after results; revisions need a new untouched confirmation set.

## Minimum defensible submission outputs

- Clear project scope and milestone/evidence map separating historical NAB results, Alibaba development fitting, M4A, retrospective M5B-2, synthetic drift/interval tests and any later authorized held-out results.
- Reproducible environment/version list, commands, source/model/configuration hashes, data source/license notes, qualification/partition manifests, deterministic seeds and no-overwrite ledgers. Restricted data/keys stay out of Git; a run can fail gracefully if local data are absent.
- Per-machine/horizon point-error and uncertainty tables with genuine counts and availability; fixed/adaptive/persistence controls on matched targets; negative findings, model failures and exclusions retained. No invented LSTM, dashboard, novelty, independence, formal coverage or full-framework claims.
- Figures derived only from permitted saved artifacts: chronological workflow/partition diagram, representative synthetic interval bands, coverage versus nominal, width versus availability, support/reset examples and existing preserved point-model comparison plots. New slides/plots need a separately scoped request if not already authorized; this milestone only plans them.
- Limitations: short/missing traces, shared cluster provenance, selected development machines, uncertain seasonality, highly overlapping h12 losses, detector misses/repeated alarms, interval undercoverage/nonstationarity, policy mixtures, cold-start support, unqualified confirmation and8GB resource constraints.
- Final report/presentation narrative that treats unfavorable results as valid research evidence, distinguishes empirical diagnostics from guarantees and explains what remains unimplemented. If confirmation qualification/access cannot be completed, submit an explicitly engineering/development study instead of claiming independent validation.

Readiness verdict: conditional engineering readiness only. M8 has not started; no research calibration/final/confirmation values were inspected for this plan. A future request should first approve the remaining protocol/qualification decisions, then name exactly which block may be opened. Do not merge those permissions into a general continuation instruction.

# M2C — Missing-data feasibility, prefix-only
Date: 30 October 2026. Status: design assessment, not an approved qualification or forecasting experiment.

## Decision and evidence boundary

Recommend **Option B: gap-aware chronological evaluation with genuine inputs and targets**, conditional on approving a separately versioned protocol and testing its missing-event semantics. Use bounded causal imputation only as an explicitly separate Option C ablation. If intermittent forecast availability is unacceptable, retain the strict rule and seek an independently qualified alternative dataset (Option A).

M2B remains a completed negative result: **all 15 nominees failed v1; zero qualified machines**. This report does not change that outcome. No model was fitted, forecast produced, detector implemented, suffix opened, or reserve promoted. The draft protocol is not executable authorization for M3 or confirmation.

New analysis read only the six development CSVs under:
`data/processed/dafr/m2b_v1/qualification_20261030_001/five_minute_prefix/`.
Only the already published M2B prefix-quality metadata was consulted for the nine confirmation nominees. Neither readable development suffixes nor encrypted confirmation suffixes were analyzed. No archive or encrypted payload needed to be reopened.

Primary local sources: [research design](../phase3_dafr_research_design.md), [roadmap](../phase3_dafr_implementation_roadmap.md), [M2 manifest](../../configs/dafr_experiment_manifest_v1.json), [M2B manifest](../../configs/dafr_experiment_manifest_m2b_v1.json), [qualification report](m2b_qualification_report_v1.md), [independent prefix validation](m2b_prefix_validation_v1.json), and [ingestion implementation](../../src/dafr/alibaba_ingestion.py).

## 1. What counts as observed

Every development prefix has **1,152 grid positions**, right-edge labels 300 through 345,600 elapsed seconds. A bin labelled b summarizes [b−300,b); its timestamp is a synthetic UTC reference, not the original calendar date. The original eight-day grid has 2,304 positions.

An observed bin means the existing M2B export marks it valid and contains a finite CPU mean in [0,100]. Original quality rules remain unchanged: at least 24 valid unique raw samples, no conflicting duplicate CPU records, and internal/leading/trailing gaps at most 30 seconds. A failed bin remains unobserved even when it contains partial raw measurements. “Missing bins” below therefore include quality-rejected partial bins; they do not assert complete telemetry absence throughout every such five-minute interval. No lower-quality CPU mean was recovered.

The analysis checked exact five-minute order, 1,152 rows, value/status consistency, and finite observed values. A missing run is a maximal consecutive sequence of failed grid positions, including prefix boundaries. A genuine-history run is the analogous sequence of valid positions. Durations below are bin counts multiplied by five minutes.

## 2. Development-prefix coverage and contiguous history

| Machine | Genuine bins | Missing bins | Observed coverage | Missing runs | Longest missing run | Longest genuine run (bins) | Genuine runs ≥24 bins |
|---|---:|---:|---:|---:|---:|---:|---:|
| m_505 | 946 | 206 | 82.12% | 38 | 68 (340 min) | 224 | 7 |
| m_1426 | 920 | 232 | 79.86% | 37 | 74 (370 min) | 192 | 6 |
| m_3028 | 946 | 206 | 82.12% | 32 | 67 (335 min) | 382 | 11 |
| m_3276 | 902 | 250 | 78.30% | 37 | 64 (320 min) | 305 | 5 |
| m_1029 | 880 | 272 | 76.39% | 39 | 75 (375 min) | 454 | 4 |
| m_2104 | 896 | 256 | 77.78% | 33 | 67 (335 min) | 275 | 6 |

Coverage is **76.39–82.12%**. Maximum missing runs span **320–375 minutes**; longest genuine runs span **960–2,270 minutes**. Thus the data contain usable segments, but not four uninterrupted days per machine. Neither reliable seasonality nor sufficient LSTM training data has been established.

| Machine | Gaps of 1 bin | 2–3 | 4–12 | 13–36 | ≥37 | Median gap (bins) | P95 gap (nearest rank, bins) | Leading / trailing missing bins |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| m_505 | 18 | 12 | 4 | 3 | 1 | 2 | 27 | 5 / 0 |
| m_1426 | 13 | 11 | 9 | 3 | 1 | 2 | 19 | 8 / 0 |
| m_3028 | 18 | 4 | 5 | 4 | 1 | 1 | 28 | 0 / 0 |
| m_3276 | 18 | 7 | 6 | 5 | 1 | 2 | 34 | 2 / 0 |
| m_1029 | 12 | 8 | 14 | 4 | 1 | 3 | 18 | 18 / 0 |
| m_2104 | 19 | 4 | 4 | 4 | 2 | 1 | 49 | 0 / 0 |

P95 uses the ceil(0.95 × number_of_runs)-th sorted run length. Counts include boundary runs; their true duration outside the prefix is unknown. Existing completely empty-bin counts are 146, 168, 164, 186, 206, and 207 respectively. The remaining 60, 64, 42, 64, 66, and 49 failed bins contain insufficient-quality partial measurements. These are not additional genuine targets.

## 3. Structural comparison without forecasts

For each zero-based origin i, B permits learned-model issuance only when i≥23 and all 24 positions [i−23,i] are genuine. C hypothetically carries the last genuine input for at most three elapsed grid ticks, leaves leading gaps undefined, and requires a 24-position defined input window with at least 18 genuine positions. These gates use only history through i. C analysis calculated input-availability masks; it did not generate imputed CPU values.

After applying a past-only gate, count potential scoreable pairs only if i+h<1,152 and the exact target is genuine. Looking at a target mask here is a retrospective feasibility count, never an issuance rule. No predictions, residuals, trained samples, or held-out accuracy were calculated.

| Machine | B eligible origins / all grid positions | B genuine pairs h=1 / h=12 | C eligible origins | C genuine pairs h=1 / h=12 | C input-only fill slots / still undefined |
|---|---:|---:|---:|---:|---:|
| m_505 | 543 (47.1%) | 536 / 529 | 832 | 791 / 745 | 67 / 139 |
| m_1426 | 546 (47.4%) | 540 / 520 | 763 | 726 / 692 | 73 / 159 |
| m_3028 | 509 (44.2%) | 498 / 477 | 791 | 755 / 705 | 56 / 150 |
| m_3276 | 507 (44.0%) | 502 / 490 | 721 | 692 / 668 | 68 / 182 |
| m_1029 | 547 (47.5%) | 543 / 525 | 674 | 650 / 628 | 84 / 188 |
| m_2104 | 566 (49.1%) | 560 / 543 | 740 | 708 / 678 | 59 / 197 |

B permits learned issuance at **44.0–49.1%** of all prefix positions and offers **477–560** potential genuine-target pairs per machine/horizon. C increases structural availability but changes the input assumptions. Counting all 1,152 positions in the denominator includes initial history-building positions. Origins targeting beyond the prefix are not counted as scoreable; they are not failed forecasts.

These counts include the initial fit block and **are not out-of-sample evaluation counts**. They demonstrate structural opportunity only. An actual chronological pilot has fewer usable training/validation/calibration samples. For B, potential target pairs in the final 288 prefix grid ticks range from 207 to 263; this does not prove that any future warm-up supplies 100 matured out-of-sample residuals. The actual validation, warm-up and final blocks remain unexamined. No inferential power or interval coverage claim follows from these counts.

Reproduction: take the status mask from each hashed CSV; count false/true runs; apply the two past-only gates above at each original grid index; for h in {1,12}, count genuine exact targets inside the permitted prefix. Input SHA-256 values, numeric aggregates, origin counts, beyond-boundary counts and method identifiers are retained in the draft JSON. This bounded scan needs only a 1,152-slot mask per machine; it does not revisit the 8.38 GiB CSV.

## 4. Proposed eligibility and verdict for all nominees

The following are **new draft design screens**, chosen for structural feasibility on development evidence, not tuned against forecast errors or confirmation outcomes. They are not original M2 rules, validated optimal thresholds, or guarantees of successful training:

1. Keep all original schema, duplicate, timestamp, CPU-range and per-bin validity rules.
2. In the fixed first-half prefix, require ≥500 genuine bins and ≥75% genuine coverage (≥864/1,152).
3. Require a longest genuine run ≥48 bins (four hours), and ≥40% B-eligible learned origins across the full grid.
4. Require ≥400 potential genuine-target pairs separately for h=1 and h=12 under B. This is a prefix availability screen; forecasting decisions must never use future target availability.
5. Maintain original roles and reserve order. Qualify only from authorized prefix checks. Failures are recorded; no shortening to a favorable segment, role reassignment, suffix-based selection or automatic replacement.

**All six development nominees meet these draft numeric screens**, with actual evidence shown above. They are provisionally feasible for a missing-data pilot, not qualified under an approved v2 manifest. Three primaries remain m_505, m_1426 and m_3028; reserves remain m_3276, m_1029 and m_2104. None has been promoted.

For confirmation nominees, the following numbers are copied from existing M2B prefix metadata, not newly inspected observations:

| Machine | Genuine prefix bins | Missing bins | Observed coverage | Draft assessment |
|---|---:|---:|---:|---|
| m_295 | 891 | 261 | 77.34% | Aggregate coverage gate only; remaining checks unknown |
| m_66 | 926 | 226 | 80.38% | Aggregate coverage gate only; remaining checks unknown |
| m_1878 | 815 | 337 | 70.75% | Below proposed coverage gate |
| m_197 | 919 | 233 | 79.77% | Aggregate coverage gate only; remaining checks unknown |
| m_3836 | 812 | 340 | 70.49% | Below proposed coverage gate |
| m_1022 | 935 | 217 | 81.16% | Aggregate coverage gate only; remaining checks unknown |
| m_1194 | 912 | 240 | 79.17% | Aggregate coverage gate only; remaining checks unknown |
| m_1059 | 915 | 237 | 79.43% | Aggregate coverage gate only; remaining checks unknown |
| m_2502 | 872 | 280 | 75.69% | Aggregate coverage gate only; remaining checks unknown |

m_1878 and m_3836 would fail the proposed 75% gate. The other seven pass that aggregate gate but have no newly authorized contiguous-run/origin-pair assessment here; **none of the nine is declared v2 eligible**. Preserve original primary/reserve order. A later authorized, value-blind check of confirmation prefix masks could establish the missing structural criteria without opening suffixes. Full research still aims for three development and at least six qualified confirmation machines. If insufficient machines qualify, acquire additional independently nominated machines or an alternative source under a new frozen selection plan; do not lower thresholds to admit them.

## 5. Feasibility limits and approval conditions

An 8 GiB Mac can readily handle these short masks and bounded histories. M2B previously measured 112.64 MiB process peak RSS for ingestion; that is not an M2C benchmark or evidence of affordable LSTM fitting. No new acquisition, dependency, model-memory measurement or training was needed. Streaming state should stay O(history + pending horizons + bounded score buffers), one machine at a time. Model latency and RAM still require future measurement.

Missingness may be related to workload or collection behavior; its cause is unknown. Scoring only observed targets estimates performance conditional on telemetry availability, potentially excluding difficult periods. Long gaps hide real changes, suppress feedback, age calibration, and can make drift alarms fire only on recovery. Machines share a cluster; they are not proven independent replications. Eight days and fewer usable examples limit generalization and complex models. Research/study access does not establish permission to redistribute raw traces.

Before approval: freeze B versus C, eligibility thresholds, shared lag information, fallback age, missing-event/arrival policy, long-gap reset and calibration aging, model fit windows, exact training-example construction, selector/detector timers, reporting denominators, and same-role replacement decisions. Archive an approved v2 manifest and new output namespace; keep all v1 outcomes intact. See [protocol options](m2c_protocol_options.md) and [draft](../../configs/dafr_missing_data_protocol_v2_draft.json).

## 6. Verification

- `.venv/bin/python -m unittest discover -s tests -v`: **53 tests passed**, 1.011 seconds reported by unittest. These are the existing ingestion, chronology, preprocessing and regression tests; no new missing-data engine is claimed to be tested.
- A separate standard-library recount independently verified six development masks, gap-run totals/histograms/P95, contiguous history, B/C origin gates and exact-target pair counts. JSON draft safety flags, unchanged original confirmation locks, and zero approved v2 IDs passed validation.
- **All 66 protected baseline SHA-256 values matched after the work and tests**, including tracked M1/M2/M2B code/configuration/reports, seven saved M1 artifacts, three historical processed/forecast CSVs, and the original M2B qualification/seal receipts. All six permitted development-prefix input hashes also matched. The complete protected-file inventory and input hashes are in the draft JSON.
- No suffix values, encrypted payloads, vault keys or raw archive were opened by the new prefix analysis or integrity check. Ciphertext payloads were not rehashed; preservation checks cover their existing seal receipt, not a new decryption or payload-content audit.
- Only the three requested M2C documents/configuration files were added. No original source, qualification result, historical prediction or manifest was edited. No model training, dependency installation or forecasting engine implementation occurred.

## 7. Sources and interpretation

- Alibaba official [Cluster Trace 2018 documentation](https://github.com/alibaba/clusterdata/tree/master/cluster-trace-v2018), with pinned source provenance and terms already recorded in M2 evidence. No source-term change was inferred here.
- [statsmodels, “SARIMAX: Model selection, missing data”](https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_sarimax_internet.html) documents state-space handling of missing values. This supports a future adapter feasibility check, not a claim that our existing ARIMA script handles gaps.
- Margaux Zaffran, Olivier Feron, Yannig Goude, Julie Josse and Aymeric Dieuleveut (2022), [“Adaptive Conformal Predictions for Time Series,” ICML, PMLR 162:25834–25866](https://proceedings.mlr.press/v162/zaffran22a.html). Dependence and adaptive calibration require care; this paper does not validate our proposed missingness policy or supply a DAF-R coverage guarantee.

The two methodological sources were checked on their official publication/documentation pages. Quantitative results in this report come exclusively from local prefix evidence, not these references. DAF-R remains a proposed experimental framework without demonstrated improvement.


# M3B-1 — Development-data qualification v1
Completed 30 October 2026. Data admission and planning only; no model training.

## Decision

**Qualify the original development primaries m_505, m_1426 and m_3028 for the prefix-only V2 development pilot.** Each passes every frozen V2 screen. Reserves m_3276, m_1029 and m_2104 also pass the screens but remain unselected reserves in their original order. No roles changed and no replacement was needed.

This is new development-only admission under the user's M3B-1 request. It does not alter the original M2B finding: **all 15 nominees failed strict v1 completeness, with zero v1-qualified machines**. Nor does it qualify confirmation machines, the entire eight-day trace, a model implementation or an eventual final experiment.

The new [development manifest](../../configs/dafr_m3b_development_manifest_v1.json) records these admissions. Existing M2/M2B/M2C/M2D manifests remain unchanged; the frozen M2D configuration's original approved-machine list remains empty because that historical artifact is not rewritten.

## Authorized sources and validation method

Only the six canonical files under:
`data/processed/dafr/m2b_v1/qualification_20261030_001/five_minute_prefix/`
were read. Their SHA-256 values match M2C's source evidence.

[Read-only qualification code](../../src/dafr/development_qualification_v1.py) enforces an explicit six-machine allowlist and canonical paths, rejects symlink redirection, verifies checksums, schema and exact row count, and checks each timestamp against its fixed five-minute bin label. Genuine CPU must be finite in [0,100], including genuine zero; failed bins must have null CPU and explicit original reasons. Valid bins cannot have failure reasons. Duplicates, reordered or compressed rows, non-UTC timestamps and malformed quality metadata fail validation.

Each prefix retains all **1,152 positions**, labels 300 through 345,600 elapsed seconds, covering raw [0,345600). Labels are synthetic UTC relative to 2000-01-01, not original calendar dates. The authoritative per-bin status still comes from the hash-verified M2B pipeline: at least 24 valid raw samples with the original duplicate and 30-second gap/edge rules. This step does not rerun the raw resampler or lower its quality threshold.

No development suffix, original later validation block, confirmation observations/suffix, encrypted payload/key or raw archive was opened. CPU distributions, trends and forecasting outcomes were not examined. Newly calculated evidence consists of quality-mask counts and chronological example availability only.

## Frozen screens and verified results

Required across the entire fixed prefix: at least 500 genuine bins, 75% genuine coverage, a 48-bin longest genuine run, learned-origin availability at least 40%, and at least 400 genuine exact-target pairs separately for h=1 and h=12. Learned origin eligibility requires the last 24 original grid positions genuine. A potential pair additionally requires a genuine exact target inside the prefix.

| Machine | Original nomination | Genuine bins | Coverage | Longest genuine run | Eligible origin fraction | Prefix pairs h=1 / h=12 | All screens |
|---|---|---:|---:|---:|---:|---:|---|
| m_505 | primary | 946 | 82.12% | 224 | 47.14% | 536 / 529 | Pass |
| m_1426 | primary | 920 | 79.86% | 192 | 47.40% | 540 / 520 | Pass |
| m_3028 | primary | 946 | 82.12% | 382 | 44.18% | 498 / 477 | Pass |
| m_3276 | reserve | 902 | 78.30% | 305 | 44.01% | 502 / 490 | Pass |
| m_1029 | reserve | 880 | 76.39% | 454 | 47.48% | 543 / 525 | Pass |
| m_2104 | reserve | 896 | 77.78% | 275 | 49.13% | 560 / 543 | Pass |

These development-informed thresholds are unchanged engineering choices, not optimal thresholds established by experiments. Quality eligibility does not prove adequate effective sample size or future convergence. They apply to the whole 1,152-bin prefix, not independently to every proposed inner fold. In particular, inner-fit coverage for m_1426 is 635/864 (73.50%); that limitation is disclosed rather than silently applying a new partition-level exclusion.

## Prefix-only pilot partition

Use a newly named **prefix_inner_75_25_v1** fold inside the original research fit block:

- Inner fit: zero-based indices [0,864), 864 grid bins, labels 300–259,200 seconds.
- Inner development validation: [864,1152), 288 grid bins, labels 259,500–345,600 seconds.
- Original research validation [1152,1612), warm-up [1612,1842) and final evaluation [1842,2304) remain untouched and unexamined.

This uses a three-day fit and one-day inner validation to assess a small engineering pilot; it does not establish daily seasonality or replace the original research partitions. Actual counts for the later original validation block are **not available from this authorized analysis**. The chosen split was stated before computing these counts and was not searched to improve forecasting results.

## Counts and model feasibility

Across selected primaries, inner-fit genuine CPU counts are 663, 635 and 660, but only **243–329** h=1 and **223–314** h=12 genuine supervised window/target examples remain. Common learned-model validation pairs are **206–254** at h=1 and **204–242** at h=12. These are potential samples, not realized model predictions or performance.

ARIMA uses a likelihood on the full regular fit grid, skipping missing measurement updates; its usable genuine likelihood contributions after the common 24-grid-bin burn are 646, 626 and 645. It is not trained on the supervised-window count. The [training protocol](m3b1_training_validation_protocol_v1.md) gives all six machines' counts, horizon definitions and baseline denominators.

ARIMA and XGBoost are structurally feasible for a small development pilot, conditional on real-backend tests, numerical convergence and an explicit training authorization. LSTM tensor sizes are small but the highly overlapping sequence support is weak; defer LSTM from the initial two-expert pilot. See the [LSTM feasibility assessment](m3b1_lstm_resource_feasibility_v1.md).

## Verification and preservation

**130 tests passed: all existing 114 plus 16 new M3B-1 tests**, zero failures/errors; final full suite 7.217 seconds. New tests cover exact source/schema/grid/missingness checks, genuine zero CPU, allowlist/checksum/symlink guards, training target boundaries, model-ready validation origins, missing targets, direct h=12 labels across intermediate gaps, fit-example invariance under later mask changes, overlap diagnostics, independent six-prefix recounts, original roles/locks, unfitted ARIMA constructor settings and preservation.

The ARIMA check constructs unfitted models on a short constant synthetic array with missing slots. It verifies unchanged row count, common burn and diffuse initialization only. It performs no optimization, fitting, filtering, smoothing or forecasting.

All **95 prior artifact hashes** and **six permitted prefix hashes** match. The [preservation inventory](m3b1_preservation_v1.json) covers historical models/code/results, M1/M2/M2B/M2C/M2D/M3A artifacts and saved synthetic ledgers. No sealed ciphertext payload was rehashed or decrypted; its existing sealing receipt is protected.

Training and confirmation locks remain false. No model was trained, no package installed and no result overwritten. A separate M3B-2 request and development-only execution configuration are required before training can begin.


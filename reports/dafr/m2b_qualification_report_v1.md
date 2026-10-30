# DAF-R M2B — Alibaba CPU Acquisition and Qualification v1

Completed 30 October 2026. This is a data qualification result, not a forecasting experiment.

## Decision

**No nominated machine qualifies under the frozen M2 rules. The dataset is not ready for M3 development under the current manifest.** All three development primaries, six confirmation primaries, and six reserves fail the requirement that every one of the 1,152 prefix bins pass. Therefore no same-role reserve replacement is possible. This is a completed negative qualification finding, not a failed download or a reason to silently relax the protocol.

The new manifest is `configs/dafr_experiment_manifest_m2b_v1.json`. It keeps `confirmation_execution_allowed=false`, records zero qualified IDs, and preserves the original M2 manifest and nominations. No ARIMA/XGBoost/LSTM fit, forecasting evaluation, drift detector or adaptive model selection was run.

## 1. Acquisition and resources

- Pre-download disk space: **36.28 GiB**, exceeding the mandatory 4 GiB gate.
- Hardware check: Apple Silicon arm64, **8 GiB physical RAM**, **8 logical CPUs**.
- Only the official `machine_usage.tar.gz` object was downloaded, with curl partial-download resume enabled. There was no pre-existing partial file. No unrelated machine/container/batch table was acquired.
- Downloaded bytes: **1,774,523,160**, taking **308.65 seconds** (about 5 minutes 9 seconds).
- SHA-256: `3e6ee87fd204bb85b9e234c5c75a5096580fdabc8f085b224033080090753a7a`, matching the expected official checksum. Verification finished before ingestion; the ingestion entry point also rechecks it.
- Source path: `data/external/alibaba2018/m2b_v1/machine_usage.tar.gz`.
- Current access/terms provenance remains the pinned M2 evidence. The source is retained locally; no redistribution permission is assumed.

The resource and download receipt is `reports/dafr/m2b_acquisition_evidence_v1.json`. No package installation was needed.

## 2. Reader and measured computational costs

`src/dafr/alibaba_ingestion.py` streams TAR/gzip directly without filesystem extraction of the full CSV. It checks the expected member and CSV schema, retains only the 15 fixed machine IDs, and uses a private disk-backed SQLite table with a 16 MiB page cache for per-machine chronological sorting. Retained payloads are the three required raw columns; full-row fingerprints and source ordinals are duplicate/provenance metadata, not additional CPU/resource features.

| Measurement | Observed result |
|---|---:|
| Source CSV rows scanned | 246,934,820 |
| Nominated-machine raw rows retained | 930,988 |
| TAR member size read sequentially | 8,996,532,344 bytes |
| Malformed nine-column rows | 0 |
| Nominated unplaceable timestamps | 0 |
| Nominated timestamps outside the fixed eight-day window | 0 |
| CSV header | Absent; nine-column schema verified |
| Archive scan / staging / index time | 294.95 seconds |
| Total qualification, excluding download/checksum | 307.37 seconds |
| Ingestion Python process peak RSS | 112.64 MiB |
| Additional encrypted-sealing time | 12.58 seconds |
| Retained qualification artifacts after sealing | 89,376,453 bytes |
| Free disk after acquisition/qualification | 34.51 GiB |

The peak is process RSS measured by `resource.getrusage`, not system-wide RAM, OS file cache or combined encryption-child memory. The full 8.38 GiB CSV was never extracted or loaded into RAM. The generated SQLite stage was 84,221,952 bytes before encryption and is now encrypted rather than kept as readable raw staging.

Code provenance distinguishes the actually measured scan revision from later hardening. The recorded executed source SHA-256 is `71f88ad1e8cd9c84ebf82e9b2e981a717f30b19d8ad010cca4fbacbf887cec99`. After that scan, a pre-allocation row-length cap and encryption integration were added and verified with synthetic tests. Their delivered hashes are recorded in the updated manifest; no claim is made that a second full throughput benchmark was performed. These changes do not relax or change qualification arithmetic.

## 3. Prefix-only quality findings

Eligibility used only raw elapsed seconds **[0,345600)**, the first 50% of the fixed eight-day window. Neither confirmation suffix values nor suffix quality informed qualification or reserve choice.

Every nominated prefix has:
- A modal timestamp difference of **10 seconds**.
- All observed timestamps aligned to the ten-second grid.
- Only approximately **99.13–99.44% of observed consecutive intervals** equal to ten seconds. This is not full-grid coverage: one large gap can omit many expected readings.
- Between **5,290 and 9,453 missing expected raw grid timestamps**, out of the expected 34,560 prefix readings.
- No exact full-row duplicates, no conflicting duplicate CPU readings, and no same-value repeated timestamps.
- No nonfinite, nonnumeric or out-of-range observed CPU cells. There is **one missing CPU cell in `m_66`**; the other nominees have none.

These cell and grid checks were independently repeated from exported raw prefixes, using Decimal timestamp parsing. Their results are saved in `reports/dafr/m2b_prefix_validation_v1.json`. No CPU-value distribution, correlation, trend, seasonality or forecasting statistics were calculated on confirmation suffixes.

The decisive failure is incomplete measurement coverage, not a different nominal sampling rate. Even the best prefix has failed bins. Some machines also start after elapsed time zero. Failed-bin reasons include fewer than 24 valid unique samples, uncovered bin edges exceeding 30 seconds, or an internal raw gap exceeding 30 seconds. Multiple reasons may apply to a single bin.

### All nominated machines

Each row requires **1,152 valid bins**. Empty-bin counts are a subset of failed bins; no fill was applied.

| Machine | Role / nomination | Prefix raw rows | Valid bins | Failed bins | Completely empty bins | Qualification |
|---|---|---:|---:|---:|---:|---|
| `m_505` | development / primary | 29,270 | 946 | 206 | 146 | Failed |
| `m_1426` | development / primary | 28,577 | 920 | 232 | 168 | Failed |
| `m_3028` | development / primary | 28,965 | 946 | 206 | 164 | Failed |
| `m_3276` | development / reserve | 27,943 | 902 | 250 | 186 | Failed |
| `m_1029` | development / reserve | 27,221 | 880 | 272 | 206 | Failed |
| `m_2104` | development / reserve | 27,569 | 896 | 256 | 207 | Failed |
| `m_295` | confirmation / primary | 27,287 | 891 | 261 | 212 | Failed |
| `m_66` | confirmation / primary | 28,672 | 926 | 226 | 164 | Failed |
| `m_1878` | confirmation / primary | 25,107 | 815 | 337 | 288 | Failed |
| `m_197` | confirmation / primary | 28,198 | 919 | 233 | 180 | Failed |
| `m_3836` | confirmation / primary | 25,173 | 812 | 340 | 276 | Failed |
| `m_1022` | confirmation / primary | 29,036 | 935 | 217 | 149 | Failed |
| `m_1194` | confirmation / reserve | 28,299 | 912 | 240 | 173 | Failed |
| `m_1059` | confirmation / reserve | 28,419 | 915 | 237 | 167 | Failed |
| `m_2502` | confirmation / reserve | 27,032 | 872 | 280 | 215 | Failed |

The raw run's `development_prefix_nominal_ten_seconds_verified` gate is false because it is defined on the **empty qualified selection**. The observed nominee cadence itself is ten seconds. The new manifest makes this distinction explicit rather than presenting that gate as evidence for a different sampling rate.

## 4. Qualification, reserve rules and resampling

The original three development primary slots and six confirmation primary slots remain unfilled. Every reserve failed its own prefix test, so there were **zero replacements**. No additional machine IDs were searched and no machine changed roles.

The implementation applied the existing rules:
1. Sort the nominated raw records chronologically; preserve original elapsed timestamps and duplicate fingerprints.
2. Deduplicate exact full rows and prevent repeated timestamps from inflating valid sample support.
3. Exclude invalid CPU cells from means without clipping or imputing; conflicting duplicate CPU readings invalidate their bin.
4. Emit each completed **[b−300,b)** arithmetic mean at right-edge time **b**, using only raw readings strictly before that label.
5. Require at least 24 valid unique readings, internal gaps no greater than 30 seconds, and leading/trailing edge gaps no greater than 30 seconds.
6. Keep failed bins explicitly on the five-minute grid with an unavailable value and recorded reason. Do not compress time, search for the longest clean segment or fill gaps.

All expected grid positions were materialized, but **2,304 output grid rows do not mean 2,304 valid measurements**. Valid means exist only for bins that pass the frozen rules. The research partitions remain 1,152 fit / 460 validation / 230 warm-up / 462 final evaluation positions; no candidate has a qualified complete prefix for using them.

The resampled files retain the synthetic UTC anchor documented in M2. No actual collection-calendar date or seasonal pattern is inferred. The horizon definitions remain h=1 for five minutes and h=12 for sixty minutes.

## 5. Confirmation seal and provenance

Mechanical suffix parsing, causal binning, hashing and encryption were necessary to prepare the artifacts. No human inspected confirmation suffix CPU values, technical quality details, plots, statistics or forecasting outcomes. The public report exposes only prefix results, selection decisions and artifact metadata.

Permission-only sealing proved unreliable: the workspace restores owner-read permission between tool invocations. The final seal therefore encrypts:
- 27 generated confirmation files: nine suffix raw subsets, nine five-minute suffix grids and nine technical-quality receipts.
- The nominated-data SQLite staging database, which also contained later confirmation values.

All **28** encrypted artifacts were verified through streaming decrypt-to-SHA-256 checks, without CSV decoding or content display. Only after every recovery hash matched were those newly generated plaintext intermediates removed. They are recoverable using the local key at `data/external/alibaba2018/m2b_v1/qualification_20261030_001.vault.key`; the key contents were never logged. No historical/M1/M2 artifact was removed.

The immutable `seal_receipt_v1.json` maps the original paths and plaintext hashes in `qualification.json` to their replacement `.aes256` paths and ciphertext hashes. The pre-seal qualification log remains unchanged. The original source archive is also retained. This is a research holdout guard, not a confidentiality boundary against a project owner who has the local key or public source.

Run root: `data/processed/dafr/m2b_v1/qualification_20261030_001/`. Readable prefixes and development suffix artifacts remain separate from encrypted confirmation suffixes. The source/clean hashes, machine metadata, exact original rules, prefix failures and code provenance are linked from the new manifest.

## 6. Verification

- **53 tests passed:** 31 existing regression/chronology tests plus 22 new ingestion/preprocessing/sealing tests.
- Tests cover checksum failure before ingestion, disk/memory/row-size gates, schema rejection, nominated-ID filtering, decimal timestamps, exact/conflicting duplicates, invalid CPU cells, exact count/gap/edge thresholds, causal bin boundaries, explicit missing bins, fixed-order same-role reserves, future-suffix invariance, exclusive run creation and encrypted recovery before plaintext removal.
- An independent raw-prefix pass reproduced row/unique counts and checked missing cells and grid timestamps.
- SHA-256 checks confirm **all 50 pre-M2B protected files remain unchanged**, including M1, original M2 documents/configuration, and historical ARIMA/XGBoost forecasts.
- No code path trained models, installed TensorFlow, fitted a detector/selector or ran forecasting evaluation.

## 7. Remaining limitations and next decision

The source is computationally manageable, but the selected streams do not satisfy the current complete-grid research protocol. More than 500 valid bins does not overcome the explicit regularity and completeness requirement. All sampled machines share a production cluster; machine/domain separation does not prove statistical independence, and eight days cannot establish weekly seasonality.

**M3 must not start from this manifest.** A separate, explicitly versioned data-protocol decision is needed: either investigate a causally specified missing-data policy or select another suitable source. Any such change must be declared before confirmation suffix analysis, with fresh confirmation separation where needed. This M2B run does not authorize an automatic threshold relaxation, interpolation, start-time shift or additional machine search.


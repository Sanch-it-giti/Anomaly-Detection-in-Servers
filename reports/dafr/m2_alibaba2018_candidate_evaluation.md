# DAF-R M2 — Alibaba 2018 feasibility and experimental manifest

Assessment begun 29 October 2026. Scope: source investigation, metadata-only nominations and experiment planning. M1 and historical forecasting artifacts remain preserved. No learned model, CPU-trajectory analysis, confirmation forecasting outcome, or hyperparameter tuning was used in this assessment.

## Decision

**Conditionally feasible for a small set of individual machine CPU streams on an 8 GB Apple Silicon Mac, using sequential archive processing.** It is not suitable for a whole-cluster in-memory load. Access, schema, metadata identities and archive sizes have been checked. Per-machine usable length, raw sampling intervals and complete chronological coverage have **not** been measured: the CPU CSV was not read. Therefore this is a candidate selection manifest, not a claim that nine usable machine series have already been extracted.

Alibaba 2018 adds separate machine workloads and an external source. It does not add a longer observed history than the existing approximately two-week NAB example. Distinct machines in one shared production cluster also do not establish statistically independent workloads. Initial failure-domain separation reduces known overlap but cannot remove cluster-wide dependencies.

## 1. Evidence and access verification

Documentation is pinned to official repository commit `3858992ca41bf92082e6d6522ddf0bebd14e838b`. The companion `m2_source_evidence_v1.json` records documentation hashes, endpoint observations, metadata counts, archive identities and all 46 pre-existing artifact hashes captured before M2 changes.

- The release describes about 4,000 machines over eight days and offers separate table archives. Its documentation describes a survey and also explicitly provides access without completing it. No form was submitted. [Official release description](https://raw.githubusercontent.com/alibaba/clusterdata/3858992ca41bf92082e6d6522ddf0bebd14e838b/cluster-trace-v2018/trace_2018.md).
- The published fetch script points to Alibaba OSS. An HTTPS HEAD request to its `machine_usage.tar.gz` object returned **200**, a content length of **1,774,523,160 bytes**, and byte-range support. The script itself was inspected, not executed; executing it would retrieve unrelated large tables. [Official fetch script](https://raw.githubusercontent.com/alibaba/clusterdata/3858992ca41bf92082e6d6522ddf0bebd14e838b/cluster-trace-v2018/fetchData.sh).
- A **4,096-byte** range request returned **206**. Only the first **512 decompressed bytes**, the TAR member header, were decoded. It declares `machine_usage.csv` at **8,996,532,344 bytes**. No CPU CSV row was decoded. This is an archive-header size, not a completed decompression or a whole-archive integrity check.
- The small metadata archive was read in memory: **92,432 compressed bytes**, matching the publisher's SHA-256. Its CSV is **552,566 bytes**, with **17,592 metadata-event rows** and **4,034 distinct IDs**. These are measured metadata counts, not proof that all IDs have CPU measurements. Of these, **3,887** have unambiguous domain metadata at elapsed time zero; **147** do not. Among the former there are 292 domain-1 values and 20 domain-2 values. Only time-zero domains were used for nominations.
- The expected usage-archive SHA-256 is recorded from the release. It is **not verified** because the whole 1.65 GiB machine-usage object was not downloaded. Multipart ETags are recorded as object metadata and are not substituted for SHA-256.

No full dataset archive, container trace, batch table or full machine-usage table was acquired. The metadata/TAR-header probes read 96,528 unique archive-body bytes; the metadata archive was fetched a second time to produce a compact nomination result. Documentation/API traffic is additional. No downloaded archives were saved locally; derived evidence and nominees are saved as JSON.

## 2. Usage terms and remaining permission limits

The official README expressly permits use for research or study in its motivation section. This university experiment fits the described purpose. A root-directory listing found no standalone LICENSE/COPYING/NOTICE file, and GitHub's license API returned 404. No SPDX license or explicit raw-data redistribution grant was verified. [Official README](https://raw.githubusercontent.com/alibaba/clusterdata/3858992ca41bf92082e6d6522ddf0bebd14e838b/README.md).

There is currently no demonstrated access or stated research-use blocker. Raw-data redistribution remains unresolved: retain data locally, preserve attribution and the source terms, and do not publish the raw/derived machine traces under an assumed MIT/Apache license. Requests for broader use or redistribution would need clarification from the publisher; no email or external message was sent. A README statement permitting study should not be relabeled as a standard open-source license.

## 3. CPU schema and time semantics

The official schema aligns these fields with the machine-usage CSV column order. [Official schema](https://raw.githubusercontent.com/alibaba/clusterdata/3858992ca41bf92082e6d6522ddf0bebd14e838b/cluster-trace-v2018/schema.txt).

| Zero-based column | Field | Source type | Project use |
|---:|---|---|---|
| 0 | `machine_id` | string | Preserve original individual-machine identity |
| 1 | `time_stamp` | double | Elapsed seconds from trace start |
| 2 | `cpu_util_percent` | bigint | Machine CPU-utilization percentage, valid range 0–100 |
| 3–8 | `mem_util_percent`, `mem_gps`, `mkpi`, `net_in`, `net_out`, `disk_io_percent` | mixed numeric | Ignore for this univariate experiment |

Retain the official `mkpi` spelling in the raw schema mapping. Do not confuse machine CPU percentage with container requests or batch CPU fields whose core-based conventions differ. Machine metadata separately provides `machine_id`, `time_stamp`, `failure_domain_1`, `failure_domain_2`, `cpu_num`, `mem_size`, and `status`; only ID and initial domains are needed for nomination.

These timestamps are not Unix timestamps and do not provide actual calendar dates or timezone. For future M1-compatible replay, map elapsed-bin-end seconds to **2000-01-01T00:00:00+00:00 plus elapsed time**, explicitly labeled a synthetic UTC anchor. Keep original elapsed seconds and mapping metadata. Do not infer weekday, timezone, calendar seasonality or real collection dates from that anchor.

## 4. Sampling and observation sufficiency

The official 2018 schema establishes seconds as the time unit but does not guarantee exact regular sampling. A primary research paper reports a nominal **10-second** interval for the 2018 trace; this is literature-supported context, not an empirical verification of the nominated streams. [Author-hosted TFEGRU paper, experimental dataset description](https://www.cs.newpaltz.edu/~lik/publications/Feiyu-Zhao-IEEE-TSC-2025). Do not import the 2017 release's different sampling/averaging statement into this release.

Conditional arithmetic for a complete eight-day machine record:

- At a ten-second nominal interval: approximately **69,120 raw observations per machine**.
- On a complete five-minute grid: **2,304 derived observations**, exceeding the project's 500-observation minimum.
- DAF-R `h=1` then targets the next five-minute aggregate; `h=12` targets the aggregate sixty minutes later. It does not require an hourly dataset or twelve-hour forecasts.

The 2,304 count is a **planned grid size, not observed data**. Actual raw cadence, timestamp duplicates, missing bins, CPU validity and per-machine coverage are pending prefix-only checks. Short or irregular traces cannot be certified from metadata alone. Eight days is also too short to establish weekly seasonality or broad generalization.

## 5. Storage and memory budget

| Item | Amount | Evidence status |
|---|---:|---|
| Full cluster release, compressed | Approximately 48–49 GB | Official published estimate; not acquired |
| Full cluster release, extracted | Approximately 280 GB | Official published estimate; not extracted |
| Machine-usage archive only | 1,774,523,160 bytes / 1.65 GiB | Current HTTP Content-Length |
| Machine-usage CSV | 8,996,532,344 bytes / 8.38 GiB | Bounded TAR-header declaration |
| Usage archive plus extracted CSV | Approximately 10.03 GiB | Arithmetic; avoid this extraction path |
| Nine nominated primary streams, two numeric columns, 2,304 rows each | Approximately 0.32 MiB | Packed-array arithmetic only, not Python/CSV/log size |

The official file-size listing counts both combined and separate archives in its total; do not misread that total as a requirement to download both. For actual work, only machine metadata and machine usage are required.

At the hypothetical 4,034-machine, eight-day, ten-second density, there would be approximately **278.8 million raw rows**. Nine eight-byte fields per row alone would occupy about **18.7 GiB**, before Python strings, indexes, copies and parsing buffers. This is an illustrative density calculation; actual row count was not measured. Loading the full CSV with pandas is inappropriate on this Mac.

The proposed acquisition path reserves **at least 4 GiB free disk**, keeps the compressed usage file for checksum verification, and streams TAR/gzip entries through a sequential CSV reader. Filter only the 15 nominated primary/reserve IDs, retaining the required columns. A bounded reader or chunks of at most 50,000 rows should target **under 1 GiB process RSS**; stop at **4 GiB RSS**. Allow up to 256 MiB for selected raw staging as a conservative cap; actual projected arrays are much smaller. These memory/disk caps are planning limits, not measured ingestion benchmarks. No full CSV extraction, full-cluster dataframe, parallel candidate loading or bulk fetch script is planned.

The CPU table is a single compressed object, not a verified per-machine download service. Selecting nine machines can reduce retained memory/storage, but generally still requires a sequential scan of the machine-usage archive. Network/decompression time remains a feasibility cost even when output series are small.

## 6. Deterministic development/confirmation nominations

The metadata-only seed is **`DAFR-M2-v1`**. The exact rules are recorded in the manifest:

1. Start with IDs having a single unambiguous `(failure_domain_1, failure_domain_2)` pair at time zero. Do not select by later machine status or workload trajectory.
2. Rank distinct initial domain-2 strings by SHA-256 of UTF-8 `DAFR-M2-v1|domain|<domain>`, breaking ties by the exact string. Even zero-based ranks form development pools; odd ranks form confirmation pools.
3. Within each pool's domains, rank machine IDs by SHA-256 of `DAFR-M2-v1|machine|<machine_id>`, with the same tie rule. Iterate development first, then confirmation; nominate the first ranked machine whose domain-1 identifier has not already been nominated. Nominate at most one machine per domain-2 value.
4. Keep three development primaries plus three reserves, and six confirmation primaries plus three reserves. Role order is frozen in the inventory. No CPU value or forecasting result enters this ranking.

| Role | Primary nominees | Reserves in fixed order |
|---|---|---|
| Development | `m_505`, `m_1426`, `m_3028` | `m_3276`, `m_1029`, `m_2104` |
| Confirmation | `m_295`, `m_66`, `m_1878`, `m_197`, `m_3836`, `m_1022` | `m_1194`, `m_1059`, `m_2502` |

All 15 nominees have distinct initial domain-1 and domain-2 values. These are **nominees pending prefix quality**, not final qualified machines. Keep the role assignment fixed; use the first eligible same-role reserve only when a primary fails predefined prefix checks, before suffix inspection. No post-lock replacement based on quality of final CPU outcomes, model errors, coverage or apparent drift. If a confirmation suffix later fails the frozen quality rules, record the failed/incomplete stream and reduced sample count. Do not replace it with an easier workload.

The full metadata machine-ID set is fingerprinted by SHA-256 of lexicographically sorted IDs, joined by newline including a final newline. The inventory records each nominee's ranking hash and time-zero domains. Shared-cluster dependence still limits statistical claims despite domain separation.

## 7. Fixed chronological partitions

Prespecify the raw analysis window **[0, 691200) seconds**, without searching the full record for the longest clean segment. Emit completed five-minute bins with right-edge labels 300 through 691200. Use fit `floor(0.50N)`, validation `floor(0.20N)`, warm-up `floor(0.10N)`, and evaluation remainder.

For the planned N=2,304:

| Block | Zero-based indices, half-open | Count | Bin-end elapsed seconds, inclusive |
|---|---|---:|---|
| Fit | [0, 1152) | 1,152 | 300–345600 |
| Validation | [1152, 1612) | 460 | 345900–483600 |
| Calibration / warm-up | [1612, 1842) | 230 | 483900–552600 |
| Final evaluation | [1842, 2304) | 462 | 552900–691200 |

Development-machine fit/validation data can inform global settings. Confirmation-machine data cannot choose global or per-machine hyperparameters: after global settings freeze, the allowed first-70% prefix fits expert parameters/scalers with that fixed recipe. Its nominal validation block remains chronological pre-evaluation history, not a new tuning opportunity. Warm-up updates only the prespecified online state using matured forecasts. The final block remains sealed until the entire experiment configuration and actual qualified ID list are locked.

At h=12, starting forecasts at the final fitted-prefix origin yields **219** matured warm-up errors by evaluation start under a complete grid (230 minus the first eleven target positions). This exceeds the proposed 100-score support minimum, but is a timing calculation rather than observed calibration performance. Evaluation metrics use target-based phase assignment; a pre-evaluation origin can legitimately predict a final-block target. All policies receive the same targets at each horizon; unarrived tail targets remain unscored.

The M1 JSON's 12-observation synthetic warm-up must not be reused as the independent-data experiment's warm-up. Its protocol file is preserved; M2's partition plan is separate and not executable by M1's current loader. If the fixed eight-day grid cannot be supported, revise the data protocol before confirmation-suffix inspection, rather than silently shortening a workload.

## 8. Prefix quality gates and causal preprocessing specification

Only raw elapsed seconds **[0, 345600)** may determine initial machine eligibility. This is the first half of the planned window. Check the actual development-prefix timestamp deltas before treating ten seconds as a verified nominal interval; freeze any necessary cadence-protocol revision before confirmation data is opened. The planned bin thresholds below are conditional on that verification.

- Validate nine-column schema, machine identity, finite nonnegative elapsed seconds and numeric CPU values. Preserve decimal timestamp precision; do not reinterpret elapsed seconds as epoch time. Header presence has not been empirically checked: detect a declared header deterministically or fail rather than silently dropping the first data row.
- Keep valid CPU values in [0,100]. Missing/nonfinite values and invalid sentinels/out-of-range values cannot contribute to a bin; count them explicitly. Do not clip extremes, delete valid spikes, or screen machines by high forecast accuracy, high variance or convenient drift behavior.
- Remove exact duplicate full rows deterministically with a counter. Conflicting CPU values for the same machine/time invalidate that bin. Sort per machine by raw timestamp for replay; sorting does not authorize transformations that use future values.
- For bin end `b`, compute an arithmetic mean from valid unique readings with timestamps in **[b−300, b)** and publish at `b`, only after the bin is complete. Require at least 24 unique readings, no inter-reading gap over 30 seconds, and no leading/trailing uncovered edge interval over 30 seconds. This defines a forecast of future five-minute means, with no sample after `b` leaking into a feature available at `b`.
- Require all 1,152 fit-prefix bins to pass for initial eligibility. The final qualified research stream requires the full 2,304-bin grid. Do not forward-fill, interpolate, backfill, relabel gaps as adjacent observations, choose the longest convenient segment, or concatenate machines.
- Keep constant/zero CPU series if they pass data-quality gates; mark MAPE/MASE invalid when their denominators require it. The primary MAE remains available.
- Mechanically filtering/hashing later records into sealed artifacts does not authorize analysts to plot or tune from their values. Any post-lock quality failure is reported without outcome-based replacement or silent exclusion.

A prefix-QC exclusion must have a machine ID, role/rank, explicit reason and counts, no suffix-value summary. Additional exclusions are unknown/ambiguous initial domains, unrecognized metadata identity, incompatible units, or known cross-role duplicate physical identity. No full-series CPU similarity search is permitted to select confirmation machines; metadata and prefix-only duplicate checks are the initial overlap controls. Record any previously unknown provenance concern rather than asserting machine IDs prove independence.

## 9. Provenance and experiment lock requirements

Before confirmation, retain the official source/version and terms hashes, verify the complete compressed usage checksum, record raw and filtered row counts, source-to-bin mapping, all invalid/duplicate/gap decisions, per-machine data hashes and exact split boundaries. Lock the qualified role lists, global model/detector/selector/calibrator recipe, hardware/runtime budget, output paths and access log. A changed manifest becomes a new version, never an overwrite.

`configs/dafr_experiment_manifest_v1.json` currently sets `confirmation_execution_allowed` to false. This accurately records unfinished data qualification and configuration freezing; it is not a runnable training configuration or a claim that confirmation experiments are ready. M2 stops at feasibility and manifest preparation.

All ten previously screened NAB CPU series remain **exploratory** in the inventory. Their inspected final-test outcomes cannot select DAF-R settings or act as confirmation. The M1 synthetic data is an engineering fixture, not a research replication unit.

## 10. Remaining gates and handoff

The remaining data-stage gates are complete usage-archive checksum verification, bounded sequential extraction, development-prefix cadence checks, same-rule nominee prefix quality checks, and actual per-machine manifest lock. These are explicitly pending; none was silently treated as successful. Research-use permission and current endpoint access are supported; raw redistribution is not established. No claim of calibrated intervals, seasonality, model improvement or statistical independence follows from this assessment.

Created alongside this assessment: `m2_source_evidence_v1.json`, `m2_dataset_inventory_v1.json`, and `../../configs/dafr_experiment_manifest_v1.json`. Validation checks JSON consistency, nomination disjointness/ranking, partition coverage/horizons and preservation of pre-M2 hashes. M3, TensorFlow installation, model training and dashboard work remain outside this completed task.

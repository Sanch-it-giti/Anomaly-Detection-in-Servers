# M7A completion — synthetic engineering diagnostic only

7 November2026. Run `m7a-synthetic-20261107-001`. **M7A is complete. Stop after this milestone.** No real-world coverage, uncertainty-calibration guarantee, independent DAF-R improvement or real-data result is claimed.

## Approved constraints and implementation

The original research design section4.3 requires both90% and95% intervals, so both are retained rather than silently using90% alone. The readiness plan's minimum100, capacity288 and288 elapsed-grid-tick recency are frozen. For n same-policy/horizon/era genuine prior errors, the radius is the ceil((n+1)×nominal_percent/100)-th smallest absolute error, using exact integer arithmetic and no interpolation. Insufficient support/rank means null bounds with the point center retained. This engineering configuration does not authorize opening research calibration/final/confirmation partitions.

New frozen contracts retain original immutable source forecasts, support counts/time bounds/digests, calibration forecast/outcome links, interval IDs/bounds/rank/configuration provenance and later coverage/width/interval-score outcomes. Separate buffers belong to complete policy/version/horizon/current telemetry era. Fixed shadow experts, adaptive and persistence never borrow each other's errors. Adaptive's own issued fallback errors explicitly remain adaptive-policy scores, as the approved original complete-policy design requires. Such intervals describe the complete mixed-source policy, not a guarantee conditional on the current expert or fallback source. Model metadata/version changes are rejected rather than silently inheriting old support.

The new standard-library engine processes current revealed genuine/missing ticks, ages/resets support, resolves earlier issued intervals and inserts genuinely matured own-policy errors, then attaches intervals to current immutable point centers. Current-target errors may inform forecasts for later exact targets. Wrong observations/arrival links, future feedback, duplicate policy/origin issuance, revisions and late feedback after interval issuance are rejected. The fourth missing tick resets once per gap; old-era genuine outcomes still score original intervals but do not populate new-era support. Missing and pending targets never create coverage outcomes or fake zero residuals. Abstentions and gated/numerically failed experts remain explicitly unavailable.

Bounds are **raw center±radius, not clipped to[0,100]**. Width/coverage/interval-score diagnostics use those same raw bounds. Out-of-range endpoints are counted; none occurred in these saved fixtures, and a unit test confirms that raw out-of-range bounds remain visible. No unbounded interval is created; cold-start bounds are unavailable/null, never fabricated zero width. All point centers are unchanged.

## Synthetic results and limitations

Ten fixed fixtures cover stable errors, growing/shrinking variation, abrupt changes, an isolated extreme, short missing runs, leading/long/trailing gaps and recovery, insufficient support, numerical expert failures, and calibration expiry during prolonged model unavailability with continuous telemetry. Delayed h12, pending targets and future-suffix invariance are also tested. Deterministic mock experts are used throughout; these are not newly trained ARIMA/XGBoost/LSTM results. No fitting or outcome-driven parameter selection took place.

Complete adaptive-policy overview,90% nominal intervals, on genuinely observed targets with available bounds:

| Fixture | h1 coverage | h12 coverage | h1 mean issued width | h12 mean issued width |
|---|---:|---:|---:|---:|
| stable |89.96%|90.30%|1.355893|3.446284|
| growing variation |57.53%|56.12%|3.170767|8.081442|
| shrinking variation |100.00%|97.47%|4.464976|11.932068|
| abrupt change |71.81%|64.56%|3.382704|8.573570|

Widths are CPU percentage points. Stable/growing/shrinking/abrupt rows each have259 /237 available genuine intervals at h1/h12, out of359 /348 genuine matured adaptive centers; warm-up unavailability is reported, not hidden. At95% nominal, growing variation covers only66.41% /64.14%. Shrinking variation can retain excessive width. These unfavorable outcomes remain unchanged. The insufficient-support fixture has59 /48 genuine targets and **zero available intervals**, not zero empirical coverage; coverage is unavailable.

The [full diagnostic report](coverage_width_availability.md) and [160-row CSV](coverage_width_availability.csv) retain every policy, horizon and nominal level, both availability denominators, covered/genuine counts, mean/median issuance widths, genuine-scored width, proper interval score, missing/pending/fallback/unissued counts and coverage gap. No aggregate cross-policy coverage headline or claim of adaptive superiority is made. Equal masks would be required for a comparative performance claim.

Across3430 synthetic grid ticks there are27440 source point decisions and54880 two-level interval attempts. Unique source accounting:24303 genuinely scored targets +104 missing targets +498 pending +2535 unissued attempts =27440. Interval accounting:30786 genuine available scores +17820 genuine interval-unavailable outcomes +208 missing outcomes +996 pending issued intervals +5070 center-unavailable attempts =54880. In the long-gap fixture,22 genuine old-era errors remain in audit records but cannot seed new calibration. Prolonged failures expire fixed-shadow support; the adaptive policy keeps calibrating its own real issued fallback centers under the declared rule.

## Verification and preservation

**381 tests passed:341 existing +40 new; zero failures/errors;106.042seconds.** The final source/config/design gate was frozen after that run and before saved execution. Earlier incremental test runs also passed. The final command was:

`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v`

Tests cover exact finite-sample order statistics and floating-boundary cases, source-specific buffers, current-observation identity, delayed h12 feedback, support99/100, capacity/expiry, fallback attribution, numerical failures, all-missing streams, gaps/resets/recovery, old-era exclusion, exact coverage/width/interval-score arithmetic, raw CPU-bound behavior, future-suffix perturbation, immutability, duplicate rejection, model-version refusal, no observation/model loading by the new driver, exclusive outputs and tamper rejection even after a forged file-level hash is updated.

All **ten independent saved-ledger audits pass**. The auditor does not call the interval engine: it reconstructs support/era/expiry from source ticks and original outcomes, checks integer quantiles and support digests, verifies original forecast links, recalculates interval outcomes and confirms complete eligible calibration accounting. Authoritative source/disabled source event files and drift/disabled drift event files are byte-identical. Thus intervals changed **no point forecasts, selector decisions or drift alarms**. Old forecast-contract fields remain unchanged; external M7A records represent the new component.

**739 protected historical hashes match**, extending the prior690 with M6B artifacts and its final inventory. All **six historical checkpoint bundles /27 files** match; M7A never loads a historical model. The739 protection set also pins the previous synthetic checkpoints and saved research outputs. Original code/configuration/ledgers/results remain unchanged. Original research/confirmation locks remain false or byte-identical as applicable. Actual retry of this run ID was rejected before execution and all124 then-existing saved files remained unchanged. See `overwrite_preservation.json` and `preservation_verification.json`.

## Cost and deliverables

Whole saved execution including independent audits: **55.365015seconds**; peak process high-water RSS **301.125MiB**. Active calibration support is bounded; small-run immutable audit ledgers are kept in memory. This is not a production latency benchmark, and p95 issuance latency was not measured. See `runtime_memory.md` for per-fixture timings and limitations. No dependency installation occurred.

New source/configuration/design files:

- `configs/dafr_m7a_synthetic_v1.json`
- `src/dafr/interval_contracts_v1.py`
- `src/dafr/interval_v1.py`
- `src/dafr/interval_streaming_v1.py`
- `src/dafr/interval_fixtures_v1.py`
- `src/dafr/audit_m7a_v1.py`
- `src/dafr/run_m7a_v1.py`
- `tests/test_dafr_intervals_v1.py`
- `reports/dafr/m7a_interval_design_v1.md`
- `reports/dafr/m7a_preservation_v1.json`
- `reports/dafr/m7a_synthetic_gate_v1.json`
- `reports/dafr/m7b_readiness_boundary_plan_v1.md`

Exclusive synthetic manifests, completion marker and ten case ledgers are under `data/processed/dafr/m7a_synthetic_v1/m7a-synthetic-20261107-001/`. Each case saves ticks, source forecasts/outcomes/events, disabled source events, original/disabled drift events, intervals, calibration scores, interval outcomes, summary and hashes. Public CSV/diagnostic/runtime/preservation/completion reports are under this directory. The final artifact inventory hashes all new delivered files and excludes itself.

## Remaining research boundaries and next step

Rolling absolute-residual intervals do not automatically yield formal exchangeability-based, conditional, short-window or real-world coverage guarantees under dependence, drift and switching. Growing variation undercovers; shrinking variation can make intervals too wide; policy mixtures, initial support, gaps and stale errors limit reliability. Raw unclipped endpoints may be physically impossible in other settings and must remain reported. No setting was retuned after these results.

M5B-2's lack of adaptive improvement and M6A's missed abrupt h1 step, early-support limitations and repeated alarms remain. No reliability-based selection, ACI, detector-triggered calibration reset, new CPU-level detector, refit, LSTM or dashboard was implemented. No new Alibaba observations or restricted calibration[1612,1842), final[1842,2304) or confirmation data were opened. Existing regression-only fixture reads are unchanged; all new interval experiments use generated observations.

**Ready for review of a separately authorized M7B synthetic real-backend integration; not ready or authorized for real-data coverage/confirmation claims.** A validated real-backend interval bridge and model-version calibration convention must be approved first. M7B has not started. Stop after M7A.

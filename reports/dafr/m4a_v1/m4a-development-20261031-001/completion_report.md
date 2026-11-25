# M4A completion — forward fixed-model DEVELOPMENT benchmark

Completed 31 October 2026. Run: `m4a-development-20261031-001`. **Ready for review; stop after M4A.**

## Scope and frozen settings

Evaluated exactly **[1152,1612)** for **m_505, m_1426 and m_3028**, 460 five-minute positions each, including missing positions. The earlier permitted [0,1152) histories were used only for checkpoint/state reconstruction. No reserve/confirmation suffix, calibration/warm-up [1612,1842), or final evaluation [1842,2304) was opened. No encryption key was opened and no decryption was needed.

The new [M4A execution configuration](../../../../configs/dafr_m4a_execution_v1.json) authorizes only this benchmark; fitting, refitting and confirmation are false. Historical configurations and execution locks remain byte-identical. The historical M3B-2 training authorization is not repurposed as permission for new fitting.

ARIMA (1,1,1) and direct XGBoost C1 (depth 2, 100 trees, learning rate 0.05) were selected previously, using inner validation [864,1152). Their original fitted artifacts, features and scalers were reused unchanged. No model/configuration was reselected. The source-hashed engineering gate was recorded before reading new block values. Descriptive temporal windows were also fixed before that access.

## Chronology and provenance

Saved ARIMA parameters rebuild the fitted state through index 863 once; the last 23 fitted grid positions populate input context without being assimilated again. Both adapters then advance once per index 864..1151, including missing events. **All six reconstructed end-state hashes exactly match their completed M3B-2 ledgers.** Reconstruction issues no predictions, imports no historical pending forecasts, and seeds no error/calibration buffers.

Each new tick follows reveal → exact-target resolution/scoring → era/support maintenance → both fixed-state updates using the identical immutable context → state record → h=1/h=12 issuance. First origin is 1152 after its arrival, never before model/configuration selection. All forecast records retain original checkpoint training/scaling/version provenance plus a frozen envelope recording policy-selection cutoff 1151, the requested checkpoint metadata hash and M4A execution hash. Target availability is not supplied at issuance.

The same 24-consecutive-genuine gate, age-three persistence fallback, stale abstention, fourth-missing era rule and genuine exact-target rules apply throughout. ARIMA updates filtered state without parameter optimization and advances across missing ticks. XGBoost retains elapsed grid positions and consumes genuine declared lag inputs when the gate passes. Interval bounds remain null and drift/selection functions remain disabled.

All 8,280 decisions reconcile as **8,139 scored**, **24 target-unavailable**, **117 boundary-pending**, **zero abstentions**. Each policy/machine has one h=1 and twelve h=12 pending forecasts, including targets outside the authorized block. They remain unscored. Earlier M3B-2 pending records remain unchanged; no outcomes were backfilled.

## Findings and availability

Equal-machine expert-matched MAE / RMSE (CPU percentage points):

| Policy | h=1 (five minutes) | h=12 (sixty minutes) |
|---|---:|---:|
| Persistence | 4.125690 / 5.424773 | 7.133119 / 9.324500 |
| Fixed ARIMA | 3.901195 / 5.104576 | 6.797972 / 8.788959 |
| Fixed XGBoost | 4.396641 / 5.801670 | 6.937706 / 9.025295 |

Common genuine comparison counts are 1,297 and 1,272, respectively. Complete-policy results, per-machine errors, support counts and descriptive M3B-2 comparisons are in [comparison.md](comparison.md) and [forward_metrics.csv](forward_metrics.csv). No model-specific subsets were pooled to claim gains.

| Machine | Genuine / grid | Missing indices | Longest gap | Expert / fallback decisions per learned policy, per horizon | Abstentions |
|---|---:|---|---:|---:|---:|
| m_505 | 458 / 460 | 1201,1203 | 1 tick | 431 / 29 | 0 |
| m_1426 | 459 / 460 | 1585 | 1 tick | 436 / 24 | 0 |
| m_3028 | 459 / 460 | 1557 | 1 tick | 436 / 24 | 0 |

Persistence issued at all 460 origins per machine/horizon. After missing observations, learned policies used explicit fallback until 24 genuine consecutive bins recovered. The two nearby m_505 gaps have overlapping recovery periods; its initial three gated origins also reflect the genuine streak carried from the prefix. All missing targets produced linked null-error outcomes. There were no four-tick gaps or new telemetry eras here, so long-gap and abstention behavior is verified synthetically, not demonstrated by this block.

ARIMA has the lowest whole-block macro errors at both horizons. XGBoost is worse than persistence at h=1 macro, and worse on m_3028 at both horizons; these unfavorable observations are retained. Local losses vary: h=12 final-third macro MAE slightly favors XGBoost, whereas the first two thirds favor ARIMA. [Temporal analysis](temporal_loss_analysis.md) reports the frozen partitions, denominators and interpretation limits. This does not establish drift or DAF-R improvement.

## Verification and resources

- **166 tests passed before access** (147 existing + 19 new), zero failures/errors, 10.792 seconds.
- **166 tests passed again after replay**, zero failures/errors, 10.756 seconds.
- New tests cover read boundaries before CPU fields, no read-ahead/tail dependence, reconstruction, shared contexts, exact horizons, delayed feedback, missing events, recovery, immutable parameters/predictions, future-suffix perturbation, fitting prohibition, support-safe macro reporting and historical preservation.
- Saved-ledger audits independently verify exact timestamp/horizon joins, error arithmetic, reveal/score/state/issue sequence, shared context digests at all **1,380 machine/tick combinations**, missing/abstention semantics, and pending reconciliation. The extended audit also recomputes both metric scopes from saved outcomes.
- All **297 protected historical SHA-256 values** and all selected checkpoint fingerprints match. No historical source, model, configuration, forecast or report changed.
- Reusing the run ID was refused before data access; all 60 files then present in the new run remained byte-identical. Creation uses exclusive files/directories; ledgers are never revised.
- Runtime was **103.377 seconds**, peak process RSS **213.45 MiB**, below the 4 GiB guard. Maximum whole-tick p95 including serialization/buffered writes was **54.951 ms**. No numerical failures, stale states, parameter changes, fitting calls or resource stops occurred. See [runtime report](runtime_resource_report.md).
- All twelve private plots decode successfully; representative forecast/error and trailing-loss plots and the public aggregate chart were visually reviewed. Matplotlib's temporary font-cache creation was informational, not a remaining error.

## Restricted extraction and integrity scope

Existing separate plaintext development exports were read unbuffered one byte at a time, checking each timestamp/bin-end label **before** reading that row's CPU field. The reader stopped immediately after authorized row 1611, with no read-ahead into 1612. Bytes consumed, including headers: m_505 **25,675**, m_1426 **25,288**, m_3028 **25,513**. Each scoped copy contains 460 rows and has a newly verified SHA-256 receipt. Source file size/inode/mode/modification time were unchanged.

The original M2B full-export hashes remain historical provenance. **They were not freshly recomputed**, because doing so would read forbidden later blocks. Current integrity evidence combines protected original metadata, unchanged recorded size/stat, exact scoped labels/quality validation and fresh scoped-copy hashes. It does not prove cryptographic equality of unread source tails; no such claim is made. Whole-block extraction creates a private bounded copy; the simulator still reveals one tick at a time and receives no future target mask or fitted transformation.

## New deliverables

- `configs/dafr_m4a_execution_v1.json` and `reports/dafr/m4a_backend_gate_v1.json`.
- `src/dafr/scoped_development_reader_v1.py`: restricted reader and extraction receipts.
- `src/dafr/forward_streaming_v1.py`: selected-checkpoint reconstruction, immutable provenance envelopes and forward-only driver, preserving earlier simulators.
- `src/dafr/run_m4a_v1.py`: no-fitting benchmark, metrics, plots and resource guard.
- `src/dafr/audit_m4a_v1.py`: independent saved-ledger and metric checks; does not reopen original suffix exports.
- `tests/test_dafr_forward_v1.py`: 19 additional tests.
- `reports/dafr/m4a_preservation_v1.json`: original 297-file inventory.
- This versioned report directory: completion/comparison/temporal/resource reports; per-machine and macro JSON/CSV tables; missingness, scope/runtime receipts; initial and extended ledger audits; overwrite protection; aggregate plot; final verification and artifact inventory.
- Private ignored `data/processed/dafr/m4a_development_v1/m4a-development-20261031-001/<machine>/`: scoped input/receipt, bootstrap/reconstruction records, combined event ledger, immutable per-policy prediction/outcome ledgers, pending IDs, machine summary and twelve actual forecast/error/temporal figures across the machines. Derived traces remain local rather than being included in public reports.

## Limits and stopping point

Three correlated development machines and a 38-hour-20-minute grid block provide limited evidence. The selected-model benchmark is subsequent to tuning, but it is still development data, not final confirmation. Missingness is sparse; no sustained outage, fallback expiration or telemetry-era reset occurred in this real block. Macro differences and temporal rank changes have no significance or drift interpretation established here. Runtime measurements exclude a deployed service and model training.

No fitting, LSTM installation/training, adaptive selector, drift detector, prediction intervals or dashboard was performed. Confirmation remains locked and calibration/final blocks remain unopened. **M4A is ready for review. M5 and any further data access require separate authorization.**

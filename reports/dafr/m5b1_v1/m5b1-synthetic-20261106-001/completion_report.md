# M5B-1 completion — real-backend adaptive integration, synthetic verification

Completed 6 November 2026. Run `m5b1-synthetic-20261106-001`. **Ready for engineering review; stop after M5B-1.** No real-data adaptive benchmark was executed.

## Implemented integration

The separate real-backend driver uses the existing exact registered `RealAdapter` implementation for statsmodels ARIMA and native XGBoost, connected to the frozen M5A selector through a typed feedback bridge. M5A contracts, thresholds and synthetic driver remain byte-identical. No frozen scientific rule required modification.

The selector still needs **100 matched genuine pairs per horizon**, retains at most **288 pairs** from the current 288-grid-tick window, requires **24 elapsed ticks of dwell**, and switches only for improvement **max(0.1 CPU percentage points, 5%)**. Default ARIMA, incumbent-retaining ties, independent horizons, unavailable-incumbent fallback, history gate and era conventions are unchanged. `MatchedSelectorV1.choose` is inherited directly; the bridge adds no alternative loss rule.

New immutable forecasts distinguish actual expert shadows, selected adaptive centers, persistence fallback, unissued attempts and genuine/missing outcomes. Records retain actual model/version metadata plus checkpoint, parameter, filtered-state, registry and execution fingerprints. Requested incumbent provenance remains visible during fallback; the actual source is recorded as persistence. Switching copies a linked immutable shadow and does not replace or update either model's parameters.

The checkpoint factory admits only complete fingerprinted synthetic registries built from the declared generated 96-bin source. It rejects arbitrary model objects, wrong registry hashes/scopes, modified artifacts and version changes. The separate historical inventory verifies six existing selected checkpoint bundles (27 files) without loading their observations or executing a real-data evaluation. Historical feature/scaler specifications and version bytes are preserved.

Loading filters synthetic ARIMA fit observations once and bootstraps 23 history positions without duplicate adapter updates. Every replay tick calls both adapters once, including missing ticks. ARIMA advances fixed-parameter filtering and skips missing measurement correction; XGBoost uses genuine origin-relative lags [0,1,2,5,11,23] under the shared 24-bin gate. Scoring uses exact timestamps and occurs before selection/issuance; h=12 losses mature only at their exact genuine target.

Only genuine matched expert shadow errors enter ranking. Missing targets are unavailable, failed shadows have no fabricated prediction/loss, and adaptive fallback errors remain in the adaptive policy's separate accounting. Fourth-missing resets clear active supports/default incumbents once per long gap while preserving old audit records/lifetime outcomes. Old-era losses can be scored but cannot seed new-era selection.

See [integration design](../../m5b1_integration_design_v1.md) for contracts, registry admission, chronology and provenance details.

## Verification

**239 tests passed: all 205 existing tests plus 34 new integration tests**, zero failures/errors, 39.030 seconds. The exact source/configuration gate was frozen before saving these demonstrations and remains valid afterward.

New tests cover checkpoint/registry/feature/scaler hashes, controlled types, frozen settings, bootstrap, exactly one update call per tick, sequential missing-state equivalence to batch filtering, h=1/h=12 forecast purity, origin-relative features, standalone shadow/state parity through gaps and recovery, delayed/exact feedback, 99/100 support, margin/dwell and independent horizons, future-suffix invariance, gaps/reset/recovery, support expiry and old-era exclusion, numerical/update failures, parameter/version tamper rejection, immutable decisions/outcomes and shadow links, fitting prohibition, data-access isolation, output reservation and historical fingerprints. A saved-ledger audit test also rejects an altered temporary prediction.

The first fault-injection test targeted a results instance that ARIMA's update replaces. Patching the underlying inherited method also missed statsmodels' generated wrapper method. The final synthetic injection patches `SARIMAXResultsWrapper.forecast` and was explicitly checked to produce an h=1 numerical failure while h=12 remains valid. The full 239-test gate then passed. This was a fixture correction before the saved run; no selector setting, historical checkpoint or forecasting result was changed.

All **437 protected historical SHA-256 values** match before and after execution, including all prior M5A artifacts and M1–M4A history. The six selected historical checkpoints also pass their explicit 27-file audit. Existing confirmation locks remain unchanged; the new configuration keeps real-data/Alibaba training/confirmation/M5B-2/drift/interval execution false.

## Actual saved synthetic results

The fixture bank uses prescribed valid ARIMA(1,1,1) coefficients [0.4,0.2,1.0] for real filtering, and **two throwaway XGBoost C1 fits** on generated observations only. ARIMA optimization is not performed. The inherited accepted/converged fixture diagnostic is not evidence of an optimizer run. These coefficients are mechanical test inputs, not proposed research parameters. A replay fitting guard recorded **zero fit attempts** in every case.

| Scenario | Ticks / missing | h=1 / h=12 loss switches | Telemetry resets | Maximum matched support h=1 / h=12 | Final support h=1 / h=12 |
|---|---|---|---:|---|---|
| Continuous generated CPU | 420 / 0 | 0 / 1 | 0 | 288 / 288 | 288 / 288 |
| Gaps and forecast failures | 450 / 28 | 0 / 1 | 4 | 149 / 136 | 0 / 0 |
| ARIMA update failure | 180 / 6 | 0 / 0 | 1 | 40 / 40 | 0 / 0 |

The continuous h=12 switch occurs at relative replay tick **111**, exactly when its 100th pair matures. h=1 stays ARIMA. In the gap case, h=12 changes to XGBoost once, then the later telemetry reset returns it to the default with a distinct restart event; that restart is not counted as an additional loss-based switch. The trailing gaps leave zero active support despite retained lifetime outcomes.

| Scenario | h | Adaptive expert | Persistence fallback | Abstentions | Genuine scored | Missing target | Pending |
|---|---:|---:|---:|---:|---:|---:|---:|
| Continuous | 1 | 420 | 0 | 0 | 419 | 0 | 1 |
| Continuous | 12 | 420 | 0 | 0 | 408 | 0 | 12 |
| Gaps/failures | 1 | 306 | 132 | 12 | 419 | 19 | 0 |
| Gaps/failures | 12 | 307 | 131 | 12 | 409 | 24 | 5 |
| Update failure | 1 | 40 | 137 | 3 | 173 | 4 | 0 |
| Update failure | 12 | 40 | 137 | 3 | 162 | 6 | 9 |

The gap case deliberately injects one ARIMA h=1 and one XGBoost h=12 forecast failure. The update case deliberately fails one ARIMA state update at tick 40. That adapter remains invalid: all 180 tick updates are called, but only 40 filtered steps succeed, with **140 stale-state receipts** rather than fabricated current state. XGBoost continues independently. The two failed shadow attempts at the failed-update tick are consequences of that single update error, not two additional backend forecast calls. The 139 subsequent unavailable updates and their shadow attempts remain logged. No unexpected backend exception or parameter change occurred.

All saved ledgers reconcile **8,400 decisions/attempts** into **7,213 genuine scores**, **171 target-unavailable outcomes**, **90 boundary-pending forecasts**, and **926 unissued attempts**. The latter include 866 gated/failed/unavailable shadows and 60 actual policy abstentions across adaptive and persistence; they are not all service abstentions. Separate per-shadow/adaptive/persistence rows are in [availability_accounting.csv](availability_accounting.csv); [switch_support.csv](switch_support.csv) reports horizon-specific support/switch counts.

Independent saved-ledger audits pass for all **1,050 synthetic ticks**, verifying exact genuine targets, issue/arrival/score order, common contexts, checkpoint/parameter provenance, selected shadow equality, one update call per expert/tick, recomputed matched means/age/capacity, the 100-pair/margin/dwell conditions on every switch and reset/support accounting. See [ledger_verification.json](ledger_verification.json).

## Example immutable events

These values are generated fixture observations, not Alibaba measurements. Record IDs are local to each scenario.

| Scenario / relative origin | h | Adaptive record | Source/value | Exact later outcome |
|---|---:|---|---|---|
| Continuous / 111 | 12 | forecast-3168 | XGBoost / 42.014229; switch with 100 pairs | Genuine 42.419302; absolute error 0.405073 |
| Gaps / 115 | 1 | forecast-2967 | Persistence / 46.145046 after ARIMA numerical failure | Genuine 46.174468; error 0.029422 belongs to adaptive policy, not ARIMA shadow |
| Gaps / 125 | 12 | forecast-3248 | ARIMA / 41.190689 while XGBoost shadow fails | Genuine 41.765381; error 0.574691; no matched pair for that missing XGBoost forecast |
| Gaps / 233 | 1 | forecast-6097 | Abstained; fourth missing tick, support 0 | No prediction/error/pending target invented |
| Update failure / 40 | 1 | forecast-1176 | Persistence / 45.001872; filtered ARIMA cutoff remains earlier | Genuine 46.123492; error 1.121621 |

Each scenario directory contains all shadow/policy predictions, outcomes, matched pairs, selector snapshots, switches and telemetry resets, not only these examples. Synthetic UTC labels use the legacy fixture epoch in year 2000; actual artifact construction occurred on 6 November 2026 and is recorded separately in native metadata.

## Resources and access limits

Measured replay/registry-load/ledger/accounting times were **26.358 s**, **21.194 s** and **9.909 s**. Peak process RSS reported during these phases was **200.69 MiB**, below the 4 GiB per-tick guard. RSS is process-cumulative; it includes imports/native libraries and is not per-expert incremental memory. Checkpoint construction and later independent JSON audits are outside those replay timers; audit-phase peak RSS was not separately persisted. Continuous successful backend-only forecast p95 was approximately 0.985 ms for ARIMA and 8.244 ms for XGBoost; this excludes whole-tick validation, shadow inference, selection and I/O overhead.

Only generated observations and new synthetic fixture checkpoints are used by this integration. Existing regression-only prefix reads and opaque preservation hashes were the sole historical observation access, as explicitly authorized. No new Alibaba observations, development suffix, M4A outcome-based tuning, warm-up/final/confirmation values or keys were accessed. No historical model was retrained/replaced. No TensorFlow/LSTM, drift detector, intervals or dashboard was installed/implemented.

## Created files and readiness boundary

- `configs/dafr_m5b1_integration_v1.json` and `configs/dafr_m5b1_checkpoint_registry_v1.json`.
- Seven new Python modules: `adaptive_checkpoint_registry_v1.py`, `adaptive_real_contracts_v1.py`, `adaptive_real_feedback_v1.py`, `adaptive_real_streaming_v1.py`, `adaptive_real_fixtures_v1.py`, `run_m5b1_v1.py`, `audit_m5b1_v1.py`, under `src/dafr/`.
- `tests/test_dafr_adaptive_real_v1.py`: 34 new tests.
- `reports/dafr/m5b1_integration_design_v1.md`, `m5b1_preservation_v1.json`, `m5b1_backend_gate_v1.json` and `m5b2_evaluation_readiness_plan_v1.md`.
- This versioned report directory: completion/verification reports; synthetic summary, saved-ledger/preservation receipts; availability and switch/support CSVs; overwrite/final verification and new artifact inventory.
- New local ignored `data/processed/dafr/m5b1_synthetic_backend_v1/m5b1-synthetic-20261106-001/`: fixture source/registry plus two native checkpoint bundles; three scenario directories containing complete immutable manifest/event/shadow/policy/outcome/support/switch/reset/summary/completion files. Successful and failed run IDs are reserved rather than overwritten.

M5B-1 establishes backend integration mechanics, not adaptive forecasting superiority or final research readiness. The conservative unavailable-incumbent rule can prefer fallback despite a usable challenger; resets can prevent adaptation; complete-pair evidence may be sparse/conditionally biased. Long-run scaling, different machines and uncertainty behavior remain untested.

The separate [M5B-2 readiness plan](../../m5b2_evaluation_readiness_plan_v1.md) derives ideal 230-tick warm-up bounds (229/218 pairs with genuine prehistory; 206/195 without) and explains missingness/support failure, logical design availability after index 1611, inspected-development limitations and independent confirmation requirements. **M5B-2 has not begun; confirmation remains disabled.**

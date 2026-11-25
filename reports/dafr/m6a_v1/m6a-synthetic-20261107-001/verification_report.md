# M6A verification — SYNTHETIC ENGINEERING VERIFICATION ONLY

Run `m6a-synthetic-20261107-001`, 7 November 2026. **PASS for the synthetic monitoring milestone.** No real-world drift-detection or forecasting-performance conclusion follows.

## Test and preservation evidence

**315 tests passed (273 previous + 42 new), zero failures/errors, 47.338 seconds.**

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

The source-hashed gate in `reports/dafr/m6a_synthetic_gate_v1.json` pins the exact new configuration, five modules, test file and design report before saved experiments. Those eight hashes still match. No threshold, normalization rule, fixture or detector response was revised after seeing the saved alarms.

All **571 historical SHA-256 entries** match, including original M1–M5B-2 sources, models, configurations, tables, figures and immutable ledgers. An explicit selected-checkpoint check also verifies six bundles/27 files. M5B-2's unfavorable h=12 adaptive result remains unchanged. Existing regression fixtures and opaque preservation hashing are the sole historical data reads; the new detector experiments do not parse real development outcomes or use them for settings.

Actual reuse of the saved run ID was refused before synthetic generation. All **104 files then present** retained identical hashes. Automated tests also verify successful/failed ID reservation and saved-ledger tamper rejection. New reports/receipts added later are new files, not revisions of source/error/alarm ledgers.

## Acceptance checks

| Requirement | Evidence |
|---|---|
| Exact fixed reference | Only typed genuine outcomes linked to persistence/rule_v2 baseline records accepted; other policy/version/identity and unlinked predictions rejected |
| Causal normalization | First 32 current-era genuine errors only; median/MAD scale floor; frozen after prefix; hand-computed recurrence and robust-outlier normalization tests |
| Support/warnings | No warning/alarm before 64 recent genuine errors; 288-grid-target aging and bounded state; genuine zero is valid, missing targets cannot be samples |
| Independent horizons | Separate normalization/PH/support/cooldown; h=12 receives no errors before its exact target |
| Exact timing | Source issue < genuine arrival < source score < detector input/update/alert < future source issuance |
| Missingness/eras | Five-minute positions preserved; fourth missing reset once; short gaps add no residuals; old-era genuine errors audit-only; cold-start after reset |
| Alert provenance | Exact target/availability timestamp, fixed expert/version, horizon, genuine support, statistic/threshold, era, original forecast/outcome IDs and cooldown boundary |
| Cooldown | Wall-clock 24-tick suppression; support/clipping still counted; clock-only expiration verified without fabricating errors |
| Immutable behavior | Frozen snapshots/alerts/forecasts/outcomes, deterministic suffix invariance, same fixed-reference outputs as the preserved V2 source |
| No automatic actions | No selector object/callback, no refit/reselection API, zero adaptive switches and model refits |
| Failure handling | Six declared failed forecast decisions remain unissued and never acquire outcomes/errors |
| Input/output safety | New pipeline read guard excludes real data/model paths; built-in fixtures only; exclusive output directories and failure receipts |

M6A's 64-error monitor gate is a new engineering value and does not change M5A's 100 matched-pair selection requirement, source policy support scaffolding, or historical calibration settings.

## Saved ledger audits and synthetic findings

All eleven audits pass. They verify source forecast/outcome correspondence and exact arrival timing, side-ledger equality with the master event stream, genuine-only monitor inputs, alert support/threshold/source-era/cooldown, and full decision reconciliation.

Totals: **5,220 decisions = 5,013 genuine scored + 42 missing-target + 141 pending + 24 abstentions**. Twenty genuine old-era h=12 errors remain scored in source accounting but do not enter new detector normalization/support. Four telemetry-era boundaries create eight detector reset receipts. No telemetry reset is counted as a statistical alarm or selector switch.

Measured outputs are **33 statistical alarms**, **37 warning entries**, and **zero statistical false/pre-change alarms under the declared fixture labels**. Four warnings occur in outlier/short-gap controls without a sustained-change label. No warning is promoted to a concept-drift claim.

First synthetic delays are 2/2 ticks for sustained error increase, 30/12 for gradual change, and 4/2 for cooldown stress (h=1/h=12). The abrupt level step is missed at h=1 and alarms after two ticks at h=12. The early insufficient-support change is missed at both horizons because neither reaches 64 genuine errors. These misses and repeated alarms are retained. See [detection_summary.csv](detection_summary.csv) and the [completion report](completion_report.md).

These deterministic fixtures do not estimate a real-world false-alarm probability, prove concept-drift identification, establish statistical significance, justify optimized thresholds or demonstrate any DAF-R forecasting improvement. Clipping saturation and repeated alarms are limitations requiring future development evidence.

## Boundary and readiness

No new Alibaba observation, development-error analysis, warm-up/final/confirmation suffix or key is accessed by the component. No ARIMA/XGBoost fit, LSTM install/training, prediction interval or dashboard is implemented. Research locks remain unchanged and the new configuration keeps real-data execution, confirmation, model refitting, selector changes, intervals and M6B false.

Maximum recorded per-case process high-water RSS is 49.62 MiB; sum of case run times is 4.616 seconds, excluding later audits/preservation checks. The detector's working state is bounded. Audit-phase peak is not separately persisted; whole-system/production memory and latency are not established by this small capped harness.

The final new-artifact inventory excludes itself and protects all engineering reports/configuration/code and eleven saved synthetic run directories. The [M6B readiness plan](../../m6b_integration_readiness_plan_v1.md) identifies unresolved scale/threshold validity, initialization contamination, repeated-alarm/rebaselining, CPU-level channel and independent-evaluation decisions. **M6A is complete; M6B remains unstarted and unauthorized.**

# M5B-2 verification — RETROSPECTIVE DEVELOPMENT DIAGNOSTIC

Run `m5b2-retrospective-20261106-001`, completed 6 November 2026. **PASS: scoped retrospective software evaluation complete.** This verification is not independent research confirmation.

## Test gate

**273 tests passed: 239 existing plus 34 new, zero failures/errors, 45.399 seconds.**

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

The final test-log digest and exact six configuration/source/test SHA-256 values are in `reports/dafr/m5b2_replay_gate_v1.json`. All still match after the saved run. No source, threshold, window, default or switch setting was changed after examining retrospective results. Required checks passed on their first full M5B-2 gate; no unresolved error or technical blocker remains.

The completed 76-artifact M4A preflight was accepted rather than restarted. Normal per-input hash checks protect each newly loaded saved record, and the later full preservation check is the separately required historical-artifact verification.

## Acceptance evidence

| Requirement | Evidence |
|---|---|
| Authorized scope | Fixed whitelist m_505/m_1426/m_3028; exact original 460 origins per machine; only saved M4A JSON data and checkpoint metadata read by the replay |
| Source integrity/provenance | Pinned inventory chain, original prediction/event/outcome equality, exact checkpoint/version/fit-cutoff checks, canonical per-record references with path/line/run/ID/digest |
| Required shadows | Every original persistence/ARIMA/XGBoost decision exists at each origin/horizon; absent records, changed contexts or missing feedback abort rather than inventing a prediction |
| Original causal context | Exact 24-position digest reproduced from saved trailing history and current tick/quality metadata; no original CSV or filtered model state loaded |
| Cold start | Empty selector buffers, no pre-block pending predictions/errors, default ARIMA; source telemetry-era/history state carried solely for gate consistency |
| Frozen rules | Direct unchanged `MatchedSelectorV1.choose()` and original clock/reset/aging routine; exact original configuration SHA and numeric setting equality |
| Feedback timing | Exact target arrival only; premature/shifted/duplicate/missing outcomes rejected; h=12 support empty before its first matured target |
| Matched evidence | Only both genuine expert-issued errors at identical origin/target/horizon/context/era; fallback/policy errors never used to rank experts |
| Independent horizons/support | Separate 99/100 boundaries, dwell/margin checks, 288-tick aging/capacity and horizon-specific switches |
| Missingness | Null missing-target errors, age-three persistence, explicit abstention, fourth-missing reset, old-era exclusion and 24-genuine recovery; long-gap mechanisms tested synthetically |
| No future leakage | Unrevealed future values/masks/forecasts cannot change prefix decisions; first state mutation follows all input/provenance validation |
| Immutable outputs | Frozen decisions/outcomes, exact source links, append-only event records, boundary-pending reconciliation and saved-artifact tamper rejection |
| Metrics | Identical genuine target intersections for four policies; expert-only/complete scopes distinct; equal-machine macro means; independent recomputation of all matched per-machine MAE/RMSE |
| Historical preservation | 505 prior file hashes match, including prior M5A/M5B-1 and historical forecasts/checkpoints/configurations; explicit six-bundle/27-file selected checkpoint check |
| Output protection | Actual existing-run attempt refused before source loading; all 54 files then present remain hash-identical; automated no-overwrite test also passes |

## Independent audit and reconciliation

The auditor does not call the selector or replay. It independently reconstructs the rule using archived genuine expert errors, independently maintains support/expiry/reset/dwell/incumbent state, and checks every emitted snapshot/decision. It confirms exact source copying, source version/context, both comparison scopes, future-boundary handling and event order. Independent audit means a separate software verification path, not independent test data.

| Machine | Adaptive decisions | Genuine scores | Missing targets | Pending | Abstentions | h=1/h=12 switches |
|---|---:|---:|---:|---:|---:|---|
| m_505 | 920 | 903 | 4 | 13 | 0 | 0 / 2 |
| m_1426 | 920 | 905 | 2 | 13 | 0 | 0 / 1 |
| m_3028 | 920 | 905 | 2 | 13 | 0 | 0 / 0 |
| Total | 2,760 | 2,713 | 8 | 39 | 0 | 0 / 3 |

Every decision is accounted for. All missing targets remain unscored; all targets beyond source index 1611 remain pending. No original warm-up/final observation is read to finish them. There are no real-data telemetry resets, numerical model failures or new predictions generated in this replay; original unavailable/history-gated issuance and valid fallback are preserved. Synthetic tests separately verify long-gap failure behavior.

All six streams eventually have at least 100 matched pairs and eligible history/availability/dwell. That does not guarantee a switch: h=1 and m_3028 h=12 never satisfy the required challenger improvement. Exact switch/support details are in [support_switching.json](support_switching.json), [switch_events.csv](switch_events.csv) and the [support analysis](support_switching_analysis.md).

## Preserved unfavorable finding

At h=1, adaptive expert-matched macro MAE/RMSE equals fixed ARIMA at **3.901195 / 5.104576**. At h=12, adaptive is **6.896834 / 8.827642**, worse than fixed ARIMA's **6.797972 / 8.788959**. Complete-policy comparisons show the same direction. These measured errors and the unfavorable m_505 result are retained unchanged. No threshold search or rerun with modified settings occurred.

M4A was inspected before the adaptive design existed. The recorded policy is a computationally causal retrospective reconstruction, not a historically deployed policy or unbiased independent estimate. Every metric table/plot and new result ledger is labeled RETROSPECTIVE DEVELOPMENT DIAGNOSTIC.

## Access, resource and stopping checks

The new pipeline parses only approved saved M4A JSON records, original checkpoint metadata and integrity manifests. Trailing saved reconstruction ticks prime context only. Existing regression fixtures and opaque historical byte hashing remain the only other previously approved observation access. Original Alibaba archives/tables, development suffix containers, warm-up [1612,1842), final [1842,2304), confirmation machines and encryption keys are not opened by this evaluation. No models are instantiated, trained, refitted or used for new inference.

The new execution configuration keeps confirmation, new observation access, training and M6/M7/M8 false. Old execution locks, all old weights/scalers/features and all old reports/ledgers remain unchanged. No M6 detector, M7 interval, LSTM/TensorFlow or dashboard work occurred.

Runtime JSON records 32.721 seconds including input loading, replay logs, plot/table generation and independent audits before the final historical recheck; peak process RSS is 195,379,200 bytes (186.33 MiB), below the 4 GiB replay guard. Replay plus ledger I/O alone takes approximately 0.82–0.84 seconds per machine. These are archive-replay costs without live forecasting. All eleven PNGs decode successfully; representative aggregate, support and forecast/error figures were visually reviewed. No plotting failure remains.

The final artifact inventory covers all new engineering files, report tables/figures/documents and immutable private run outputs, excluding its own bytes to avoid a circular hash. The [completion report](completion_report.md) lists deliverables and measured results; [future recommendations](m6_and_independent_evaluation_recommendations.md) do not authorize another milestone or any new data access. **M5B-2 is complete and stops here.**

# M5A synthetic demonstrations and accounting

Run group `m5a-synthetic-20261031-001`, 31 October 2026. Every CPU value and expert forecast is synthetic deterministic arithmetic. Expert names denote registered lifecycle mocks, not real ARIMA or XGBoost inference. No real-data adaptive accuracy claim is made.

## Prespecified fixtures and observed mechanics

| Fixture | Grid ticks | h=1 switches | h=12 switches | Telemetry resets | Final matched support h=1 / h=12 |
|---|---:|---:|---:|---:|---:|
| Stable constant 40 | 400 | 0 | 0 | 0 | 288 / 288 |
| Constant → alternating 32/48 → constant | 900 | 2 | 0 | 0 | 288 / 288 |
| Linear ramp 20 + 0.15 × tick | 400 | 0 | 1 | 0 | 288 / 288 |
| Leading/short/long/trailing gaps and declared failures | 600 | 0 | 0 | 3 | 0 / 0 |

The alternating fixture changes at indices 250 and 500. Its h=1 incumbent changes ARIMA→XGBoost at index **261** (238 matched pairs) and XGBoost→ARIMA at **780** (288 pairs). This illustrates that a long rolling window can retain old evidence and delay recovery; the settings were not shortened afterward. Its h=12 incumbent remains ARIMA. These workload changes are known fixture construction, not detected concept drift.

On the ramp, h=12 switches to XGBoost at index **134**, exactly when its 100th genuine matched pair arrives. h=1 stays ARIMA, demonstrating independent horizons. On an all-genuine stream, the first expert origin is 23, so the first possible 100-pair decision is tick **123** at h=1 and **134** at h=12. CPU targets are always exact future five-minute bins.

The gap fixture has leading missing indices 0–1, a one-tick gap at 100, three ticks 200–202, six ticks 300–305, four ticks 450–453 and trailing ticks 590–599. Fourth-missing resets occur at **303,453,593**, once per long gap. Its two deliberately injected ARIMA numerical forecast failures occur at 150/151, h=1; XGBoost is deliberately unavailable at 160, h=12. Successful expert versions and parameters remain fixed. No unexpected numerical failure occurred.

## Actual adaptive-policy availability

Counts below are per horizon. Fallback predictions are actual persistence centers and are not counted as genuine shadow expert predictions or expert-ranking errors.

| Fixture | h | Expert predictions | Persistence fallback | Abstentions | Genuine scored | Missing target | Boundary pending |
|---|---:|---:|---:|---:|---:|---:|---:|
| Stable | 1 | 377 | 23 | 0 | 399 | 0 | 1 |
| Stable | 12 | 377 | 23 | 0 | 388 | 0 | 12 |
| Alternating episode | 1 | 877 | 23 | 0 | 899 | 0 | 1 |
| Alternating episode | 12 | 877 | 23 | 0 | 888 | 0 | 12 |
| Ramp | 1 | 377 | 23 | 0 | 399 | 0 | 1 |
| Ramp | 12 | 377 | 23 | 0 | 388 | 0 | 12 |
| Gaps/failures | 1 | 457 | 130 | 13 | 571 | 16 | 0 |
| Gaps/failures | 12 | 459 | 128 | 13 | 558 | 24 | 5 |

For each row: expert + fallback + abstention = grid ticks; scored + missing-target + pending = expert + fallback. Complete per-shadow, adaptive and persistence accounting, including gated/unavailable/numerical attempts, is in [availability_accounting.csv](availability_accounting.csv). Shadow forecasts have **no persistence fallback**: unsuccessful shadow attempts stay null and never create a fabricated expert loss. The gap fixture's final support is zero despite earlier reaching 220 matched pairs; the trailing long gap clears and ages active evidence instead of preserving stale confidence.

Across all four fixtures, **18,400 decisions/attempts** reconcile as 17,197 genuine scored forecast-target pairs, 138 target-unavailable outcomes, 170 boundary-pending forecasts and 895 unissued attempts. Unissued attempts include gated/failed shadows and actual policy abstentions; they are not all service abstentions. These repeated expert/policy records are not independent CPU observations.

Lifetime matched pairs h=1/h=12: stable 376/365; alternating episode 876/865; ramp 376/365; gaps/failures 452/432. Lifetime counts include auditable old-era pairs; only same-era recent pairs enter active selection. No unmatched easier subset is used to make an expert appear better.

## Examples from the immutable synthetic ledger

Identifiers are local to each scenario's run. Indices refer to five-minute grid ticks beginning synthetic UTC 1 January 2026 at 00:00.

| Fixture / origin | h | Adaptive record | Issuance | Selected source / value | Later exact-target outcome |
|---|---:|---|---|---|---|
| Ramp / 134 | 12 | forecast-3578 | Expert; first supported switch | XGBoost mock / 42.05 | Index 146 genuine 41.9; absolute error 0.15 |
| Alternating episode / 261 | 1 | forecast-7131 | Expert switch | XGBoost mock / 38.916667 | Index 262 genuine 32; error 6.916667 |
| Alternating episode / 780 | 1 | forecast-21664 | Expert switch back | ARIMA mock / 40 | Index 781 genuine 40; error 0 |
| Gaps / 88 | 12 | forecast-2269 | Expert | ARIMA mock / 40 | Index 100 missing; null actual/error |
| Failure / 150 | 1 | forecast-3856 | Persistence fallback | Persistence / 40 | Index 151 genuine 40; policy error 0, not an ARIMA shadow error |
| Long gap / 303 | 1 | forecast-7963 | Abstention, new era | None / null | No forecast to score; no pending record |
| Recovery / 329 | 1 | forecast-8545 | Expert after 24 genuine bins | ARIMA mock / 40 | Index 330 genuine 40; error 0; selector support still zero at issuance |

For ramp origin 134, h=12, the ARIMA shadow is **40.1**, the XGBoost shadow **42.05**; both were issued before target 146 arrived. The adaptive record links the XGBoost shadow ID and copies exactly 42.05. Both shadows later get their own genuine loss (1.8 and 0.15); the adaptive policy gets its actual issued-center loss. This demonstrates provenance and delayed feedback, not expected real-model performance.

Telemetry reset, era-default restart, and loss-based expert switch have different ledger kinds. There are three telemetry resets and six horizon-specific era-default restart records in the gap fixture; these are not counted among the three loss-based switches. No drift alert is emitted and no drift detector is instantiated.

## Full local records and reproduction

For each scenario, all shadow predictions and unissued attempts are in:
`data/processed/dafr/m5a_synthetic_v1/m5a-synthetic-20261031-001-<scenario>/shadow_predictions.jsonl`.

All actual adaptive/persistence decisions are in `policy_predictions.jsonl`. The same directory contains `events.jsonl`, `outcomes.jsonl`, `matched_losses.jsonl`, `selector_states.jsonl`, `switches.jsonl`, `resets.jsonl`, manifest, summary and completion receipt. These are exclusively created and never rewritten; their parent remains ignored by Git.

The ledger audit independently recomputes matched means/support bounds, checks 100-pair and margin/dwell conditions on every switch, verifies identical causal contexts, exact target joins and score arithmetic, and reconciles all decisions. [ledger_verification.json](ledger_verification.json) records all four successful audits.

Reproduce one built-in scenario with a **new** ID:

```bash
PYTHONPATH=src .venv/bin/python -m dafr.selector_streaming_v1 --run-id m5a-NEW-ID --scenario horizon_divergence
```

No CLI accepts a dataset filename, checkpoint, confirmation source, model optimizer or tunable selector thresholds. M5A execution does not authorize real-data selection experiments.

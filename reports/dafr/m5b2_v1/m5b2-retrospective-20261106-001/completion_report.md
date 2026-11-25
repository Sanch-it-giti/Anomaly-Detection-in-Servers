# M5B-2 completion — RETROSPECTIVE DEVELOPMENT DIAGNOSTIC

Completed 6 November 2026. Run `m5b2-retrospective-20261106-001`. **M5B-2 is complete.** This is a development-only retrospective diagnostic of the frozen M5A algorithm on archived M4A forecasts, not an independent test or demonstrated DAF-R improvement.

## Measured result

**Adaptation equals fixed ARIMA at h=1 and performs worse than fixed ARIMA at h=12**, on both expert-only matched errors and complete-policy matched errors. No setting was altered after observing these results. Three switches occurred, all at h=12.

Equal-machine macro MAE / RMSE, CPU percentage points, on identical genuine expert-matched origin/target sets:

| Policy | h=1: five minutes | h=12: sixty minutes |
|---|---:|---:|
| Persistence | 4.125690 / 5.424773 | 7.133119 / 9.324500 |
| Fixed ARIMA | 3.901195 / 5.104576 | 6.797972 / 8.788959 |
| Fixed XGBoost | 4.396641 / 5.801670 | 6.937706 / 9.025295 |
| Frozen adaptive | 3.901195 / 5.104576 | 6.896834 / 8.827642 |

Common expert-matched target counts are **1,297 at h=1** (429,434,434) and **1,272 at h=12** (417,432,423), in machine order m_505,m_1426,m_3028. Macro RMSE is the arithmetic mean of three per-machine RMSEs, not pooled RMSE. h=12 targets remain exact five-minute bin means ending sixty minutes after the origin, not an average over the next hour.

Complete-policy comparisons include the actual persistence fallback centers, with identical target support across all four policies in this block:

| Policy | h=1 MAE / RMSE | h=12 MAE / RMSE |
|---|---:|---:|
| Persistence | 4.120591 / 5.438665 | 7.140607 / 9.347145 |
| Fixed ARIMA with fallback | 3.908631 / 5.138632 | 6.823330 / 8.841859 |
| Fixed XGBoost with fallback | 4.377595 / 5.804142 | 6.953960 / 9.069516 |
| Frozen adaptive with fallback | 3.908631 / 5.138632 | 6.915697 / 8.876146 |

Complete common counts are **1,373 at h=1** and **1,340 at h=12**. Expert-only and complete-policy rows are separate scopes in [comparisons.csv](comparisons.csv) and [macro_comparisons.csv](macro_comparisons.csv); each also reports the policy's own genuine support rather than hiding availability losses.

## Per-machine expert-matched errors

All rows below are RETROSPECTIVE DEVELOPMENT DIAGNOSTIC results on shared exact target sets; errors are MAE / RMSE in CPU percentage points.

| Machine | h | Common n | Persistence | ARIMA | XGBoost | Adaptive |
|---|---:|---:|---:|---:|---:|---:|
| m_505 | 1 | 429 | 4.026449 / 5.336539 | 3.765395 / 4.921844 | 3.941375 / 5.090962 | 3.765395 / 4.921844 |
| m_505 | 12 | 417 | 6.442680 / 8.499691 | 6.069862 / 7.915405 | 6.165309 / 7.879401 | 6.372762 / 8.040037 |
| m_1426 | 1 | 434 | 4.343090 / 5.858206 | 4.205338 / 5.595001 | 4.536271 / 6.026882 | 4.205338 / 5.595001 |
| m_1426 | 12 | 432 | 7.923529 / 10.460706 | 7.695167 / 9.835368 | 7.510281 / 9.705130 | 7.688853 / 9.826784 |
| m_3028 | 1 | 434 | 4.007533 / 5.079574 | 3.732851 / 4.796884 | 4.712277 / 6.287166 | 3.732851 / 4.796884 |
| m_3028 | 12 | 423 | 7.033149 / 9.013103 | 6.628887 / 8.616105 | 7.137528 / 9.491354 | 6.628887 / 8.616105 |

The unfavorable h=12 macro difference comes mainly from m_505: adaptive MAE is about 0.302900 points higher than fixed ARIMA, outweighing a small m_1426 reduction. The expert-matched macro difference is **+0.098862 MAE / +0.038683 RMSE**; the complete-policy macro difference is **+0.092367 / +0.034287**. These are descriptive differences on this inspected period, without a significance or generalization claim.

## Frozen replay and scope

The prior integrity preflight was accepted and not restarted wholesale. The new reader verifies each consumed artifact against its existing pinned hash as it loads it. Inputs are only archived M4A JSON artifacts for the three original development machines, with issuance origins **[1152,1612)**. No original Alibaba table/CSV or new observation block is read by this replay.

Trailing 23 ticks from the already-saved M4A reconstruction ledger restore the original history context; verified issue-time quality/era metadata restores its exact digest. No model is loaded or updated. The original gate, fallback, missing-target semantics and fixed model versions are retained. Context hashes match the archived records at every origin for every expert. No new historical prediction is invented.

Each selector starts at ARIMA with **empty loss buffers and no pre-block pending forecasts**. Existing M4A error/support counters are not imported. After each recorded tick, only previously issued forecasts whose exact target has now arrived can mature. Ranking uses matched, genuine, expert-issued ARIMA/XGBoost errors only. Fallback errors never masquerade as expert losses. Old-era outcomes remain auditable but cannot seed new-era support.

The unchanged `MatchedSelectorV1` performs the actual choice. Its clock/reset/aging routine is advanced with no mock outcomes; the separately validated current-target pairs are inserted into the same bounded buffers before the unchanged `choose()` method runs. Inserting these current-target pairs after age expiry is equivalent to insertion before expiry because they cannot already be stale. No M5A contract or scientific rule was weakened or edited.

Rules remain default ARIMA, minimum **100 pairs**, maximum **288 pairs**, **288 elapsed target ticks** of recency, **24-tick dwell**, improvement **max(0.1 points,5%)**, deterministic incumbent-retaining ties, independent horizons, 24 genuine input bins, age-three persistence and fourth-missing telemetry reset. New decisions link to an existing immutable expert forecast or persistence reference. Later outcomes link back to that same source and never revise a decision.

The algorithm/default was designed after M4A was inspected through index 1611. New manifests explicitly mark the exercise retrospective and record that later design availability. Computationally causal replay does not imply the policy was deployed or designed before the historical origins. Source UTC dates are artificial event coordinates inherited from the Alibaba preprocessing epoch, not actual experiment execution dates.

## Support, switching and availability

All six machine/horizon streams eventually meet the 100-pair minimum and become eligible to consider a challenger under the history/dwell rules. h=1 never meets the required improvement margin, so it remains exactly the fixed ARIMA policy. See [support and switching analysis](support_switching_analysis.md), [support_summary.csv](support_summary.csv) and [switch_events.csv](switch_events.csv) for readiness, age expiry and every switch.

Adaptive issuance counts per machine, separately at each horizon:

| Machine | Expert | Persistence fallback | Abstention | Genuine h=1 / h=12 targets | Missing h=1 / h=12 targets | Pending h=1 / h=12 |
|---|---:|---:|---:|---|---|---|
| m_505 | 431 | 29 | 0 | 457 / 446 | 2 / 2 | 1 / 12 |
| m_1426 | 436 | 24 | 0 | 458 / 447 | 1 / 1 | 1 / 12 |
| m_3028 | 436 | 24 | 0 | 458 / 447 | 1 / 1 | 1 / 12 |

The 2,760 new adaptive decisions reconcile as **2,713 genuine scores + 8 missing-target outcomes + 39 boundary-pending predictions**, with zero abstentions. Fallback totals 77 per horizon. Fixed policies and persistence retain their original availability and scores. All pending targets remain unscored; no warm-up observation is opened to resolve them. The block has only four isolated missing bins, so there is **no real-data telemetry reset** or long-gap abstention; those mechanisms are exercised by synthetic tests.

## Verification, resources and files

**273 tests passed: all 239 prior tests plus 34 new tests**, zero failures/errors, 45.399 seconds. Tests cover scope/locks, original context reconstruction, no pre-block support, exact targets, delayed h=12 feedback, 99/100 boundaries, horizon separation, future-suffix invariance, missing/premature feedback, source/version/context/reference tampering, genuine-only matching, pending/abstention behavior, frozen records, matched metrics/macro weights, dataset-read isolation, output protection, saved-audit tampering, and synthetic long gaps/reset/recovery/support expiry.

Independent audits do not invoke the selector/replay. They reconstruct matched support, means, expiry, timers, switch rules, source linkage and exact-target accounting, and independently recompute all per-machine matched MAE/RMSE values. Every audit passes. All **505 protected historical hashes**, including M1–M5B-1, match. Selected checkpoint fingerprints and M5A source/configuration remain unchanged. The full [verification report](verification_report.md) records preservation and output checks.

Measured execution took **32.721 seconds**, including input loading, replay logs, eleven plots, independent audits and table generation before the final historical hash recheck. Per-machine replay with ledger I/O took 0.828,0.838,0.817 seconds. Peak process RSS recorded was **186.33 MiB**, below the 4 GiB replay guard. These costs exclude model inference/training because none occurs here. They must not be interpreted as live DAF-R inference latency. The temporary matplotlib font cache was built successfully; no plotting error remains.

Created engineering files:

- `configs/dafr_m5b2_retrospective_v1.json`.
- `src/dafr/retrospective_sources_v1.py`, `retrospective_replay_v1.py`, `run_m5b2_v1.py`, `audit_m5b2_v1.py`.
- `tests/test_dafr_retrospective_v1.py` (34 new tests).
- `reports/dafr/m5b2_preservation_v1.json` and `m5b2_replay_gate_v1.json`.
- This versioned report directory: complete comparison/macro/availability/support/switch CSV and JSON tables, aggregate plots, independent audit/runtime/preservation receipts, completion/support/verification/recommendation documents, final verification and artifact hashes.
- Local ignored `data/processed/dafr/m5b2_retrospective_v1/m5b2-retrospective-20261106-001/`: execution/completion manifests plus three machine directories containing source manifests, immutable event/decision/outcome/selection/matched-loss/switch/reset ledgers, pending summaries, and nine private forecast/error/support plots. Public figures contain aggregate statistics; machine traces remain in ignored local outputs.

No model training/refitting, threshold search, new data access, confirmation unlock, M6 drift detector, M7 intervals or M8/dashboard work occurred. [Recommendations](m6_and_independent_evaluation_recommendations.md) describe future work without authorizing it. **Stop after M5B-2.**

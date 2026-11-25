# M5A completion — causal adaptive selection design and synthetic verification

Completed 31 October 2026. Run group `m5a-synthetic-20261031-001`. **Ready for review; stop after M5A.**

## Result and frozen rules

Implemented a separately versioned hard selector and synthetic driver using deterministic registered ARIMA/XGBoost lifecycle mocks only. Initial expert is ARIMA, informed only by earlier aggregate development evidence. No M4A ledger was parsed for selector design or tuning, and no adaptive strategy was evaluated on real CPU data.

Independent h=1/h=12 buffers compare **identical genuine shadow origin/target/era/context pairs**, using mean absolute errors. Each buffer retains at most **288 pairs** with targets no older than **287 elapsed ticks**. A loss-based switch needs **100 matched pairs**, **24 elapsed grid ticks of dwell**, and improvement at least **max(0.1 CPU percentage points, 5% of incumbent loss)**, allowing 1e−12 arithmetic tolerance. Ties retain incumbent. These are frozen engineering choices, not empirically optimized thresholds.

Both current shadows must be available to switch. An unavailable incumbent keeps its identity and uses persistence fallback, rather than forcing an unsupported alternate expert. Insufficient support holds the incumbent. Original 24-consecutive-genuine history, age-three persistence, explicit stale/no-history abstention and exact missing-target rules remain unchanged.

At the fourth consecutive missing tick, one telemetry era begins. Active loss/policy support clears; incumbents restart at ARIMA and dwell restarts, recorded separately from loss-based switches. Old records and lifetime outcomes remain intact; old-era scores cannot seed new-era support. Shadow errors, matched comparison support, actual adaptive errors including fallback, and persistence errors are separate. No drift detector, interval calibration or reliability gate is implemented.

The [design document](../../m5a_selector_design_v1.md) explains event order, cutoffs, ties, failures, reset timing and the deliberate bounded-window amendment to the original provisional exponentially weighted-loss proposal. It does not change the original research protocol or approve final settings.

## Tests and synthetic findings

**205 tests passed: all 166 existing tests plus 39 new M5A tests**, zero failures/errors, 22.395 seconds. The source-hashed execution gate was then frozen before the saved demonstrations. No gated source/configuration changed afterward.

Tests cover future-data perturbation invariance, exact h=1/h=12 targets and delayed feedback, 99-versus-100 pair warm-up, matched versus selective evidence, cold start, deterministic ties, absolute/relative hysteresis, 23-versus-24 tick dwell, insufficient support after selection, missing targets, numerical and update failures, fallback/stale abstention, recovery/eras, old-era accounting, 288-score capacity/age expiry, shared contexts, immutability, invalid inputs, no real-data/model reads by the selector, duplicate decisions/feedback, output protection, historical hashes and an independent saved-ledger audit including tamper rejection.

An initial selective-availability fixture inherited an h=12-only fault setting while its assertion intended both horizons. The fixture was corrected to explicitly target both horizons; the complete gate was rerun. No selector threshold was changed in response to that failure or to demonstration results.

Four predefined synthetic fixtures yielded:

| Fixture | Ticks | h=1 switches | h=12 switches | Telemetry resets |
|---|---:|---:|---:|---:|
| Stable | 400 | 0 | 0 | 0 |
| Alternating episode | 900 | 2 | 0 | 0 |
| Linear ramp | 400 | 0 | 1 | 0 |
| Gaps and failures | 600 | 0 | 0 | 3 |

The ramp's h=12 first switch occurs at its 100th matched target (tick 134), while h=1 retains ARIMA. The alternating fixture eventually switches back after old evidence ages, illustrating window lag. Gaps/failures produce honest fallback/abstention and erase active support on resets; zero support at the end does not imply zero lifetime outcomes.

Independent saved-ledger checks pass for all **2,300 synthetic grid ticks** and **18,400 decisions/attempts**: 17,197 genuine scored outcomes, 138 unavailable exact targets, 170 boundary-pending forecasts and 895 unissued attempts. All actual expert policy centers link to identical immutable shadows. Fallback losses never enter expert ranking. Both selected-policy and all shadow records are preserved. These counts demonstrate mechanics, not adaptive forecasting improvement or drift-detection accuracy. Detailed switches, support, source predictions and fallback counts are in [synthetic_demonstration.md](synthetic_demonstration.md) and [availability_accounting.csv](availability_accounting.csv).

## Preservation, access and resources

All **374 protected historical SHA-256 values** match before and after the demonstrations, including M1–M4A source/configuration/reports/output inventories and fitted checkpoint fingerprints. [Preservation verification](preservation_verification.json) links the baseline inventory. Real ARIMA/XGBoost artifacts were not loaded by this new synthetic driver or refitted.

The user separately approved existing regression-only prefix fixture reads and opaque historical-ledger hashing. Those old fixture reads are confined to the existing suite; preservation hashing does not parse historical values. M5A's selector and demonstrations read configuration and built-in synthetic inputs only. No new Alibaba development period, M4A outcome-based selector tuning, calibration/warm-up, final evaluation, confirmation suffix or encryption key was accessed. Historical configuration bytes and confirmation locks remain unchanged; the new synthetic configuration also keeps real-data execution/training/confirmation/M5B false.

Measured demonstration times (including synthetic ledger writing and accounting, excluding each later independent audit) were stable **2.676 s**, alternating **5.726 s**, ramp **2.518 s**, gaps **3.433 s**. Peak RSS reported during the runs was **194.58 MiB**, below the 4 GiB guard. It is process-cumulative and includes memory retained/high-water usage from preceding synthetic audits; it is not per-expert memory. Initial stable-run peak was 25.95 MiB. Working history/loss buffers remain bounded; this small pilot retains the capped-run audit ledger in memory. The runner checks RSS before each tick, not system-wide memory or future real-model deployment latency. No dependency was installed.

Reusing existing output IDs is rejected. Successful and failed run preservation is automated-tested; an actual run-group overwrite attempt and file hash audit are recorded separately. Unexpected model/provenance errors are not hidden as favorable missing losses. The only numerical failures in the saved runs were declared synthetic injections.

## Created files

- `configs/dafr_m5a_synthetic_v1.json`: frozen synthetic-only execution and selector choices.
- `src/dafr/selector_contracts_v1.py`: immutable matched-loss, selection, adaptive/shadow forecast and audit contracts.
- `src/dafr/selector_v1.py`: matched feedback, bounded horizon-specific state, hysteresis and dwell.
- `src/dafr/selector_streaming_v1.py`: separate synthetic integration/ledger, missing events, mock lifecycle, policy issuance and exclusive output writer.
- `src/dafr/run_m5a_v1.py`: gated demonstrations, independent saved-ledger checks and opaque preservation hashes.
- `tests/test_dafr_selector_v1.py`: 39 synthetic and preservation tests.
- `reports/dafr/m5a_selector_design_v1.md`, `m5a_preservation_v1.json`, `m5a_synthetic_gate_v1.json`.
- This versioned report directory: completion, demonstration and preservation/verification reports, combined synthetic summaries, ledger verification, switch/support/availability accounting, overwrite check, final verification and new artifact inventory.
- Four new local ignored run directories under `data/processed/dafr/m5a_synthetic_v1/`, each with eleven immutable manifest/ledger/summary/completion files. Historical outputs are untouched.

## Limitations and next boundary

The mocks and designed workloads are mechanical tests. They establish no forecast-accuracy gain, optimal thresholds, concept-drift detection or real-data selector stability. Matched complete-pair evidence prevents unequal-subset comparisons but can be sparse or conditionally biased under informative failures/missingness. The conservative unavailable-incumbent rule may use fallback despite a usable challenger; that cost is deliberate and visible. The 288-pair window can react slowly; resets can prevent 100-pair warm-up; high switch costs or larger banks are untested.

The new synthetic driver has no path for real artifacts, training, LSTM, drift detection, intervals, or a dashboard. No real-model adaptive integration or confirmation research protocol is approved here. The engineering foundation is ready for **a separately scoped M5B design/review**, which must decide real-adapter integration, permitted development evidence and an independently defensible future evaluation plan. **M5B has not begun.**

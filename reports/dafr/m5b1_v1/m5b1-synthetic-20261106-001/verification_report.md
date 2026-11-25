# M5B-1 complete verification report

6 November 2026. Run `m5b1-synthetic-20261106-001`. Result: **PASS for synthetic real-backend integration; no real-data evaluation authorization.**

## Tests and frozen execution gate

**239 tests passed (205 prior + 34 new), zero failures/errors, 39.030 seconds.**

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

`reports/dafr/m5b1_backend_gate_v1.json` records the test-log SHA and the exact ten configuration/source/test file hashes used for the saved demonstration. They still match. Synthetic ARIMA fault targeting was corrected before this final gate to intercept statsmodels' generated results-wrapper method, which survives creation of a newly filtered results instance. No research threshold or old artifact changed.

## Acceptance evidence

| Requirement | Verified evidence |
|---|---|
| Controlled real types | Registry references only; exact registered ARIMA/XGBoost `RealAdapter` types; arbitrary object/type/scope rejection tests |
| Complete checkpoint provenance | Metadata, weights/parameters, features, identity scaler, fit/source/generator, version and loaded parameter hashes verified before admission and after saved replay |
| Historical preservation | All 437 historical SHA-256 entries match; six selected historical bundles/27 files pass explicit fingerprint checks |
| Unchanged scientific rules | M5A configuration SHA and exact selector/missingness dictionary equality; direct inheritance of the unchanged M5A `choose` method |
| Bootstrap and chronological updates | Fit state filtered once, 23 history positions bootstrapped without model updates; first replay tick strictly follows the checkpoint; one update call per expert per tick |
| Standalone equivalence | Bit-identical successful synthetic shadow values and state digests versus equivalent standalone real-backend runs, including missing positions and recovery |
| Missing ARIMA transition | Sequential filtered state matches full fixed-parameter batch filtering; missing measurement correction skipped |
| Genuine XGBoost inputs | Actual booster predictions equal explicitly constructed origin-relative [0,1,2,5,11,23] features; common 24-genuine gate retained |
| Forecast purity | Both horizons leave parameter/state fingerprints unchanged; selected centers copy linked shadows exactly |
| No future leakage | Suffix perturbation invariance, exact origin/target matching, delayed h=12 feedback and pre-mutation version/parameter checks |
| Fair adaptive feedback | Only matched genuine expert shadows rank models; policy fallback errors, unmatched losses, missing targets and failed attempts cannot enter ranking |
| Adaptive conditions | 99/100-pair gate, absolute/relative margin and elapsed dwell tests; independent horizons; all saved switches independently rechecked |
| Missingness/eras | Age-three fallback/stale abstention, genuine-window recovery, fourth-missing reset once, old-era outcome retention/exclusion and grid-based support expiry |
| Failures | Declared numerical forecast failures and invalid-update latch, honest unavailable/stale provenance, continued independent expert updates; no hidden refit |
| Immutable records | Frozen forecast/outcome objects; append-only linked records; duplicate/revision protection and saved-prediction tamper rejection |
| Output protection | Automated successful/failed ID reservation; actual run reuse rejected before fixture build; all 50 then-existing new-run files hash-identical |
| Data boundary | New driver uses generated synthetic fit/replay values only; no data/model path read in the isolation test; historical reads restricted to approved regression fixtures and opaque hashing |

## Saved-ledger reconciliation

Three independent audits parse only the new synthetic ledgers. The audit rechecks the original five-minute tick/value/missingness fixture; correct gate/input age; issue < target arrival < score < current state order; exact target/horizon links; null missing errors; native checkpoint/version/parameter links; selected shadow equality; common contexts; matched support age/capacity/means; 100-pair, margin and dwell conditions; reset and update accounting.

| Scenario | Ticks | Decisions/attempts | Genuine scores | Missing exact targets | Boundary pending | Unissued attempts |
|---|---:|---:|---:|---:|---:|---:|
| Continuous | 420 | 3,360 | 3,308 | 0 | 52 | 0 |
| Gaps/forecast failures | 450 | 3,600 | 2,820 | 144 | 14 | 622 |
| Update failure | 180 | 1,440 | 1,085 | 27 | 24 | 304 |
| Total | 1,050 | 8,400 | 7,213 | 171 | 90 | 926 |

Every decision reconciles. Unissued attempts include both unavailable/gated shadows and actual policy abstentions; shadow attempts are not mislabeled service abstentions. Two loss-based switches occurred, both at h=12, independently of five telemetry resets and ten horizon-specific default-restart events. No drift detector or drift alert exists.

Exactly 1,050 update calls per expert were made across the cases. While valid, every genuine/missing observation advances ARIMA filtering on its original grid. In the deliberate update-failure case, ARIMA processes each subsequent tick/history position but reports invalid/stale filtered state instead of pretending successful assimilation: 140 stale receipts, one numerical update failure, 139 subsequent unavailable updates. The actual filtered-state cutoff remains its last successful time; XGBoost continues normally. The two immediately blocked shadow attempts are consequences of that one update failure, not additional backend forecast calls.

The two actual injected forecast failures occur in the gap case. Their unissued shadows never acquire losses, while the adaptive policy retains its true selected/fallback center and corresponding error. No unexpected failure occurred. All parameters remained fixed; streaming fitting guards recorded zero attempts.

## Checkpoint and dataset scope

The saved fixture bank contains a 96-value generated source, ARIMA known-parameter filtered checkpoint and two native XGBoost direct-horizon fits. No ARIMA optimizer is run. Synthetic source hashes and `scope=synthetic_backend_test` distinguish these from preserved historical research checkpoints; the inherited legacy `RealVersion` loader label is retained rather than used to claim Alibaba training. Only the new synthetic registry is executable in this milestone.

No new Alibaba observations/development suffix/calibration/warm-up/final/confirmation values or keys were accessed. Existing 205-test regression fixture reads and historical byte hashing remain the only real-data reads, explicitly allowed by the request. The new selector never parses M4A outcomes for tuning. Historical registry checks read checkpoint bytes only; no original suffix container is rehashed, and no sealed payload is opened.

Real-data execution, Alibaba training, confirmation, M5B-2, drift and prediction-interval flags remain false. No old configuration lock changed. No TensorFlow/LSTM or dashboard work occurred.

## Resources, limitations and readiness

Replay phases took 26.358,21.194,9.909 seconds, with cumulative process high-water RSS 200.69 MiB recorded before the independent audit phase, below the 4 GiB replay guard. Later JSON-audit peak RSS was not separately persisted. Small capped histories/support are lightweight, but full synthetic audit records remain in memory under the 2,304-tick cap; production storage/scaling is not established.

Synthetic switches and losses demonstrate implementation mechanics only. They do not prove adaptive superiority, optimized thresholds, drift robustness, interval calibration or generalization. Conservatively retaining an unavailable incumbent can force persistence despite a valid challenger; frequent resets can prevent 100 matched errors. These outcomes remain in accounting rather than being removed or used to relax the protocol.

The final artifact inventory covers new code/configurations/reports and the complete saved synthetic outputs, excluding itself. The separate M5B-2 readiness plan shows that the 230-position warm-up can theoretically hold 229/218 matched h=1/h=12 targets with usable genuine prehistory, or 206/195 without; actual support is unknown until separately authorized data access. M4A and prior inspected outcomes cannot become independent confirmation evidence. **Engineering integration is ready for review; M5B-2 and confirmation execution remain unapproved and have not started.**

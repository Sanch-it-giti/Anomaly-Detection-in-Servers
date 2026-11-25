# M3A — Causal forecasting adapter design and synthetic verification
Completed 30 October 2026. Engineering milestone only; no real model training or confirmation evaluation.

## 1. Result and scope

A common adapter interface and separate mock integration driver are implemented. The original M1 and M2D files, contracts, configuration and saved outputs are preserved byte for byte. M2B still has zero qualified machines under its original strict protocol; no new qualification or reserve replacement occurred.

The new driver accepts only validated frozen deterministic mock specifications. It cannot accept a user-supplied ARIMA, XGBoost, LSTM or arbitrary object merely because it implements the interface. It has no fit/refit API, external dataset loader, TensorFlow import, detector, adaptive selector, interval estimator or dashboard.

Both `confirmation_execution_allowed=false` and `m3_training_allowed=false` remain unchanged in the approved M2D configuration. New run manifests repeat those locks. M3A does not change the meaning of these authorization flags.

Read as primary sources: [research design](../phase3_dafr_research_design.md), [roadmap](../phase3_dafr_implementation_roadmap.md), [M2C protocol options](m2c_protocol_options.md), [M2D report](m2d_gap_aware_simulator_v2.md), [frozen pilot configuration](../../configs/dafr_engineering_pilot_v2.json), both V2 source modules, and the historical classical/advanced preparation and ARIMA/XGBoost forecasting scripts.

## 2. Created files

- `src/dafr/adapters_v1.py`: interface, frozen version/spec/result/resource records, genuine-window/lag helpers, three deterministic lifecycle mock families.
- `src/dafr/streaming_adapters_v1.py`: separate integration driver, validated update/forecast hooks, immutable adapter audit events and an exclusive synthetic output writer.
- `tests/test_dafr_adapters_v1.py`: 30 synthetic contract, integration, causality and preservation tests.
- `reports/dafr/m3a_preservation_v1.json`: 85-file pre-M3A SHA-256 inventory.
- This report: `reports/dafr/m3a_adapter_design_verification_v1.md`.

The synthetic run is `data/processed/dafr/m3a_mock_v1/m3a-synthetic-20261030-001/`, containing five exclusively created files: `manifest.json`, `events.jsonl`, `forecasts.jsonl`, `summary.json`, and `completion.json`. Generated data remain local under the existing ignore policy. Despite its filename, `forecasts.jsonl` includes every policy decision, with explicit abstention status and null prediction where appropriate.

## 3. Adapter interface and lifecycle

`ExpertAdapterV1` declares four operations:

| Operation | Contract |
|---|---|
| `metadata` | Read-only expert ID, immutable model version/family, training/scaling cutoffs and model availability timestamp |
| `update(tick, context)` | Consume exactly the next genuine or missing five-minute event; return explicit success, unavailability or numerical-failure receipt |
| `forecast(context, horizon)` | Forecast exact h=1/h=12 targets from state already updated through this origin; no assimilation or parameter mutation |
| `resources()` | Observation/forecast calls, completed state steps, genuine measurement updates, bounded-history slots, invalid-state flag and measured operation runtime |

There is deliberately no `fit`, `partial_fit`, scaler-fitting or refit operation. Initial model/scaler creation belongs to a separately authorized pre-replay development process. The three current families implement fixed arithmetic only. Family names indicate which lifecycle is tested; they do not imply that any real forecasting library is connected.

### Version and cutoff validation

`ModelVersionV1` uses a frozen expert ID/version/family and explicit aware UTC availability timestamp. Optional training/scaling cutoffs must be on the grid and no later than availability. Before the first replay mutation, every cutoff and availability time must be no later than the origin. Fit/scaling cutoffs must be strictly before the first replay tick, preventing repeated assimilation of data already used for fitting. A later availability time aborts this pilot rather than implementing unapproved asynchronous model loading.

Mock cutoffs used in tests are **declared synthetic metadata**, not evidence of fitted models. The current provenance kind is `synthetic_mock_no_fit`. Actual artifact identity, training data/target hashes and permitted real-artifact provenance require a future approved contract version.

The integration driver checks fixed adapter type, metadata and parameter fingerprint before each tick and after each response. Forecast responses must match the requested expert/version, origin, exact horizon/target, observation cutoff and context digest. Forecasting must leave the assimilated state fingerprint unchanged. Incorrect provenance, modified parameters or state-mutating forecasts are contract violations: abort the run, do not convert them into a seemingly valid forecast.

On successful expert issuance, the immutable V2 forecast stores that expert's fit/scaler cutoffs, model availability time and source version. During persistence fallback, these source cutoffs are null because persistence has no fitted model. The requested expert metadata remains separately visible in the linked adapter attempt event; the fixed policy ID/version continues to own its fallback errors. This avoids falsely attributing a persistence prediction to a trained source model.

### Shared causal information and event order

M2D remains unchanged and stub-only. The new driver subclasses its initialization/context primitives, reuses its validated ledger and immutable event contracts, and provides a separate explicit orchestration method. Small portions of chronology orchestration are repeated because the preserved M2D driver has no observation-update hook. Parity tests compare its gate, era, context and persistence/support behavior against M2D across the full synthetic gap fixture.

At each grid tick:

1. Reveal one genuine CPU or explicit missing event.
2. Resolve prior exact-target predictions into genuine scores or target-unavailable outcomes.
3. Apply the unchanged fourth-missing-tick era reset and support aging/maturity rules.
4. Call **every adapter's update**, even when its forecasting gate is closed, with the identical immutable tick/context object.
5. Snapshot causal state; for each fixed policy and h=1/h=12, call forecasting only after a successful update and the common 24-genuine-bin gate. Log the adapter attempt before the immutable decision.
6. Use the unchanged three-tick persistence fallback or explicit abstention on unavailable/failed/gated issuance.

No adapter receives future targets or other experts' predictions. Each learns about the entire revealed tick sequence, including missing events, while forecasting uses the same declared 24-position context and information cutoff. Architecture-specific state summaries need not be identical; their observations and available times are identical.

Each forecast result refers to the exact context already consumed by its update. The guard compares the full frozen context as well as the digest, so a caller cannot reuse a digest while substituting different historical values. Timestamp gaps are represented by explicit null slots; filtering out null rows is forbidden.

### Failure behavior

- Forecast numerical exceptions and nonfinite mock outputs become `numerical_failure`; explicit backend unavailability becomes `unavailable`. They produce logged persistence fallback when fresh enough, otherwise abstention.
- A forecast-only failure is retryable on a subsequent origin because forecasting must not mutate assimilated state.
- An unsuccessful update latches the mock state invalid. Later ticks are still consumed and logged, but the model remains unavailable; it cannot silently skip a failed state transition and resume as if history were complete. No automatic reset, refit or catch-up is invented. The distinction between update calls and completed state steps is recorded.
- Metadata/response integrity violations stop the run. A failed writer attempt keeps its reserved ID and failure receipt. Partial invalid-tick state is not recoverable for continued replay; start a new audited run after correcting the engineering defect.

Telemetry-era resets clear scoring support, not model parameters or the model's causal observation state. An update-failure quarantine is separate from telemetry eras and is not cleared by a gap recovery.

Runtime nanoseconds are observational reports outside the causal event bundle. They never affect eligibility, model choice or predictions; identical-input causal events remain deterministic despite different execution timing.

## 4. Model-specific integration requirements

### ARIMA

The ARIMA-family mock advances one fixed arithmetic state transition for every grid tick and counts measurement updates only for genuine CPU bins. This proves hook timing and missing-event delivery, not a Kalman-filter implementation.

A real adapter must carry fixed fitted parameters, process one regularly indexed observation or explicit missing measurement per five-minute step, skip the measurement correction when missing, and forecast h=1/h=12 from the resulting filtered state. It must not drop missing rows, use a future smoother, refit during replay, or advance the live state when calculating the h=12 prediction.

The official [statsmodels extend documentation](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAXResults.extend.html) describes filtering only newly appended chronological data, which is a candidate interface to verify against the installed version. This milestone does not certify actual missing-value behavior, fixed-parameter equivalence or numerical stability; those need real-backend tests before data experiments.

Historical `src/classical_models.py` fits a small AIC-selected ARIMA grid and the old runner emits one long fixed-origin forecast. The research design already documents differing likelihood burn-in and hidden convergence warnings. Those historical scripts were read, not run or corrected. M3B must establish common burn/likelihood treatment, convergence/finite/root checks, chronological validation and training provenance in new modules.

### XGBoost

The common helper returns exactly 24 genuine contiguous values, oldest to newest. Mock XGBoost uses **origin-relative offsets (0,1,2,5,11,23)**; offset 0 means the observed value at the current origin. These correspond to the old one-step lag convention (1,2,3,6,12,24) only for the next-step target. They must not be silently interpreted as target-relative lags for h=12.

The helper never removes a missing slot to reach further into the past. Any missing/short window is rejected, and the authoritative simulator gate prevents learned issuance. Fixed weights and a separately fitted, frozen scaler (if used) are required. Prediction wrappers must normalize exactly one finite scalar per requested horizon; the official [XGBoost prediction documentation](https://xgboost.readthedocs.io/en/stable/prediction.html) explains that return shapes depend on API/options, so shape checks must be tested against the chosen installed API.

The historical XGBoost script selects configurations with recursive validation, then forecasts the entire held-out span from one origin. It must not be called during replay. Whether new h=12 models use a direct horizon target or a recursive rollout remains a development decision, with common rolling validation. No actual h=12 training method is selected by the arithmetic mock.

### Planned LSTM

The LSTM-family mock consumes the **same 24 genuine values** as a declared sequence, using simple arithmetic rather than a recurrent network. The future adapter should produce a fixed shape such as one batch × 24 grid positions × one CPU feature, preserve order, use a frozen genuine-fit-only scaler and deterministic inference settings, and emit the exact requested target. It cannot fill missing targets, shuffle evaluation time, train on observed suffix feedback, or use final evaluation for early stopping.

TensorFlow and Keras are not installed, and nothing was installed here. Architecture, horizon strategy, seeds, epoch count, early-stopping folds and backend feasibility remain future decisions. The research design's small LSTM is a proposal, not an implemented or validated model.

## 5. Synthetic verification

Command:

```bash
.venv/bin/python -m unittest discover -s tests -q
```

**114 tests passed, zero failures/errors: all previous 84 plus 30 new M3A tests.** The final full run reported 3.731 seconds.

Coverage includes future-value/mask/stream-length perturbations; identical update/forecast contexts; exact horizon targets; genuine and missing updates; no missing compression; 24-bin recovery; origin-relative feature alignment; forecast purity; model/scaler/availability cutoffs; fallback provenance; numeric/unavailable forecast failures; horizon-specific failures; latched update failures; all-missing streams; parameter/version immutability; rejecting arbitrary objects/subclasses; tampered responses and forged contexts; delayed h=12 feedback; prediction immutability; M2D chronology/support parity; bounded observational runtime reporting; output no-overwrite/symlink/traversal protection; failed-run reservation; and all 85 preservation hashes.

No test fits or imports a real forecasting backend. Existing legacy tests continue to use their established fixtures; no historical training runner was executed.

### Saved integration demonstration

`m3a-synthetic-20261030-001` replays the unchanged 180-tick M2D synthetic fixture with persistence and three mock families.

| Measurement | Observed result |
|---|---:|
| Grid ticks / genuine / missing | 180 / 164 / 16 |
| Total policy/horizon decisions | 1,440 |
| Mock expert predictions | 432 |
| Learned-policy persistence fallbacks | 612 |
| Persistence-reference predictions | 348 |
| Abstentions | 48 |
| Genuine scored forecast-target pairs | 1,244 |
| Unavailable-target outcomes | 104 |
| Boundary-pending predictions | 44 |
| Per mock: update calls / completed state steps | 180 / 180 |
| Per mock: genuine measurement updates | 164 |
| Per mock: forecast calls | 144 |
| Per mock: retained grid slots | 24 |
| Full demonstration elapsed time | 0.8746 seconds |
| Python process peak RSS on macOS | 24,395,776 bytes (23.27 MiB) |

Conservation checks: 432+612+348+48=1,440 decisions, and 1,244+104+44=1,392 issued predictions. There are multiple policies/horizons per timestamp; these are not independent samples or forecasting results. The arithmetic families have no predictive validity claim.

Operation runtime per mock was about 28–30 milliseconds summed over its updates/forecasts; full run time also includes validation, hashing, audit construction and JSONL I/O. RSS is the process high-water mark, not system-wide pressure or future model memory.

Reproduce with a **new run ID**:

```bash
PYTHONPATH=src .venv/bin/python -m dafr.streaming_adapters_v1 --demo --run-id m3a-synthetic-NEW-ID
```

## 6. Preservation, environment and computational limits

All **85 protected SHA-256 values matched** before and after testing and the demonstration. The inventory covers M1/M2/M2B/M2C, all six M2D deliverables and all ten saved M2D run files, including the approved configuration and historical ARIMA/XGBoost forecast CSVs. No sealed ciphertext payload, confirmation suffix or key was opened; the existing sealing receipt remains hashed.

Installed package metadata checked without importing/training backends: Python 3.11.15 arm64, statsmodels 0.15.0 and XGBoost 3.2.0; TensorFlow and Keras absent. Current online XGBoost stable documentation describes a newer release, so installed-version compatibility must be tested in M3B rather than assumed.

The inherited engineering guards remain 2,304 grid ticks and eight total fixed policies, including persistence. Each mock keeps only 24 slots; scoring buffers remain capped at 288 per policy/horizon. Audit ledgers stay in memory within the pilot cap; production-scale disk-backed storage is not implemented.

An 8 GiB Mac must not fit models in parallel by default. Future ARIMA full-history refiltering, XGBoost thread oversubscription and LSTM framework/runtime allocation could dominate these mock costs. Use one machine/candidate at a time, limit numeric threads, measure real memory/latency, and log failures rather than inferring feasibility from this 23.27 MiB mock run. TensorFlow installation and a small runtime check require their own authorized scope.

## 7. Remaining decisions and M3B readiness

M3A meets the engineering objective: common causal contracts, validated mock hooks, immutable provenance, explicit failures and verified preservation. It is ready as the foundation for a **separately authorized M3B development-data adapter pilot**, subject to these concrete gates:

1. Define a new development-only execution configuration; do not alter the frozen M2D synthetic configuration or unlock confirmation.
2. Explicitly qualify permitted development data under the missing-data protocol. M2D's approved-machine list is still empty; prior conditional feasibility is not automatic data admission.
3. Implement and validate real backend adapters with a new approved real-artifact provenance/registration contract. The current factory intentionally rejects real objects and synthetic metadata cannot certify a fitted artifact.
4. Freeze actual training windows/target construction, h=12 direct versus recursive behavior, lag/scaler conventions, candidate budgets and numerical checks; keep validation chronological and final confirmation sealed.
5. Resolve real backend state initialization and failure handling. This pilot has no asynchronous model loading, hot replacement, serialization of live state or failed-state recovery.
6. Authorize TensorFlow separately if LSTM is included; otherwise explicitly label a two-expert pilot incomplete.
7. Keep all drift, adaptive selection, interval construction and confirmation work outside this milestone.

Timestamp metadata and hashes can validate a declared causal interface; they cannot independently prove that an arbitrary future fitted artifact used only legitimate data. Future training manifests, source-target hashes and backend-specific tests are still necessary. Runtime instrumentation is not a security sandbox, and strict mock registration is not a proof of scientific model quality.

No model was trained, no confirmation evaluation was authorized, no DAF-R improvement was claimed, and no dashboard was built. Work stops after M3A.


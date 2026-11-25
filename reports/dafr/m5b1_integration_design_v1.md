# M5B-1 real-backend adaptive integration design v1

6 November 2026. Authorized scope: registered statsmodels/XGBoost backends on generated synthetic fixtures. No new Alibaba adaptive evaluation, historical-model refit or confirmation execution is authorized.

## Sources and unchanged scientific rules

Read the M3B-2 completion/validation and checkpoint implementation, M4A completion/forward contracts, M5A design/completion/configuration and selector/streaming contracts. M4A outcome ledgers are not parsed for selector settings. Existing reports provide context; the M5A rule is reused exactly: independent h=1/h=12 matched absolute errors, minimum 100 pairs, maximum 288 pairs, last 288 grid ticks inclusive, 24-tick dwell, improvement max(0.1 CPU percentage points, 5%), ARIMA default, incumbent-retaining ties and conservative unavailable-incumbent fallback.

No frozen scientific rule needs changing. `MatchedSelectorV1.choose` is inherited unchanged. The separate typed feedback bridge validates real-record outcomes, advances the original M5A clock/reset/aging routine with no mock records, then inserts independently validated current-target matched pairs. Inserting these current-target pairs after aging is mathematically equivalent to the original insert-before-aging routine: new targets equal the current timestamp and cannot expire. Capacity remains 288. All old source/contracts/configurations remain byte-identical.

## Registry and execution boundary

`configs/dafr_m5b1_integration_v1.json` allows synthetic real-backend integration and the specified synthetic checkpoint build only. Real-data execution, Alibaba training, confirmation, M5B-2, drift and intervals are false. It pins the unchanged M5A configuration hash and requires identical selector/missingness settings.

`configs/dafr_m5b1_checkpoint_registry_v1.json` retains the six selected historical checkpoint bundles and their original hashes for verification only. No observation source is read to instantiate these checkpoints. The new execution factory accepts only an exact frozen `RegistryReferenceV1`, verifies registry SHA and canonical paths, requires the built-in synthetic generator/source/fit hash, then checks every checkpoint/metadata/scaler/feature hash, version and loaded parameter fingerprint. It calls the existing controlled `load_registered_adapter` factory and admits only exact `RealAdapter` instances for ARIMA/XGBoost. Arbitrary model objects and historical-data registries cannot enter this milestone's driver.

The synthetic recipe has 96 genuine fit observations defined by deterministic sine terms and a small trend, with no external dataset reader. ARIMA(1,1,1) uses prescribed valid coefficients [0.4,0.2,1.0] for actual state-space filtering; it does **not** optimize ARIMA parameters. XGBoost C1 trains two throwaway direct h=1/h=12 native boosters on generated genuine examples only, using depth 2, 100 trees, learning rate 0.05 and the existing fixed seed/settings. Their supervised target counts are 72 and 61. These are backend fixtures, not proposed research model coefficients or sufficient samples for a research result.

Existing `RealVersion.provenance_kind` retains its legacy loader label `development_prefit_v1`, including for synthetic fixtures. This string is preserved, not reinterpreted as Alibaba training evidence. The original checkpoint metadata's `scope=synthetic_backend_test`, generated source hash, new fixture registry and execution scope explicitly identify these as synthetic. No real checkpoint is relabeled as a mock.

## Fixed parameters versus causal state

Loading ARIMA filters the 96-position synthetic fit block once with stored coefficients. Its last 23 fit positions populate the common history without any adapter update call; the first replay observation is the next grid position. Both experts then receive exactly one genuine/missing update each tick, using the same immutable context. ARIMA advances one filtered transition per tick and skips measurement correction for missing values. XGBoost retains the same grid history and uses only origin-relative offsets [0,1,2,5,11,23] when the 24-genuine gate passes. Identity scaling is preserved.

Parameter hashes, registered types and version metadata are checked before replay mutations and after responses. Successful state cutoffs must equal the current origin; failed states retain their honest earlier cutoff. Forecasting both horizons must leave filtered/observation state unchanged. Changing the selected expert changes only the copied forecast source, never either expert's parameters/history. No fit API is called during replay; a guard rejects optimizer/booster-update entry points.

## Chronology and independent accounting

Each tick follows reveal → resolve old exact targets → fourth-missing era reset and matured support update/expiry → both state updates → shadow forecasts → horizon-specific selection → adaptive/persistence issuance. Target times are origin+300 or origin+3600 seconds. Target availability is never passed to issuance. Future targets at the stream boundary remain pending.

New immutable backend forecast contracts carry the actual `RealVersion`, requested checkpoint metadata SHA, parameter SHA, filtered-state cutoff/SHA, registry/configuration SHA, exact origin/target, context digest and selection snapshot. Adaptive expert centers link and copy a preissued immutable shadow. Requested-model provenance remains visible during persistence fallback, with the actual prediction source explicitly persistence. Shadows have no fake fallback prediction: gated/failed/unavailable shadows are null unissued attempts.

Only two genuine expert shadows with identical origin, horizon, target, era and context create a matched ranking pair. Genuine single-expert losses stay in the audit but never create unequal comparison support. Adaptive fallback/policy errors and persistence errors remain separate from shadow ranking. Every actual policy's own genuine errors retain bounded current-era support for future scaffolding; no interval or coverage outcome is implemented.

The age-three fallback, stale abstention and 24-genuine recovery gate are unchanged. On the fourth missing tick, clear active supports and reset incumbents/dwell once while retaining all old records and lifetime outcomes. Old-era predictions can mature and be scored but cannot seed new-era ranking. Telemetry resets/default restarts, loss-based switches and future drift alerts remain distinct events; no detector exists.

Numerical forecast failures create logged failed shadows and retryable fallback. An ARIMA state-update failure uses the existing invalid-state latch, logs stale cutoffs and remains unavailable; there is no hidden catch-up/refit. Provenance, version or parameter corruption aborts replay. Declared synthetic fault injection is confined to the fixture runner/tests and is absent from the driver's public interface.

## Verification and stopping point

Tests compare real shadows and state fingerprints with equivalent standalone real-backend synthetic runs, including missing ticks and recovery; compare sequential ARIMA state to full batch filtering; verify origin features, forecast purity, 99/100 support, inherited margin/dwell, separate horizons, exact missing/delayed targets, failure attribution, old-era exclusion, support expiry, immutable records, no-overwrite and preserved historical hashes. A saved-ledger auditor independently reconstructs support and switch conditions from new synthetic artifacts only.

Versioned outputs are under `data/processed/dafr/m5b1_synthetic_backend_v1/` and `reports/dafr/m5b1_v1/`. The run cap is 2,304 ticks; recent histories/support are bounded. Process RSS is checked against 4 GiB during replay. Small audit ledgers remain in memory, so this is an engineering harness rather than a production streaming store.

Completion measurements and any corrected synthetic test failures belong in the final report. M5B-2 readiness is a separate planning document. No Alibaba access or evaluation, LSTM, drift/interval/dashboard implementation or confirmation unlock follows automatically.

# M6A drift-monitoring design v1 — SYNTHETIC ENGINEERING VERIFICATION ONLY

7 November 2026. These are new prespecified engineering choices, not optimized scientific settings or changes to any previously frozen selector/model protocol.

## Scope and reference

Primary context: original DAF-R research design/roadmap, M2C protocol options, M2D missing-event rules, M5A selector design and M5B-2 completion/recommendations. The original design proposes Page–Hinkley monitoring of standardized CPU level and worsening persistence absolute errors; it does not mandate an alternative detector. This first engineering implementation covers the **one-sided fixed persistence-error branch only**. Two-sided CPU-level monitoring and proposed cross-channel watch/confirmation/selector responses remain unimplemented and require separate design. No real development outcome ledger is analyzed or used to choose constants.

The reference is always `persistence`, version `rule_v2`, forecasting the latest genuinely observed CPU value if at most three elapsed ticks old. h=1/h=12 have independent states. The detector observes **absolute forecast error in CPU percentage points**, not CPU itself, selector-selected error, fallback from an ARIMA policy, an imputed value or missingness converted to zero. Genuine zero error is valid; a missing target supplies no sample.

A CPU-level change can affect persistence error transiently or persistently. Neither CPU-level variation nor a statistical error alarm proves a changed conditional forecasting relationship (concept drift). Missing telemetry, telemetry-era resets, statistical warnings/alarms, selector switches and refits are different events. M6A contains no selector/refitting callback and changes no M5A/M5B behavior.

## Exact normalization and detector equations

For each telemetry era and horizon, collect the first **32 genuine matured reference errors**. Freeze center m=median(error) and scale s=max(1.4826×median(|error−m|), **0.1 CPU percentage points**). No complete-series fit, future scaler or per-alarm normalization refit occurs. Retain only these 32 calibration values. Normalization is cold again on an era boundary.

Subsequent raw input e is normalized as z=clip((e−m)/s,−4,+4). Record raw e, normalized z, monitor clipping counts and the number of clipped normalization samples. Clipping limits the influence of an isolated impulse but can conceal the magnitude of genuine changes; clipping is never evidence of stability. The 0.1 floor prevents a zero-MAD division on constant errors.

The anchored initial mean mu0 is the mean of the 32 clipped normalized calibration errors. On initialization or statistical rearm set mu=mu0, weight n=32, cumulative C=0 and minimum M=0. For each genuinely matured, current-era, post-normalization input **outside cooldown**:

1. n←n+1; mu←mu+(z−mu)/n.
2. C←C+z−mu−**0.05**.
3. M←min(M,C); PH←C−M.

This is a precisely defined Page–Hinkley-style one-sided cumulative-deviation statistic, not a claim of bitwise equivalence to River or a published implementation's guarantees. Normalized statistics/thresholds are dimensionless; original errors remain CPU percentage points.

Maintain at most **288 genuine error target timestamps**, expiring targets older than current−287 grid ticks. Alerts require at least **64 such recent errors**, including the 32 normalization errors, and frozen normalization. Before 64, PH may accumulate but both warnings and alarms are suppressed. If expiry reduces previously sufficient support below 64, clear/rearm PH and warning state; retain current-era normalization. This avoids treating a stale statistic as fresh evidence. The PH running mean/sum itself is cumulative since rearm within the era, not a rolling 288-error estimator; recent support is its separate freshness/eligibility guard.

## Warnings, alarms and cooldown

- PH ≥ **4** enters warning state, emitting only the normal→warning transition. PH below 4 clears it on the next error update. Insufficient support also clears warning.
- PH ≥ **8** emits `statistical_alarm`, with priority over a warning transition at the same update.
- After an alarm, reset PH/running mean to the anchored initial state, retain fixed normalization/recent support, and suppress statistical updates/warnings/alarms for **24 elapsed grid ticks**. Genuine errors during cooldown still count toward recent/lifetime support and clipping diagnostics. Cooldown ends at exact equality with its boundary, irrespective of the number of errors observed meanwhile.
- The alarm receipt records the crossing statistic, genuine support, exact availability time, fixed source/version, horizon/era, original forecast/outcome IDs, threshold, cooldown-before flag and new cooldown boundary. Its snapshot is captured before PH is cleared. Later snapshots show rearmed state.
- Repeated alarms can occur under the same persistent increase after cooldown. They are counted honestly, not interpreted as multiple independent regime changes. No rebaseline, model refit, hyperparameter reselection or expert switch is automatic.

All values (32,64,288,0.1,1.4826,4,0.05,4/8,24) are engineering choices frozen before saved demonstrations. They were not selected from M4A/M5B-2 errors and are not validated final research thresholds. The detector's 64-error gate is new and separate from the unchanged M5A 100-pair selection gate and M2D 100-error interval-support scaffolding.

## Causal event order and gaps

At every five-minute tick: reveal genuine/missing CPU → resolve immutable reference forecasts targeting exactly that tick → apply fourth-missing era reset/support aging → advance each detector clock → feed only genuine exact-target errors → emit monitoring snapshots/warnings/alarms → record causal source state → issue future fixed-reference forecasts. Thus h=12 errors cannot enter before origin+60 minutes. Beyond-stream predictions remain pending. Late data/revisions are unsupported rather than backdated.

After exactly four consecutive missing ticks, start one new telemetry era. Each detector clears its normalization, PH, active support, warning and cooldown; lifetime accepted/ignored counts and all audit records survive. Additional missing ticks in the same gap do not reset repeatedly. An old-era forecast may later score at a genuine exact target, but its detector receipt is `old_era_ignored` and does not seed new normalization/support/statistics. Short missing runs supply no artificial error, warning input or coverage result; clocks still age support.

The fixed persistence reference keeps the original age-three rule and abstains when absent/stale. It does not require the 24-genuine learned-model gate; the unchanged source context still records that gate for provenance. No learned expert is connected here. Original fixed-source V2 forecasts retain their strict existing `disabled_m2d` detector flag; the new external monitoring component is represented by separate versioned immutable records, not by weakening V2 contracts.

Declared synthetic reference-failure origins create explicit unavailable/abstained forecast records and failure events. No forecast or zero residual is invented. These are controlled numerical-failure surrogates, not real ARIMA/XGBoost failure experiments. Their exact future targets have no detector error if no prediction was issued.

## Predefined synthetic experiments and reporting

Eleven named fixtures are fixed in `drift_fixtures_v1.py`: stable errors, sustained error increase, isolated outlier, gradual slope change, abrupt CPU-level step, short missing runs, leading/long/trailing four-tick resets, delayed h=12, insufficient support with an early change, declared reference forecast failures, and persistent-change cooldown stress. They use bounded deterministic CPU trajectories and fixed persistence predictions, not preassigned future-aware forecasts. Labels are available only to the post-run summary, never the detector.

No-change/isolated-outlier fixture alarms are reported as false for the sustained-change monitoring task; for labeled-change fixtures, pre-change alarms are false and later alarms are counted as post-change responses. First delay is target availability index minus known fixture intervention index, with missing delay/missed flag if absent. These labels are designed interventions, not proven concept-drift ground truth. In particular, a level step can create only one h=1 error impulse and be missed by this error-only monitor; that limitation must be retained.

All source decisions/outcomes, genuine error inputs, detector clocks/updates, warnings, alarms, telemetry resets and failures are immutable/versioned outputs. Tests verify independent horizons, recurrence/normalization, min support, clipping, cooldown, exact targets, missingness, era exclusion, forecast parity, suffix invariance, no callbacks, output protection and historical fingerprints. All previous 273 tests also run using their already approved regression fixtures. Historical ledger preservation is opaque hashing only; new detector experiments never parse real data/outcomes.

State is bounded by 32 normalization values, 288 target timestamps and O(1) statistics per horizon. The synthetic reference's capped audit ledger is retained in memory for at most 2,304 ticks. Replay checks process RSS against 4 GiB on the 8 GB Mac. No dependency install is required. Final measured synthetic alarms/delays/false alarms and unresolved research decisions are reported separately without claiming real-world performance. M6B, uncertainty intervals and dashboard remain disabled.

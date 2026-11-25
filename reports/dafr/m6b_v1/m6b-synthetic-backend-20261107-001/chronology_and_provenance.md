# M6B saved chronology and drift-alert provenance

Synthetic engineering evidence only. The three independent saved-ledger audits in `verification.json` pass. Source configuration hashes, registered checkpoint metadata/parameters/state hashes, training/scaling/model availability cutoffs and context digests remain in original backend records. The synthetic registry is saved separately from the immutable historical registry.

Each event tick follows the unchanged backend's reveal, target resolution, era/support/selector feedback, real adapter updates and forecast issuance. External monitor events then carry their own monotone sequence and the maximum completed backend event sequence for that tick. This explicit barrier avoids implying that an alert caused a forecast already issued at that origin. No target availability is passed to prior issuance.

Example from the sustained fixture, synthetic event coordinates:

| Record | Time UTC | Link / interpretation |
|---|---|---|
| persistence h12 issuance |2000-01-01 08:05|forecast-113; future exact target09:05|
| genuine arrival and scoring |2000-01-01 09:05|outcome-371 links forecast-113; no error before this tick|
| current backend issuance completes |2000-01-01 09:05|backend barrier sequence395|
| reference error/monitor update |2000-01-01 09:05|immutable original forecast/outcome retained; h12-only detector feedback|
| first sustained-change alarm, each horizon |2000-01-01 21:35|relative tick162; intervention160; statistical monitoring event, no model/selector response|

These times derive from the existing synthetic epoch, not real Alibaba timestamps or actual execution time. Persistence source is always rule_v2; backend envelope version m5b1_real_backend_v1 is explicitly mapped in the bridge view, not silently changed in source records. The view's backend-sequence origin locator is declared and original tick linkage remains in the authoritative backend ledger.

Missing targets create target_unavailable outcomes and no reference sample. The fourth missing tick starts one era per long gap; two detector reset receipts accompany it. A genuinely matured old-era forecast still scores in the backend, but the detector records old_era_ignored rather than adding support/normalization. All five telemetry resets are independent of statistical warnings/alarms and the one loss-driven selector switch. Numerical forecast failure and latched ARIMA update failure remain backend call records, not detector labels.

The audit verifies every eligible genuine persistence outcome has exactly one reference link, rejects adaptive/fallback/expert losses, checks exact origin/target/horizon/value/era/sequence/context linkage, reconstructs all frozen detector updates/alerts and checks completed issuance barriers. Model-enabled and monitor-disabled forecasts match in full. No observed center, earlier prediction, selector rule or model parameter is revised after an alarm. Checkpoint and ledger fingerprints are independently rechecked; future-suffix invariance is also covered in tests.

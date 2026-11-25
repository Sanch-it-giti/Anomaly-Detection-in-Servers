# M5A preservation and verification report

31 October 2026. Run group `m5a-synthetic-20261031-001`.

## Test evidence

The final code/configuration/design gate contains **205 passing tests**, 166 existing and 39 new, zero failures/errors, 22.395 seconds. Command:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

The final test log SHA-256 and exact source SHA-256 values are saved in `reports/dafr/m5a_synthetic_gate_v1.json`. All seven gated files still match after the demonstrations: new configuration, four Python modules, test file and selector design. The implementation/configuration was not adjusted after inspecting demonstration outcomes. Later completion/accounting documents summarize those outcomes without changing the frozen design.

Thirty-nine new tests cover the requested causal feedback, matched-support fairness, independent horizons, cold start, hysteresis/dwell/ties, missing/failure behavior, era support, immutable decisions, future perturbations, bounded memory, no-overwrite and preservation. A filesystem-read guard verifies that constructing/replaying the new selector does not read data/model paths. A saved-artifact test recomputes support and deliberately changes a temporary fixture prediction to prove the independent auditor rejects it; it does not alter saved demonstration or historical records.

An early test fixture inherited the default h=12-only fault setting. The test intended both horizons, so it was corrected to `fault_horizon=None`, followed by a complete passing gate. No selector constants were changed. No unresolved test failure remains.

## Historical preservation and access interpretation

The M5A baseline inventory has **374 protected SHA-256 entries**: the prior 297-file inventory plus the 76 newly inventoried M4A files and M4A's inventory itself. All match before and after execution. This protects original M1–M4A code, configurations, reports, historical ARIMA/XGBoost outputs, real fitted checkpoints and prior run ledgers. No earlier artifact was overwritten or corrected in place.

Some preserved ledgers contain previously authorized observations/outcomes. Their bytes are read only into a hash function, not parsed for M5A selection. The user explicitly approved regression-only reads of existing prefix fixtures and historical hashes; the old suite retains those fixture dependencies. This exception does not authorize M5A real-data adaptation or additional partitions. The new selector, generators and saved-ledger auditor consume built-in synthetic streams and newly generated synthetic records only. No M4A outcome search or tuning occurs.

This check does not reread forbidden original suffix tails or sealed confirmation payloads. Original inventories never required such reads; historical whole-export hashes remain prior metadata rather than newly verified unread bytes. No encryption key, confirmation suffix, calibration/warm-up or final block was opened. Existing confirmation locks and fitted checkpoint hashes remain unchanged; the new execution manifest also records all real/training/confirmation/M5B flags false.

## Saved-run audit

All four independent synthetic ledger audits passed. They verify:

- Complete original grid/tick correspondence and strictly increasing event sequences.
- Exact origin + h×300-second targets and issue-before-arrival-before-score ordering.
- Null losses/coverage for missing exact targets; no scoring of unissued attempts or boundary-pending predictions.
- Identical contexts across experts and exact links/copies from selected immutable shadows.
- Matched pair origin/target/era/context/version identity and genuine-only losses.
- Recomputed current-era support, 288-pair capacity/elapsed aging and matched mean errors.
- The minimum 100 pairs, margin and elapsed dwell for every recorded loss-based switch.
- Separate reset/default-restart/switch counts and preservation of lifetime outcomes.
- Reconciliation of 18,400 decisions/attempts into 17,197 genuine scores, 138 missing-target outcomes, 170 boundary pending and 895 unissued attempts.

Across all fixtures there are three loss-based switches and three telemetry-era resets. Those resets also create six horizon-specific default-restart events; no drift alarm is emitted. Full per-scenario receipts are in [ledger_verification.json](ledger_verification.json).

## Output protection and remaining limits

Actual reuse of the saved run-group ID was rejected before synthetic generation. All **50 files then present** across the report group and four synthetic runs retained identical byte hashes. Automated tests separately verify successful/failed run-ID reservation and exclusive output creation. Later verification/report files are new files, not updates to immutable ledgers. [overwrite_protection.json](overwrite_protection.json) records the actual check.

All four runs completed below the 4 GiB process RSS limit. No unexpected numerical exception, source/provenance violation or data-access blocker remains. Deliberate failure injections and conservative fallback are reported rather than removed. Standard-library mock replay and small capped ledgers do not establish future real-model scaling, adaptive accuracy, statistical significance or drift-detection performance.

The final artifact inventory hashes the new engineering files, reports and all four synthetic run directories; its own file is excluded to avoid a circular hash. It is an integrity record, not permission to upload raw historical data or open any new research block. M5A stops here, with M5B and confirmation disabled.

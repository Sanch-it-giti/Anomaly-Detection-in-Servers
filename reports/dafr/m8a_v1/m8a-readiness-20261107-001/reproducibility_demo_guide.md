# Reproducibility and read-only demonstration guide

This guide demonstrates already verified artifacts without new Alibaba reads, model fitting, restricted calibration/final data or confirmation execution. Run from `/Users/sanchitkhandelwal/Desktop/server-resource-forecasting` using the existing `.venv`. It does not install dependencies or execute old fitting/forecasting scripts. Research artifacts/data/models may be Git-ignored; if absent on another machine, show the public report and report the missing local archive rather than downloading/decrypting data or claiming a verification pass.

## A. Evidence-first demonstration

1. Open [project status](project_status_matrix.md) and [report draft](research_report_draft.md). Explain the distinction between historical NAB, M3B/M4A development, M5B-2 retrospective and M6/M7 synthetic evidence.
2. Show the original NAB plots and M5B-2 expert/complete-policy figures in [the figure inventory](presentation_outline.md). Emphasize the unfavorable h12 adaptive result. Do not run `src/run_arima_baseline.py` or `src/run_xgboost_forecast.py`: those historical commands fit models and may overwrite old outputs.
3. Open the saved [M7B coverage/availability report](../../m7b_v1/m7b-synthetic-backend-20261107-001/coverage_width_availability.md). Read both coverage and its available/genuine denominator. Growing variation undercovers; update-failure common comparisons are unavailable, not zero.
4. Show [M7B parity/provenance](../../m7b_v1/m7b-synthetic-backend-20261107-001/parity_chronology_provenance.md), nesting and protected hashes. No live retraining or forecast execution is necessary.
5. End with [confirmation readiness](confirmation_qualification_readiness.md): two necessary failures, seven unknown full screens, zero verified admissions, keys/blocks remain closed.

## B. Safe saved-ledger audit

The following reads only previously generated **synthetic** M7B ledgers and configuration metadata. It reconstructs audit/calibration/drift checks in memory, loads no historical trained model for prediction and fits nothing. It fails if local artifacts are missing or changed:

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
from pathlib import Path
from dafr.audit_m7b_v1 import audit_backend_intervals
root = Path('data/processed/dafr/m7b_synthetic_backend_v1/m7b-synthetic-backend-20261107-001')
for case in ('continuous', 'growing', 'gaps_failures', 'update_failure'):
    if not (root / case / 'hashes.json').is_file():
        raise SystemExit(f'Missing local synthetic artifacts: {case}; no data acquisition attempted')
    result = audit_backend_intervals(root / case)
    print(case, result['status'], result['nested_95_90_pairs'])
PY
```

This is verification of recorded synthetic outputs, not a new independent experiment or research-calibration run. Do not run `run_m7b_v1 --run-id NEW` as an M8A demo: its fixture builder trains new synthetic models. Do not bypass output protection by reusing/deleting an existing run directory.

For a small live chronology-only test with deterministic stubs and no model training:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_dafr_chronology.py' -v
```

## C. Verification scope and environment provenance

M7B's recorded full suite passed409 tests. M8A discovered409, **executed304 with304 passes and skipped105** because four classes train new synthetic fixture checkpoints during setup. Their source files/assertions were not edited or replaced by cached models. Runtime skip flags applied only to that audit process. The skipped classes are RealBackendTests, AdaptiveBackendTests, RealDriftTests and RealIntervalTests. All skipped IDs/reasons are in [the fresh verification receipt](regression_verification.json). Global guards on statsmodels fitting and XGBoost fit/train/update recorded zero fitting attempts; existing mock filtering and previously approved regression fixtures remain permitted. This is not a new409-all-pass claim.

The ordinary full command `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v` includes synthetic model fitting and is therefore **not the no-fitting M8A demonstration command**. Re-running those setups needs separately authorized verification scope. Do not quietly remove the no-fitting restriction to get a larger passing count.

[Environment provenance](environment_provenance.json) records the current interpreter/platform and installed package versions from metadata without importing or installing TensorFlow. Checkpoint metadata and frozen configurations supply seeds, feature/scaler rules and historical versions; M8A does not overwrite them to match a new environment. Hash and dependency mismatch is reported, never silently repaired by refitting or relabelling old results.

## D. Smallest optional read-only frontend

Future optional milestone, **not implemented here**: a local archived-evidence viewer with four panels—scope/status, historical development comparisons, synthetic interval/drift diagnostics, and provenance/limitations. Inputs are a fixed allowlist of public report Markdown/CSV/JSON and the eight existing PNGs. Labels must include development/retrospective/synthetic and availability denominators. Use cached aggregates, not raw traces, checkpoint loading or inference.

No upload, arbitrary path browser, dataset acquisition, decrypt/key access, training, forecast-run button, final/confirmation execution, threshold editing or writing experiment artifacts. If an optional UI is later implemented, missing data should show an explicit unavailable panel. It is an archive viewer, not a live calibrated forecasting service. Building it or a slide deck is not required to support the current engineering evidence and cannot resolve missing independent qualification or validation.

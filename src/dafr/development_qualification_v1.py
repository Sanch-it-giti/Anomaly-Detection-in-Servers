"""Read-only M3B-1 development-prefix qualification and sample counting.

No models, feature values, transforms or forecasts are constructed. Only the
six explicitly nominated prefix paths can be read. Quality masks drive counts.
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from math import isfinite
from pathlib import Path


PRIMARY_IDS = ("m_505", "m_1426", "m_3028")
RESERVE_IDS = ("m_3276", "m_1029", "m_2104")
PREFIX_DIRECTORY = Path("data/processed/dafr/m2b_v1/qualification_20261030_001/five_minute_prefix")
EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)
PREFIX_SIZE = 1152
FIT_END = 864
BURN = 24
FIELDS = ["timestamp", "bin_end_seconds", "value", "quality_status", "failure_reasons"]


def validate_prefix_csv(payload: bytes, expected_size: int = PREFIX_SIZE) -> tuple[bool, ...]:
    """Validate the canonical M2B export, retaining failed bins as False."""
    if type(expected_size) is not int or expected_size <= 0:
        raise ValueError("Expected row count must be positive.")
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8"), newline=""))
    if reader.fieldnames != FIELDS:
        raise ValueError("Unexpected five-minute prefix schema.")
    mask = []
    for i, row in enumerate(reader):
        if i >= expected_size or None in row or any(v is None for v in row.values()):
            raise ValueError("Unexpected row length or prefix overflow.")
        seconds = (i + 1) * 300
        if row["bin_end_seconds"] != str(seconds):
            raise ValueError("Prefix must retain exact consecutive bin positions, without duplicates.")
        timestamp = datetime.fromisoformat(row["timestamp"])
        if (timestamp.tzinfo is None or timestamp.utcoffset() != timedelta(0)
            or timestamp != EPOCH + timedelta(seconds=seconds)):
            raise ValueError("Timestamp does not match its canonical synthetic-UTC bin label.")
        if row["quality_status"] == "valid":
            value = float(row["value"])
            if not isfinite(value) or not 0 <= value <= 100 or row["failure_reasons"]:
                raise ValueError("Invalid genuine CPU or conflicting quality metadata.")
            mask.append(True)
        elif row["quality_status"] == "failed" and row["value"] == "" and row["failure_reasons"]:
            mask.append(False)
        else:
            raise ValueError("Failed bins need missing CPU and explicit original reasons.")
    if len(mask) != expected_size:
        raise ValueError("Truncated prefix: missing grid slots must be explicit rows.")
    return tuple(mask)


def read_development_mask(project_root: Path, machine_id: str, expected_sha256: str) -> tuple[bool, ...]:
    if machine_id not in PRIMARY_IDS + RESERVE_IDS:
        raise ValueError("Only the original six development nominees are authorized.")
    root = Path(project_root).resolve()
    path = root / PREFIX_DIRECTORY / f"{machine_id}.csv"
    if path.resolve() != path:
        raise ValueError("Do not redirect authorized prefixes using symlinks.")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError("Prefix checksum differs from the M2C source evidence.")
    return validate_prefix_csv(payload)


def _validate_mask(mask: tuple[bool, ...]) -> None:
    if not isinstance(mask, tuple) or not mask or any(type(x) is not bool for x in mask):
        raise ValueError("Expected an immutable nonempty genuine-observation mask.")


def learned_origins(mask: tuple[bool, ...]) -> tuple[int, ...]:
    _validate_mask(mask)
    return tuple(i for i in range(23, len(mask)) if all(mask[i-23:i+1]))


def example_origins(mask: tuple[bool, ...], horizon: int, target_start: int, target_end: int,
                    origin_start: int = 0) -> tuple[int, ...]:
    """Only genuine 24-slot inputs and genuine exact targets inside the block.

    origin_start is the first real model-ready issuance origin. Validation uses
    FIT_END, never origins before the fitted artifact could have been available.
    Target masks here count offline opportunity; they cannot control issuance.
    """
    _validate_mask(mask)
    if type(horizon) is not int or horizon not in (1, 12):
        raise ValueError("Only integer h=1/h=12 are supported.")
    if any(type(x) is not int for x in (target_start, target_end, origin_start)):
        raise ValueError("Partition bounds must be integer grid positions.")
    if not 0 <= target_start < target_end <= len(mask) or not 0 <= origin_start < len(mask):
        raise ValueError("Invalid partition or issuance bounds.")
    return tuple(i for i in learned_origins(mask) if i >= origin_start
                 and target_start <= i + horizon < target_end and mask[i + horizon])


def longest_run(mask: tuple[bool, ...], observed: bool = True) -> int:
    _validate_mask(mask)
    best = run = 0
    for value in mask:
        run = run + 1 if value is observed else 0
        best = max(best, run)
    return best


def disjoint_spans(origins: tuple[int, ...], horizon: int) -> int:
    """Greedy nonoverlapping [origin-23,target] spans, not an effective sample size."""
    end = -1
    count = 0
    for origin in origins:
        if origin - 23 > end:
            count += 1
            end = origin + horizon
    return count


def prefix_summary(mask: tuple[bool, ...], screens: dict, fit_end: int = FIT_END) -> dict:
    _validate_mask(mask)
    if len(mask) != PREFIX_SIZE or type(fit_end) is not int or not 24 < fit_end < len(mask):
        raise ValueError("Qualification uses the fixed 1,152-bin prefix and an explicit inner split.")
    origins = learned_origins(mask)
    full_pairs = {str(h): len(example_origins(mask, h, 0, len(mask))) for h in (1, 12)}
    observed = sum(mask)
    checks = {
        "genuine_bins": observed >= screens["min_genuine_bins"],
        "coverage": observed / len(mask) >= screens["min_observed_coverage"],
        "longest_genuine_run": longest_run(mask) >= screens["min_longest_genuine_run_bins"],
        "eligible_origin_fraction": len(origins) / len(mask) >= screens["min_learned_origin_fraction"],
        "h1_pairs": full_pairs["1"] >= screens["min_potential_genuine_target_pairs_each_horizon"],
        "h12_pairs": full_pairs["12"] >= screens["min_potential_genuine_target_pairs_each_horizon"],
    }
    per_horizon = {}
    last = None
    persistence_origins = []
    for i, genuine in enumerate(mask):
        if genuine:
            last = i
        if last is not None and i - last <= 3 and i >= fit_end:
            persistence_origins.append(i)
    for h in (1, 12):
        training = example_origins(mask, h, 0, fit_end)
        validation = example_origins(mask, h, fit_end, len(mask), fit_end)
        issued = [i for i in origins if i >= fit_end]
        per_horizon[str(h)] = {
            "xgboost_direct_training_examples": len(training),
            "lstm_direct_training_sequences": len(training),
            "arima_training_supervised_examples": None,
            "arima_training_pair_diagnostic_not_likelihood_count": len(training),
            "arima_xgboost_lstm_common_validation_pairs": len(validation),
            "validation_learned_eligible_origins_including_tail": len(issued),
            "validation_learned_missing_targets": sum(i+h < len(mask) and not mask[i+h] for i in issued),
            "validation_learned_boundary_pending": sum(i+h >= len(mask) for i in issued),
            "persistence_validation_issued_including_tail": len(persistence_origins),
            "persistence_validation_genuine_pairs": sum(i+h < len(mask) and mask[i+h] for i in persistence_origins),
            "persistence_validation_missing_targets": sum(i+h < len(mask) and not mask[i+h] for i in persistence_origins),
            "persistence_validation_boundary_pending": sum(i+h >= len(mask) for i in persistence_origins),
            "disjoint_training_input_to_target_spans": disjoint_spans(training, h),
            "disjoint_validation_input_to_target_spans": disjoint_spans(validation, h),
            "training_origin_index_sha256": hashlib.sha256(json.dumps(training).encode()).hexdigest(),
            "validation_origin_index_sha256": hashlib.sha256(json.dumps(validation).encode()).hexdigest(),
        }
    return {
        "expected_prefix_bins": len(mask), "genuine_bins": observed, "missing_bins": len(mask)-observed,
        "observed_coverage": observed/len(mask), "longest_genuine_run": longest_run(mask),
        "longest_missing_run": longest_run(mask, False), "learned_eligible_origins": len(origins),
        "learned_origin_fraction": len(origins)/len(mask), "full_prefix_genuine_pairs": full_pairs,
        "all_v2_screens_pass": all(checks.values()), "screen_results": checks,
        "fit_grid_positions": fit_end, "fit_genuine_observations": sum(mask[:fit_end]),
        "arima_common_burn_grid_positions": BURN,
        "arima_effective_genuine_likelihood_updates": sum(mask[BURN:fit_end]),
        "validation_grid_positions": len(mask)-fit_end,
        "validation_genuine_observations": sum(mask[fit_end:]),
        "mask_sha256": hashlib.sha256(bytes(mask)).hexdigest(),
        "per_horizon": per_horizon,
    }


def qualify_development_prefixes(project_root: Path) -> dict:
    root = Path(project_root).resolve()
    pilot = json.loads((root / "configs/dafr_engineering_pilot_v2.json").read_text())
    if pilot["confirmation_execution_allowed"] is not False or pilot["m3_training_allowed"] is not False:
        raise ValueError("Original execution locks must remain false.")
    evidence = json.loads((root / "configs/dafr_missing_data_protocol_v2_draft.json").read_text())["development_prefix_evidence"]
    results = {}
    for machine in PRIMARY_IDS + RESERVE_IDS:
        expected = evidence[machine]["source_sha256"]
        mask = read_development_mask(root, machine, expected)
        result = prefix_summary(mask, pilot["prefix_eligibility"])
        result.update(machine_id=machine, role="development", nomination="primary" if machine in PRIMARY_IDS else "reserve",
                      source_relative_path=str(PREFIX_DIRECTORY / f"{machine}.csv"), source_sha256=expected)
        results[machine] = result
    return results

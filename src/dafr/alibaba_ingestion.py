"""M2B: bounded Alibaba 2018 machine-table qualification, without forecasting.

The archive is checksum-verified before any CSV is read. Only nominated IDs and
three raw fields plus a full-row duplicate fingerprint enter a private SQLite
staging table. Prefix quality alone selects candidates. Confirmation values
after the prefix are processed mechanically into sealed artifacts; neither
their values nor their quality summaries enter the public qualification report.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import time


ROOT = Path(__file__).resolve().parents[2]
WINDOW_END = 691200
PREFIX_END = 345600
BIN_SECONDS = 300
EXPECTED_FIELDS = (
    "machine_id", "time_stamp", "cpu_util_percent", "mem_util_percent",
    "mem_gps", "mkpi", "net_in", "net_out", "disk_io_percent",
)
EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def peak_rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def require_resources(path: Path, min_free_bytes: int = 4 * 1024**3) -> dict:
    free = shutil.disk_usage(path).free
    if free < min_free_bytes:
        raise RuntimeError("Less than the required 4 GiB free disk space.")
    return {"free_disk_bytes": free, "logical_cpus": os.cpu_count(),
            "peak_process_rss_bytes": peak_rss_bytes()}


def verify_archive(path: Path, expected_sha256: str) -> dict:
    """Checksum mismatch stops the pipeline before it reserves an output run."""
    started = time.monotonic()
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise ValueError("Archive SHA-256 mismatch; ingestion forbidden.")
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": actual,
            "verified": True, "checksum_seconds": time.monotonic() - started}


def _decimal(text: str) -> Decimal | None:
    try:
        value = Decimal(text.strip())
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def create_staging(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA cache_size=-16384")  # 16 MiB page cache.
    connection.execute("PRAGMA temp_store=FILE")
    connection.execute("PRAGMA mmap_size=0")
    connection.execute("""CREATE TABLE raw (
        machine_id TEXT NOT NULL, elapsed_text TEXT NOT NULL,
        elapsed_numeric REAL NOT NULL, cpu_text TEXT NOT NULL,
        row_digest BLOB NOT NULL, ordinal INTEGER NOT NULL)""")
    return connection


def bounded_lines(handle, maximum_bytes: int = 65536):
    """Limit allocation before reading a malformed row, not after allocation."""
    while True:
        line = handle.readline(maximum_bytes + 1)
        if not line:
            return
        if len(line) > maximum_bytes:
            raise ValueError("Unreasonably large CSV row.")
        yield line


def stage_archive(archive_path: Path, connection: sqlite3.Connection,
                  nominated_ids: set[str], *, expected_member_bytes: int | None = None,
                  row_cap: int = 2_000_000, memory_stop_bytes: int = 4 * 1024**3) -> dict:
    """Sequential decompression with at most 5,000 retained rows per batch.

    Non-nominated values are never parsed or retained. No extract()/extractall()
    call is made; TAR members are read as streams. The per-row CPU payload stays
    in staging only, including invalid payloads needed for duplicate decisions.
    """
    started = time.monotonic()
    if peak_rss_bytes() > memory_stop_bytes:
        raise MemoryError("Ingestion already exceeds the recorded memory stop limit.")
    stats = {"source_rows": 0, "nominated_rows_retained": 0, "header_present": False,
             "unplaceable_timestamp_rows": 0, "outside_window_rows": 0,
             "archive_regular_members": 0, "schema_field_count": 9,
             "malformed_rows": 0}
    batch = []
    seen_member = False
    with tarfile.open(archive_path, mode="r|gz", bufsize=1024 * 1024) as archive:
        for member in archive:
            if not member.isfile():
                continue
            stats["archive_regular_members"] += 1
            if seen_member or member.name not in ("machine_usage.csv", "./machine_usage.csv"):
                raise ValueError("Unexpected archive member; only machine_usage.csv is permitted.")
            seen_member = True
            if expected_member_bytes is not None and member.size != expected_member_bytes:
                raise ValueError("TAR member size differs from the verified M2 declaration.")
            stats["declared_member_bytes"] = member.size
            handle = archive.extractfile(member)  # stream, not filesystem extraction
            if handle is None:
                raise ValueError("Cannot open usage member.")
            with handle:
                for ordinal, line in enumerate(bounded_lines(handle), start=1):
                    # Machine IDs are simple ASCII tokens. Handle quoted rows
                    # with csv.reader rather than counting quoted commas.
                    first = line.partition(b",")[0].strip(b'"\r\n')
                    if ordinal == 1 and first == b"machine_id":
                        header = next(csv.reader([line.decode("utf-8").strip()]))
                        if tuple(header) != EXPECTED_FIELDS:
                            raise ValueError("Unexpected CSV header.")
                        stats["header_present"] = True
                        continue
                    stats["source_rows"] += 1
                    if b'"' in line:
                        parsed = next(csv.reader([line.decode("utf-8").rstrip("\r\n")]))
                        field_count = len(parsed)
                    else:
                        parsed = None
                        field_count = line.count(b",") + 1
                    if field_count != 9:
                        stats["malformed_rows"] += 1
                        raise ValueError("CSV row does not match the nine-field schema.")
                    machine = first.decode("ascii")
                    if machine in nominated_ids:
                        if parsed is None:
                            parsed = next(csv.reader([line.decode("utf-8").rstrip("\r\n")]))
                        elapsed = _decimal(parsed[1])
                        if elapsed is None or elapsed < 0:
                            stats["unplaceable_timestamp_rows"] += 1
                            # No prefix/suffix attribution is possible, so do
                            # not use this row to replace a confirmation ID.
                            raise ValueError("Unplaceable nominated timestamp; stop without candidate reassignment.")
                        if elapsed >= WINDOW_END:
                            stats["outside_window_rows"] += 1
                        batch.append((machine, str(elapsed), float(elapsed), parsed[2],
                                      hashlib.sha256(line.rstrip(b"\r\n")).digest(), ordinal))
                        stats["nominated_rows_retained"] += 1
                        if stats["nominated_rows_retained"] > row_cap:
                            raise RuntimeError("Selected-row storage cap exceeded.")
                        if len(batch) >= 5000:
                            connection.executemany("INSERT INTO raw VALUES (?,?,?,?,?,?)", batch)
                            connection.commit()
                            batch.clear()
                    if ordinal % 1_000_000 == 0:
                        if peak_rss_bytes() > memory_stop_bytes:
                            raise MemoryError("Ingestion exceeded the recorded memory stop limit.")
                        print(json.dumps({"progress_source_rows": stats["source_rows"],
                                          "selected_rows": stats["nominated_rows_retained"],
                                          "peak_rss_bytes": peak_rss_bytes()}), flush=True)
    if not seen_member:
        raise ValueError("Usage CSV member missing.")
    if batch:
        connection.executemany("INSERT INTO raw VALUES (?,?,?,?,?,?)", batch)
        connection.commit()
    connection.execute("CREATE INDEX machine_time ON raw(machine_id,elapsed_numeric,ordinal)")
    connection.commit()
    stats.update(scan_seconds=time.monotonic() - started, peak_rss_bytes=peak_rss_bytes())
    return stats


@dataclass(frozen=True, slots=True)
class RawSample:
    elapsed: Decimal
    cpu: Decimal | None
    invalid_cpu: bool
    conflicting: bool
    raw_rows: int
    exact_duplicates: int
    same_value_timestamp_repeats: int


def unique_samples(rows):
    """Collapse only one timestamp at a time; no whole-machine list in RAM."""
    current = None
    entries = []

    def collapse(timestamp, group):
        fingerprints = set()
        payloads = []
        duplicates = 0
        for cpu_text, digest in group:
            if digest in fingerprints:
                duplicates += 1
            else:
                fingerprints.add(digest)
                parsed = _decimal(cpu_text)
                payloads.append((parsed, cpu_text.strip()))
        canonical = {("number", v) if v is not None else ("invalid", text)
                     for v, text in payloads}
        values = [v for v, _ in payloads]
        invalid = any(v is None or v < 0 or v > 100 for v in values)
        conflict = len(canonical) > 1
        cpu = None if conflict or invalid else values[0]
        return RawSample(timestamp, cpu, invalid, conflict, len(group), duplicates,
                         max(0, len(payloads) - 1) if not conflict else 0)

    for elapsed_text, cpu_text, fingerprint in rows:
        elapsed = Decimal(elapsed_text)
        if current is not None and elapsed != current:
            if elapsed < current:
                raise ValueError("SQLite timestamp order lost numeric precision.")
            yield collapse(current, entries)
            entries = []
        current = elapsed
        entries.append((cpu_text, fingerprint))
        if len(entries) > 10000:
            raise RuntimeError("Timestamp-duplicate group exceeded bounded support.")
    if current is not None:
        yield collapse(current, entries)


def machine_rows(connection, machine: str, start: int, end: int):
    return connection.execute(
        "SELECT elapsed_text,cpu_text,row_digest FROM raw WHERE machine_id=? "
        "AND elapsed_numeric>=? AND elapsed_numeric<? ORDER BY elapsed_numeric,ordinal",
        (machine, start, end),
    )


def resample(rows, *, start: int, end: int, rules: dict):
    """Right-labeled means of completed [b-300,b) bins; never fill gaps.

    All expected bins are emitted, including explicit failed bins with no mean.
    Therefore a caller cannot silently compress gaps into a shorter time axis.
    """
    if type(start) is not int or type(end) is not int or start < 0 or end <= start or start % 300 or end % 300:
        raise ValueError("Resampling bounds must define whole aligned five-minute bins.")
    samples = iter(unique_samples(rows))
    sample = next(samples, None)
    for left in range(start, end, BIN_SECONDS):
        right = left + BIN_SECONDS
        in_bin = []
        while sample is not None and sample.elapsed < right:
            if sample.elapsed < left:
                raise ValueError("Input contains an out-of-window timestamp.")
            in_bin.append(sample)
            if len(in_bin) > 10000:
                raise RuntimeError("Bin support exceeded bounded storage.")
            sample = next(samples, None)
        valid = [s for s in in_bin if s.cpu is not None]
        times = [s.elapsed for s in valid]
        gaps = [b - a for a, b in zip(times, times[1:])]
        leading = times[0] - left if times else None
        trailing = right - times[-1] if times else None
        max_gap = max(gaps, default=Decimal(0)) if times else None
        reasons = []
        if len(valid) < rules["min_valid_unique_samples_per_bin"]:
            reasons.append("insufficient_valid_unique_samples")
        if any(s.conflicting for s in in_bin):
            reasons.append("conflicting_duplicate_cpu")
        if max_gap is not None and max_gap > rules["maximum_raw_time_gap_seconds"]:
            reasons.append("raw_gap_exceeds_limit")
        if leading is None or leading > rules["bin_edge_max_distance_seconds"]:
            reasons.append("leading_edge_gap")
        if trailing is None or trailing > rules["bin_edge_max_distance_seconds"]:
            reasons.append("trailing_edge_gap")
        mean = sum((s.cpu for s in valid), Decimal(0)) / len(valid) if not reasons else None
        yield {
            "bin_end_seconds": right, "timestamp": (EPOCH + timedelta(seconds=right)).isoformat(),
            "value": float(mean) if mean is not None else None,
            "status": "valid" if not reasons else "failed", "reasons": reasons,
            "raw_rows": sum(s.raw_rows for s in in_bin), "unique_timestamps": len(in_bin),
            "valid_unique_samples": len(valid), "invalid_cpu_timestamps": sum(s.invalid_cpu for s in in_bin),
            "conflicting_timestamps": sum(s.conflicting for s in in_bin),
            "exact_duplicate_rows": sum(s.exact_duplicates for s in in_bin),
            "same_value_timestamp_repeats": sum(s.same_value_timestamp_repeats for s in in_bin),
            "max_gap_seconds": float(max_gap) if max_gap is not None else None,
            "leading_gap_seconds": float(leading) if leading is not None else None,
            "trailing_gap_seconds": float(trailing) if trailing is not None else None,
        }
    if sample is not None:
        raise ValueError("Input contains samples beyond the requested interval.")


def prefix_quality(connection, machine: str, rules: dict) -> dict:
    """This SQL path cannot access data at or after the fixed 50% cutoff."""
    previous = None
    deltas = Counter()
    first = last = None
    unique_count = 0
    for sample in unique_samples(machine_rows(connection, machine, 0, PREFIX_END)):
        unique_count += 1
        if previous is not None:
            deltas[str((sample.elapsed - previous).normalize())] += 1
        first = sample.elapsed if first is None else first
        last = sample.elapsed
        previous = sample.elapsed
    bins = list(resample(machine_rows(connection, machine, 0, PREFIX_END), start=0, end=PREFIX_END, rules=rules))
    reason_counts = Counter(reason for item in bins for reason in item["reasons"])
    mode = max(deltas, key=lambda value: (deltas[value], -Decimal(value))) if deltas else None
    ten_count = sum(count for delta, count in deltas.items() if Decimal(delta) == 10)
    total_deltas = sum(deltas.values())
    return {
        "machine_id": machine, "prefix_elapsed_interval": [0, PREFIX_END],
        "prefix_pass": all(item["status"] == "valid" for item in bins),
        "expected_bins": len(bins), "valid_bins": sum(item["status"] == "valid" for item in bins),
        "failed_bins": sum(item["status"] == "failed" for item in bins),
        "failure_reasons": dict(reason_counts), "raw_rows": sum(b["raw_rows"] for b in bins),
        "unique_timestamps": unique_count, "first_elapsed_seconds": str(first) if first is not None else None,
        "last_elapsed_seconds": str(last) if last is not None else None,
        "modal_interval_seconds": float(Decimal(mode)) if mode is not None else None,
        "ten_second_interval_count": ten_count,
        "ten_second_interval_fraction": ten_count / total_deltas if total_deltas else None,
        "delta_count": total_deltas,
        "invalid_cpu_timestamps": sum(b["invalid_cpu_timestamps"] for b in bins),
        "conflicting_timestamps": sum(b["conflicting_timestamps"] for b in bins),
        "exact_duplicate_rows": sum(b["exact_duplicate_rows"] for b in bins),
        "same_value_timestamp_repeats": sum(b["same_value_timestamp_repeats"] for b in bins),
        "first_failed_bin_end_seconds": next((b["bin_end_seconds"] for b in bins if b["status"] != "valid"), None),
    }


def choose_candidates(candidates: list[dict], prefix_results: dict[str, dict]) -> dict:
    """Same-role fixed-order reserves; no suffix qualification is consulted."""
    result = {}
    for role in ("development", "confirmation"):
        group = sorted((c for c in candidates if c["role"] == role), key=lambda c: c["role_order"])
        reserves = iter(c for c in group if c["nomination"] == "reserve" and prefix_results[c["machine_id"]]["prefix_pass"])
        selected = []
        replacements = []
        unfilled = []
        for primary in (c for c in group if c["nomination"] == "primary"):
            machine = primary["machine_id"]
            if prefix_results[machine]["prefix_pass"]:
                selected.append(machine)
            else:
                reserve = next(reserves, None)
                if reserve is None:
                    unfilled.append(machine)
                else:
                    selected.append(reserve["machine_id"])
                    replacements.append({"failed_primary": machine, "replacement": reserve["machine_id"]})
        result[role] = {"selected_ids": selected, "replacements": replacements, "unfilled_primary_slots": unfilled}
    return result


def _json_write(path: Path, payload) -> None:
    with path.open("x") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def export_raw(connection, machine: str, destination: Path, start: int, end: int) -> None:
    """Only the three required raw columns are exported; no other metrics."""
    with destination.open("xb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text:
                writer = csv.writer(text)
                writer.writerow(["machine_id", "time_stamp", "cpu_util_percent"])
                cursor = connection.execute(
                    "SELECT machine_id,elapsed_text,cpu_text FROM raw WHERE machine_id=? "
                    "AND elapsed_numeric>=? AND elapsed_numeric<? ORDER BY elapsed_numeric,ordinal",
                    (machine, start, end))
                writer.writerows(cursor)


def export_bins(connection, machine: str, destination: Path, rules: dict, start: int, end: int) -> dict:
    valid = failed = 0
    with destination.open("x", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "bin_end_seconds", "value", "quality_status", "failure_reasons"])
        for item in resample(machine_rows(connection, machine, start, end), start=start, end=end, rules=rules):
            writer.writerow([item["timestamp"], item["bin_end_seconds"], item["value"], item["status"], ";".join(item["reasons"])])
            valid += item["status"] == "valid"
            failed += item["status"] == "failed"
    return {"expected_bins": valid + failed, "valid_bins": valid, "failed_bins": failed,
            "full_window_pass": failed == 0}


def qualify(archive_path: Path, output_dir: Path, manifest: dict, candidates: list[dict],
            expected_sha256: str, expected_member_bytes: int | None = None) -> dict:
    """Versioned run; confirmation suffix details remain only in sealed files."""
    preflight = require_resources(output_dir.parent)
    verification = verify_archive(archive_path, expected_sha256)
    output_dir.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    rules = manifest["preprocessing"]["resampling"]
    for folder in ("raw_prefix", "five_minute_prefix", "development_suffix", "sealed_confirmation"):
        (output_dir / folder).mkdir(mode=0o700)
    staging_path = output_dir / "staging.sqlite"
    connection = create_staging(staging_path)
    try:
        stats = stage_archive(archive_path, connection, {c["machine_id"] for c in candidates},
                              expected_member_bytes=expected_member_bytes)
        prefix_results = {c["machine_id"]: prefix_quality(connection, c["machine_id"], rules) for c in candidates}
        selection = choose_candidates(candidates, prefix_results)
        artifacts = []
        development_suffix_quality = {}
        for candidate in candidates:
            machine = candidate["machine_id"]
            prefix_raw = output_dir / "raw_prefix" / f"{machine}.csv.gz"
            prefix_bins = output_dir / "five_minute_prefix" / f"{machine}.csv"
            export_raw(connection, machine, prefix_raw, 0, PREFIX_END)
            export_bins(connection, machine, prefix_bins, rules, 0, PREFIX_END)
            folder = "sealed_confirmation" if candidate["role"] == "confirmation" else "development_suffix"
            suffix_raw = output_dir / folder / f"{machine}.raw.csv.gz"
            suffix_bins = output_dir / folder / f"{machine}.five_minute.csv"
            export_raw(connection, machine, suffix_raw, PREFIX_END, WINDOW_END)
            suffix_quality = export_bins(connection, machine, suffix_bins, rules, PREFIX_END, WINDOW_END)
            if candidate["role"] == "confirmation":
                # No suffix counts/quality/values are exposed in public logs.
                sealed_qc = output_dir / folder / f"{machine}.technical_quality.json"
                _json_write(sealed_qc, suffix_quality)
                paths = (prefix_raw, prefix_bins, suffix_raw, suffix_bins, sealed_qc)
            else:
                development_suffix_quality[machine] = suffix_quality
                paths = (prefix_raw, prefix_bins, suffix_raw, suffix_bins)
            for path in paths:
                sealed = path.parent.name == "sealed_confirmation"
                artifacts.append({"path": str(path.relative_to(output_dir)), "sha256": sha256_file(path),
                                  "sealed": sealed, "bytes": path.stat().st_size})
                if sealed:
                    path.chmod(0)  # accidental-access guard, not cryptographic protection
        # Stage contains all nominated raw columns, including sealed suffixes.
        connection.close()
        connection = None
        staging_path.chmod(0)
        dev_selected = selection["development"]["selected_ids"]
        cadence_verified = bool(dev_selected) and all(prefix_results[m]["modal_interval_seconds"] == 10 for m in dev_selected)
        full_dev = [m for m in dev_selected if development_suffix_quality[m]["full_window_pass"]]
        result = {
            "schema_version": "dafr_m2b_qualification_v1", "milestone": "M2B",
            "source": verification, "resource_preflight": preflight, "scan": stats,
            "nominees": candidates, "prefix_quality": prefix_results, "selection": selection,
            "development_suffix_technical_quality": development_suffix_quality,
            "development_prefix_nominal_ten_seconds_verified": cadence_verified,
            "complete_development_ids": full_dev,
            "ready_for_M3_development": len(full_dev) == 3 and cadence_verified,
            "confirmation_execution_allowed": False,
            "confirmation_forecasting_outcomes_inspected": False,
            "confirmation_suffix_human_inspected": False,
            "confirmation_suffix_mechanical_processing": True,
            "confirmation_suffix_policy": "Only technical parsing/binning/hashing. No statistics/plots, model errors or human value inspection. Files mode 000; staging mode 000; not cryptographic encryption.",
            "artifacts": artifacts, "runtime_seconds_excluding_download_and_checksum": time.monotonic() - started,
            "peak_process_rss_bytes": peak_rss_bytes(), "trained_models": [],
            "partitions": manifest["partitions"], "preprocessing_rules": manifest["preprocessing"],
        }
        _json_write(output_dir / "qualification.json", result)
        return result
    except Exception as error:
        _json_write(output_dir / "failure.json", {"error_type": type(error).__name__,
                    "message": str(error), "confirmation_execution_allowed": False,
                    "runtime_seconds": time.monotonic() - started})
        raise
    finally:
        if connection is not None:
            connection.close()
        if staging_path.exists():
            staging_path.chmod(0)


def seal_artifacts(output_dir: Path, key_path: Path) -> dict:
    """Encrypt generated suffix/staging files without displaying their contents.

    Permission bits alone are unreliable in workspace tools that restore read
    access. Ciphertexts and plaintext hashes are linked by an immutable receipt.
    Only generated plaintext files are removed, after ALL encryptions have been
    verified by a streaming decrypt-to-hash check. No decoded CSV is inspected.
    The official compressed source archive is intentionally retained separately.
    """
    started = time.monotonic()
    receipt_path = output_dir / "seal_receipt_v1.json"
    if receipt_path.exists():
        raise FileExistsError("Run is already sealed; refusing to overwrite its receipt.")
    qualification = json.loads((output_dir / "qualification.json").read_text())
    inputs = [(output_dir / item["path"], item["sha256"])
              for item in qualification["artifacts"] if item["sealed"]]
    inputs.append((output_dir / "staging.sqlite", None))
    root = output_dir.resolve()
    for path, _ in inputs:
        if not path.resolve().is_relative_to(root) or not (
            path.parent.name == "sealed_confirmation" or path == output_dir / "staging.sqlite"
        ):
            raise ValueError("Encryption target is outside this run's generated holdout artifacts.")
    key_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(key_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w") as key_file:
        key_file.write(secrets.token_hex(48) + "\n")
    records = []
    for path, expected in inputs:
        path.chmod(0o400)  # controlled mechanical read; no analytical access
        original_hash = sha256_file(path)
        if expected is not None and original_hash != expected:
            raise ValueError("Generated holdout artifact changed before sealing.")
        encrypted = path.with_name(path.name + ".aes256")
        arguments = ["openssl", "enc", "-aes-256-cbc", "-salt", "-pbkdf2", "-iter", "200000",
                     "-md", "sha256", "-pass", f"file:{key_path}"]
        with encrypted.open("xb") as destination:
            subprocess.run(arguments + ["-in", str(path)], stdout=destination,
                           stderr=subprocess.PIPE, check=True)
        digest = hashlib.sha256()
        process = subprocess.Popen(arguments + ["-d", "-in", str(encrypted)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for block in iter(lambda: process.stdout.read(1024 * 1024), b""):
            digest.update(block)
        process.stdout.close()
        error_output = process.stderr.read()
        process.stderr.close()
        if process.wait() != 0 or digest.hexdigest() != original_hash:
            raise RuntimeError("Ciphertext recovery check failed; plaintext files retained.")
        records.append({"original_path": str(path.relative_to(output_dir)),
                        "original_sha256": original_hash,
                        "encrypted_path": str(encrypted.relative_to(output_dir)),
                        "encrypted_sha256": sha256_file(encrypted),
                        "encrypted_bytes": encrypted.stat().st_size,
                        "recovery_hash_verified": True})
    for path, _ in inputs:
        path.unlink()  # only newly generated intermediates, verified recoverable above
    receipt = {"schema_version": "dafr_m2b_seal_receipt_v1", "cipher": "AES-256-CBC",
               "key_derivation": "PBKDF2-HMAC-SHA256", "iterations": 200000,
               "local_key_path": str(key_path), "records": records,
               "generated_plaintext_removed": True, "human_suffix_values_inspected": False,
               "runtime_seconds": time.monotonic() - started,
               "note": "Research holdout access guard; local key and public source archive are accessible to the project owner. No production confidentiality claim."}
    _json_write(receipt_path, receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    from .contracts import identifier
    identifier(args.run_id)
    manifest = json.loads((ROOT / "configs/dafr_experiment_manifest_v1.json").read_text())
    inventory = json.loads((ROOT / "reports/dafr/m2_dataset_inventory_v1.json").read_text())
    parent = ROOT / "data/processed/dafr/m2b_v1"
    parent.mkdir(parents=True, exist_ok=True)
    output = parent / args.run_id
    if parent.resolve() != parent:
        raise ValueError("Output must not be redirected through symlinks.")
    result = qualify(args.archive, output, manifest, inventory["alibaba"]["candidates"],
                     manifest["source"]["usage_sha256_expected"],
                     manifest["resource_plan"]["machine_usage_declared_csv_bytes"])
    seal_artifacts(output, ROOT / "data/external/alibaba2018/m2b_v1" / f"{args.run_id}.vault.key")
    print(json.dumps({"output": str(output), "selection": result["selection"],
                      "ready_for_M3_development": result["ready_for_M3_development"],
                      "runtime_seconds": result["runtime_seconds_excluding_download_and_checksum"],
                      "peak_process_rss_bytes": result["peak_process_rss_bytes"]}), flush=True)


if __name__ == "__main__":
    main()

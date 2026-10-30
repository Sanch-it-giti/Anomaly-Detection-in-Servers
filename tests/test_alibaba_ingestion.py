"""M2B tests use tiny synthetic archives, never the real confirmation suffix."""

from __future__ import annotations

import csv
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import stat
import sys
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dafr.alibaba_ingestion import (  # noqa: E402
    EXPECTED_FIELDS, bounded_lines, choose_candidates, create_staging, machine_rows,
    prefix_quality, qualify, require_resources, resample, sha256_file,
    seal_artifacts, stage_archive, unique_samples, verify_archive,
)

MANIFEST = json.loads((ROOT / "configs/dafr_experiment_manifest_v1.json").read_text())
RULES = MANIFEST["preprocessing"]["resampling"]


def sample_rows(count=30, start=0, value=40):
    return [(str(start + i * 10), str(value), hashlib.sha256(f"{start+i*10},{value}".encode()).digest())
            for i in range(count)]


def csv_row(machine, seconds, cpu, extra="0"):
    return [machine, str(seconds), str(cpu), extra, "0", "0", "0", "0", "0"]


def archive_fixture(path, rows, header=False, extra_member=False):
    text = io.StringIO(newline="")
    writer = csv.writer(text)
    if header:
        writer.writerow(EXPECTED_FIELDS)
    writer.writerows(rows)
    payload = text.getvalue().encode()
    with tarfile.open(path, "w:gz") as archive:
        member = tarfile.TarInfo("machine_usage.csv")
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))
        if extra_member:
            member = tarfile.TarInfo("container_usage.csv")
            member.size = 1
            archive.addfile(member, io.BytesIO(b"x"))


class ArchiveTests(unittest.TestCase):
    def test_row_allocation_is_bounded_before_rejection(self):
        handle = io.BytesIO(b"x" * 1000000)
        with self.assertRaises(ValueError):
            list(bounded_lines(handle, maximum_bytes=64))
        self.assertEqual(handle.tell(), 65)
        self.assertEqual(list(bounded_lines(io.BytesIO(b"first\nsecond\n"))), [b"first\n", b"second\n"])

    def test_disk_gate_rejects_less_than_four_gib(self):
        with patch("dafr.alibaba_ingestion.shutil.disk_usage") as usage:
            usage.return_value.free = 4 * 1024**3 - 1
            with self.assertRaises(RuntimeError):
                require_resources(ROOT)

    def test_checksum_mismatch_stops_before_any_output_is_created(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "synthetic.tar.gz"
            archive_fixture(archive, [csv_row("m_1", 0, 40)])
            with self.assertRaises(ValueError):
                qualify(archive, root / "run", MANIFEST, [], "0" * 64)
            self.assertFalse((root / "run").exists())
            self.assertTrue(verify_archive(archive, sha256_file(archive))["verified"])

    def test_only_nominated_ids_and_three_fields_plus_provenance_are_retained(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "synthetic.tar.gz"
            archive_fixture(archive, [csv_row("m_1", 10, 40), csv_row("m_other", 0, "ignored"),
                                      csv_row("m_1", 0, 30)], header=True)
            with create_staging(root / "stage.sqlite") as connection:
                result = stage_archive(archive, connection, {"m_1"})
                self.assertEqual(result["source_rows"], 3)
                self.assertEqual(result["nominated_rows_retained"], 2)
                self.assertTrue(result["header_present"])
                rows = list(machine_rows(connection, "m_1", 0, 300))
                self.assertEqual([r[0] for r in rows], ["0", "10"])
                self.assertEqual(connection.execute("SELECT DISTINCT machine_id FROM raw").fetchall(), [("m_1",)])
                columns = [r[1] for r in connection.execute("PRAGMA table_info(raw)")]
                self.assertNotIn("mem_util_percent", columns)
                self.assertNotIn("net_in", columns)

    def test_bad_schema_or_unrelated_member_is_rejected(self):
        for rows, extra in (([["m_1", "0", "40"]], False), ([csv_row("m_1", 0, 40)], True)):
            with TemporaryDirectory() as directory:
                root = Path(directory)
                archive = root / "synthetic.tar.gz"
                archive_fixture(archive, rows, extra_member=extra)
                with create_staging(root / "stage.sqlite") as connection:
                    with self.assertRaises(ValueError):
                        stage_archive(archive, connection, {"m_1"})

    def test_invalid_timestamp_is_not_used_to_reassign_candidates(self):
        for timestamp in ("NaN", "Infinity", "-1", ""):
            with self.subTest(timestamp=timestamp), TemporaryDirectory() as directory:
                root = Path(directory)
                archive = root / "synthetic.tar.gz"
                archive_fixture(archive, [csv_row("m_1", timestamp, 40)])
                with create_staging(root / "stage.sqlite") as connection:
                    with self.assertRaises(ValueError):
                        stage_archive(archive, connection, {"m_1"})

    def test_decimal_timestamps_preserve_original_precision(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "synthetic.tar.gz"
            archive_fixture(archive, [csv_row("m_1", "10.125", 40), csv_row("m_1", "0.125", 40)])
            with create_staging(root / "stage.sqlite") as connection:
                stage_archive(archive, connection, {"m_1"})
                samples = list(unique_samples(machine_rows(connection, "m_1", 0, 300)))
                self.assertEqual([s.elapsed for s in samples], [Decimal("0.125"), Decimal("10.125")])

    def test_row_and_memory_limits_fail_closed(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "synthetic.tar.gz"
            archive_fixture(archive, [csv_row("m_1", 0, 40), csv_row("m_1", 10, 40)])
            with create_staging(root / "stage.sqlite") as connection:
                with self.assertRaises(RuntimeError):
                    stage_archive(archive, connection, {"m_1"}, row_cap=1)
                with self.assertRaises(MemoryError):
                    stage_archive(archive, connection, {"m_1"}, memory_stop_bytes=1)


class BinningTests(unittest.TestCase):
    def aggregate(self, rows, end=300):
        return list(resample(rows, start=0, end=end, rules=RULES))

    def test_completed_bin_boundary_never_reads_next_bin_into_previous_mean(self):
        bins = self.aggregate(sample_rows(value=10) + sample_rows(start=300, value=90), end=600)
        self.assertEqual([b["value"] for b in bins], [10., 90.])
        self.assertEqual([b["bin_end_seconds"] for b in bins], [300, 600])
        self.assertTrue(bins[0]["timestamp"].endswith("00:05:00+00:00"))

    def test_exact_full_row_duplicates_do_not_change_unique_support_or_mean(self):
        rows = sample_rows()
        rows.insert(1, rows[0])
        result = self.aggregate(rows)[0]
        self.assertEqual(result["raw_rows"], 31)
        self.assertEqual(result["valid_unique_samples"], 30)
        self.assertEqual(result["exact_duplicate_rows"], 1)
        self.assertEqual(result["value"], 40.)

    def test_same_cpu_timestamp_with_changed_auxiliary_field_counts_once(self):
        rows = sample_rows()
        rows.insert(1, ("0", "40.0", b"different auxiliary fields"))
        result = self.aggregate(rows)[0]
        self.assertEqual(result["same_value_timestamp_repeats"], 1)
        self.assertEqual(result["valid_unique_samples"], 30)
        self.assertEqual(result["status"], "valid")

    def test_conflicting_cpu_at_same_timestamp_invalidates_bin(self):
        rows = sample_rows()
        rows.insert(1, ("0", "60", b"different CPU"))
        result = self.aggregate(rows)[0]
        self.assertEqual(result["conflicting_timestamps"], 1)
        self.assertIn("conflicting_duplicate_cpu", result["reasons"])
        self.assertIsNone(result["value"])

    def test_invalid_and_missing_cpu_values_are_counted_without_clipping(self):
        rows = sample_rows()
        for index, payload in zip((2, 6, 10, 14, 18, 22), ("NaN", "Infinity", "", "-1", "101", "bad")):
            rows[index] = (rows[index][0], payload, hashlib.sha256(payload.encode()).digest())
        result = self.aggregate(rows)[0]
        self.assertEqual(result["invalid_cpu_timestamps"], 6)
        self.assertEqual(result["valid_unique_samples"], 24)
        self.assertEqual(result["value"], 40.)

    def test_minimum_sample_count_is_exactly_twenty_four(self):
        rows = [row for index, row in enumerate(sample_rows()) if index not in (1, 6, 11, 16, 21, 26)]
        self.assertEqual(self.aggregate(rows)[0]["status"], "valid")
        del rows[-2]
        result = self.aggregate(rows)[0]
        self.assertEqual(result["valid_unique_samples"], 23)
        self.assertIn("insufficient_valid_unique_samples", result["reasons"])

    def test_gap_over_thirty_seconds_rejected_without_interpolation(self):
        rows = [row for index, row in enumerate(sample_rows()) if index not in (5, 6, 7)]
        result = self.aggregate(rows)[0]
        self.assertEqual(result["max_gap_seconds"], 40.)
        self.assertIn("raw_gap_exceeds_limit", result["reasons"])
        self.assertIsNone(result["value"])

    def test_thirty_second_edge_is_allowed_but_forty_is_not(self):
        self.assertEqual(self.aggregate(sample_rows()[3:])[0]["status"], "valid")
        self.assertIn("leading_edge_gap", self.aggregate(sample_rows()[4:])[0]["reasons"])
        self.assertEqual(self.aggregate(sample_rows()[:-2])[0]["status"], "valid")
        self.assertIn("trailing_edge_gap", self.aggregate(sample_rows()[:-3])[0]["reasons"])

    def test_empty_bins_remain_in_grid_as_failed_without_fabricated_values(self):
        bins = self.aggregate([], end=600)
        self.assertEqual(len(bins), 2)
        self.assertTrue(all(b["status"] == "failed" and b["value"] is None for b in bins))

    def test_misaligned_window_bounds_rejected(self):
        for start, end in ((0, 450), (-300, 300), (0, 0), (1, 300)):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                list(resample([], start=start, end=end, rules=RULES))


class QualificationTests(unittest.TestCase):
    def test_encrypted_seal_verifies_recovery_before_removing_generated_plaintext(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            sealed = root / "sealed_confirmation"
            sealed.mkdir()
            fixture = sealed / "synthetic.csv"
            fixture.write_bytes(b"synthetic fixture only\n")
            staging = root / "staging.sqlite"
            staging.write_bytes(b"synthetic staging fixture\n")
            expected = sha256_file(fixture)
            (root / "qualification.json").write_text(json.dumps({"artifacts": [
                {"path": "sealed_confirmation/synthetic.csv", "sha256": expected, "sealed": True}]}))
            receipt = seal_artifacts(root, root / "private.key")
            self.assertFalse(fixture.exists())
            self.assertFalse(staging.exists())
            self.assertEqual(len(receipt["records"]), 2)
            self.assertTrue(all(r["recovery_hash_verified"] for r in receipt["records"]))
            for record in receipt["records"]:
                self.assertTrue((root / record["encrypted_path"]).exists())
                self.assertEqual(sha256_file(root / record["encrypted_path"]), record["encrypted_sha256"])
            with self.assertRaises(FileExistsError):
                seal_artifacts(root, root / "private.key")

    def test_future_values_do_not_change_prefix_quality(self):
        with TemporaryDirectory() as directory:
            reports = []
            for number, suffix_cpu in enumerate((40, 999)):
                root = Path(directory)
                archive = root / f"synthetic{number}.tar.gz"
                rows = [csv_row("m_1", i*10, 40) for i in range(60)]
                rows += [csv_row("m_1", 345600+i*10, suffix_cpu) for i in range(30)]
                archive_fixture(archive, rows)
                with create_staging(root / f"stage{number}.sqlite") as connection:
                    stage_archive(archive, connection, {"m_1"})
                    reports.append(prefix_quality(connection, "m_1", RULES))
            self.assertEqual(*reports)
            self.assertEqual(reports[0]["raw_rows"], 60)

    def test_reserve_replacement_is_same_role_and_fixed_order(self):
        candidates = [
            {"machine_id": "d1", "role": "development", "nomination": "primary", "role_order": 1},
            {"machine_id": "dr1", "role": "development", "nomination": "reserve", "role_order": 2},
            {"machine_id": "dr2", "role": "development", "nomination": "reserve", "role_order": 3},
            {"machine_id": "c1", "role": "confirmation", "nomination": "primary", "role_order": 1},
            {"machine_id": "cr1", "role": "confirmation", "nomination": "reserve", "role_order": 2},
        ]
        quality = {c["machine_id"]: {"prefix_pass": c["nomination"] == "reserve"} for c in candidates}
        result = choose_candidates(list(reversed(candidates)), quality)
        self.assertEqual(result["development"]["selected_ids"], ["dr1"])
        self.assertEqual(result["confirmation"]["selected_ids"], ["cr1"])
        quality["cr1"]["prefix_pass"] = False
        result = choose_candidates(candidates, quality)
        self.assertEqual(result["confirmation"]["selected_ids"], [])
        self.assertEqual(result["confirmation"]["unfilled_primary_slots"], ["c1"])

    def test_versioned_outputs_and_confirmation_suffix_access_guard(self):
        candidates = [{"machine_id": "d1", "role": "development", "nomination": "primary", "role_order": 1},
                      {"machine_id": "c1", "role": "confirmation", "nomination": "primary", "role_order": 1}]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "synthetic.tar.gz"
            rows = [csv_row(machine, i*10, 40) for machine in ("d1", "c1") for i in range(120)]
            archive_fixture(archive, rows)
            with patch("dafr.alibaba_ingestion.PREFIX_END", 600), patch("dafr.alibaba_ingestion.WINDOW_END", 1200):
                result = qualify(archive, root / "run", MANIFEST, candidates, sha256_file(archive))
                self.assertFalse(result["confirmation_execution_allowed"])
                self.assertNotIn("c1", result["development_suffix_technical_quality"])
                self.assertEqual(result["selection"]["confirmation"]["selected_ids"], ["c1"])
                for artifact in result["artifacts"]:
                    path = root / "run" / artifact["path"]
                    if artifact["sealed"]:
                        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0)
                self.assertEqual(stat.S_IMODE((root / "run/staging.sqlite").stat().st_mode), 0)
                before = (root / "run/qualification.json").read_bytes()
                with self.assertRaises(FileExistsError):
                    qualify(archive, root / "run", MANIFEST, candidates, sha256_file(archive))
                self.assertEqual(before, (root / "run/qualification.json").read_bytes())


if __name__ == "__main__":
    unittest.main()

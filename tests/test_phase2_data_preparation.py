"""Lightweight checks for the leakage-safe Phase 2 preparation functions."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from data_preparation import chronological_split, load_and_validate_series  # noqa: E402


class Phase2DataPreparationTests(unittest.TestCase):
    """Confirm the selected series still meets the project data contract."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.series = load_and_validate_series()

    def test_series_has_expected_observations_and_interval(self) -> None:
        self.assertEqual(len(self.series), 4032)
        intervals = self.series["timestamp"].diff().dropna()
        self.assertTrue(intervals.eq("5min").all())

    def test_default_split_is_contiguous_and_non_overlapping(self) -> None:
        train, test, summary = chronological_split(self.series)
        self.assertEqual((len(train), len(test)), (3226, 806))
        self.assertLess(train["timestamp"].iloc[-1], test["timestamp"].iloc[0])
        self.assertEqual(summary.train_end, train["timestamp"].iloc[-1])
        self.assertEqual(summary.test_start, test["timestamp"].iloc[0])


if __name__ == "__main__":
    unittest.main()

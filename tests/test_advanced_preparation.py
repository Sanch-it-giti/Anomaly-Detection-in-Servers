"""Tests guarding Phase 3 against test-period leakage."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from advanced_preparation import MinMaxScaler, make_lagged_training_examples, recursive_forecast  # noqa: E402


class AdvancedPreparationTests(unittest.TestCase):
    def test_lagged_examples_use_only_past_values(self) -> None:
        features, targets = make_lagged_training_examples([10, 20, 30, 40, 50], (1, 2))
        np.testing.assert_array_equal(features, [[20, 10], [30, 20], [40, 30]])
        np.testing.assert_array_equal(targets, [30, 40, 50])

    def test_recursive_forecast_does_not_receive_test_actuals(self) -> None:
        # A model returning the most recent lag makes the expected recursion
        # explicit: later predictions must depend on previous predictions.
        forecast = recursive_forecast(lambda row: row[0, 0], [1, 2, 3], (1,), horizon=4)
        np.testing.assert_array_equal(forecast, [3, 3, 3, 3])

    def test_scaler_is_fitted_on_train_values_only(self) -> None:
        scaler = MinMaxScaler.fit([10, 20, 30])
        np.testing.assert_allclose(scaler.transform([10, 20, 30, 40]), [0, 0.5, 1, 1.5])
        np.testing.assert_allclose(scaler.inverse_transform([0, 0.5, 1]), [10, 20, 30])


if __name__ == "__main__":
    unittest.main()

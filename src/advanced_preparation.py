"""Leakage-safe supervised-data helpers for the Phase 3 forecasting models.

XGBoost and LSTM will use the same fixed chronological split defined in
``data_preparation.py``.  These helpers make examples from training history
only and support recursive test forecasting, so no future test observation is
used as an input when predicting the next one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np


@dataclass(frozen=True)
class MinMaxScaler:
    """A simple scaler whose parameters are fitted on training values only."""

    minimum: float
    maximum: float

    @classmethod
    def fit(cls, values: Sequence[float]) -> "MinMaxScaler":
        """Fit scaling bounds using only a supplied training sequence."""

        array = np.asarray(values, dtype=float)
        if array.ndim != 1 or len(array) == 0:
            raise ValueError("Values must be a non-empty one-dimensional sequence.")
        minimum, maximum = float(array.min()), float(array.max())
        if minimum == maximum:
            raise ValueError("Cannot scale a constant series.")
        return cls(minimum=minimum, maximum=maximum)

    def transform(self, values: Sequence[float]) -> np.ndarray:
        """Apply the fitted bounds without refitting them."""

        return (np.asarray(values, dtype=float) - self.minimum) / (self.maximum - self.minimum)

    def inverse_transform(self, values: Sequence[float]) -> np.ndarray:
        """Return scaled values to the original CPU-utilization scale."""

        return np.asarray(values, dtype=float) * (self.maximum - self.minimum) + self.minimum


def make_lagged_training_examples(
    values: Sequence[float], lags: Sequence[int]
) -> tuple[np.ndarray, np.ndarray]:
    """Make one-step-ahead features and targets from *training* values only.

    For example, lags ``(1, 3)`` at index ``t`` become features
    ``[value[t-1], value[t-3]]`` with target ``value[t]``.  The input order is
    preserved deliberately; model scripts must document the chosen lag set.
    """

    array = np.asarray(values, dtype=float)
    lag_array = np.asarray(lags, dtype=int)
    if array.ndim != 1:
        raise ValueError("Values must be one-dimensional.")
    if len(lag_array) == 0 or np.any(lag_array <= 0):
        raise ValueError("Lags must contain one or more positive integers.")
    max_lag = int(lag_array.max())
    if len(array) <= max_lag:
        raise ValueError("Training values must be longer than the largest lag.")

    features = np.array(
        [[array[index - lag] for lag in lag_array] for index in range(max_lag, len(array))],
        dtype=float,
    )
    targets = array[max_lag:].copy()
    return features, targets


def recursive_forecast(
    predict_one: Callable[[np.ndarray], float],
    training_history: Sequence[float],
    lags: Sequence[int],
    horizon: int,
) -> np.ndarray:
    """Forecast a horizon without consuming observed test-period values.

    ``predict_one`` receives exactly one lag-feature row. Each prediction is
    appended to the available history before forming the next row, matching a
    genuine multi-step forecast scenario.
    """

    if horizon <= 0:
        raise ValueError("Forecast horizon must be positive.")
    history = list(np.asarray(training_history, dtype=float))
    lag_array = np.asarray(lags, dtype=int)
    if len(lag_array) == 0 or np.any(lag_array <= 0):
        raise ValueError("Lags must contain one or more positive integers.")
    if len(history) < int(lag_array.max()):
        raise ValueError("Training history is shorter than the largest lag.")

    forecasts: list[float] = []
    for _ in range(horizon):
        row = np.array([[history[-lag] for lag in lag_array]], dtype=float)
        predicted_values = np.asarray(predict_one(row), dtype=float).reshape(-1)
        if predicted_values.size != 1:
            raise ValueError("The one-step prediction function must return exactly one value.")
        prediction = float(predicted_values[0])
        forecasts.append(prediction)
        history.append(prediction)
    return np.asarray(forecasts, dtype=float)

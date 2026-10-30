"""Classical forecasting utilities for Phase 2.

The ARIMA candidate grid is selected with training data only. The test period is
reserved for one final evaluation of the selected candidate.
"""

from __future__ import annotations

from dataclasses import dataclass
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA, ARIMAResults


@dataclass(frozen=True)
class ArimaSelection:
    """Selected ARIMA order and its training-only AIC."""

    order: tuple[int, int, int]
    aic: float
    result: ARIMAResults


def select_arima_by_aic(
    training_values: pd.Series, p_values: range = range(0, 3), q_values: range = range(0, 3)
) -> ArimaSelection:
    """Fit a small ARIMA(p, 1, q) grid and return the lowest-AIC candidate.

    The differencing order of 1 follows the training-only stationarity tests.
    This intentionally small grid is appropriate for the short project timeline
    and is not a claim of exhaustive hyperparameter optimisation.
    """

    candidates: list[ArimaSelection] = []
    for p in p_values:
        for q in q_values:
            order = (p, 1, q)
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    fitted = ARIMA(
                        training_values,
                        order=order,
                        enforce_stationarity=False,
                        enforce_invertibility=False,
                    ).fit()
                candidates.append(ArimaSelection(order=order, aic=float(fitted.aic), result=fitted))
            except (ValueError, np.linalg.LinAlgError):
                # Unsupported or numerically unstable orders are not candidates.
                continue

    if not candidates:
        raise RuntimeError("No ARIMA candidate fitted successfully.")
    return min(candidates, key=lambda candidate: candidate.aic)


def forecast_selected_arima(selection: ArimaSelection, horizon: int) -> pd.Series:
    """Produce a recursive forecast for a future horizon."""

    if horizon <= 0:
        raise ValueError("Forecast horizon must be positive.")
    return selection.result.forecast(steps=horizon)


def regression_metrics(actual: pd.Series, forecast: pd.Series) -> dict[str, float]:
    """Calculate MAE, RMSE, and MAPE for aligned positive-valued observations."""

    actual_array = np.asarray(actual, dtype=float)
    forecast_array = np.asarray(forecast, dtype=float)
    if actual_array.shape != forecast_array.shape:
        raise ValueError("Actual and forecast arrays must have identical shapes.")
    if np.any(actual_array == 0):
        raise ValueError("MAPE is undefined when an actual value is zero.")

    errors = actual_array - forecast_array
    return {
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(np.square(errors)))),
        "mape": float(np.mean(np.abs(errors / actual_array)) * 100),
    }

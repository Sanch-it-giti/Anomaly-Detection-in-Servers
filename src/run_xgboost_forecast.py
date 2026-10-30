"""Train and evaluate a leakage-safe XGBoost CPU-utilization forecast."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from advanced_preparation import make_lagged_training_examples, recursive_forecast
from classical_models import regression_metrics
from data_preparation import chronological_split, load_and_validate_series


FORECAST_OUTPUT_PATH = Path("data/processed/xgboost_holdout_forecast.csv")
# These are past observations at 5-minute offsets. They provide short-term
# memory up to two hours; they do not assert a daily or weekly seasonal cycle.
LAGS = (1, 2, 3, 6, 12, 24)
VALIDATION_FRACTION = 0.20


@dataclass(frozen=True)
class XGBoostConfiguration:
    """Small, predeclared configuration for an educational model comparison."""

    max_depth: int
    learning_rate: float
    n_estimators: int


CONFIGURATIONS = (
    XGBoostConfiguration(max_depth=2, learning_rate=0.05, n_estimators=200),
    XGBoostConfiguration(max_depth=3, learning_rate=0.05, n_estimators=300),
    XGBoostConfiguration(max_depth=3, learning_rate=0.10, n_estimators=200),
)


def build_model(configuration: XGBoostConfiguration) -> XGBRegressor:
    """Return a deterministic one-step XGBoost regressor."""

    return XGBRegressor(
        objective="reg:squarederror",
        max_depth=configuration.max_depth,
        learning_rate=configuration.learning_rate,
        n_estimators=configuration.n_estimators,
        random_state=42,
        n_jobs=1,
        verbosity=0,
    )


def fit_xgboost(values: np.ndarray, configuration: XGBoostConfiguration) -> XGBRegressor:
    """Fit one model using only supervised examples from the supplied history."""

    features, targets = make_lagged_training_examples(values, LAGS)
    model = build_model(configuration)
    model.fit(features, targets)
    return model


def choose_configuration(training_values: np.ndarray) -> tuple[XGBoostConfiguration, float]:
    """Choose by recursive MAE on a final chronological validation segment."""

    validation_size = int(len(training_values) * VALIDATION_FRACTION)
    fitting_values = training_values[:-validation_size]
    validation_actual = training_values[-validation_size:]
    candidates: list[tuple[XGBoostConfiguration, float]] = []

    for configuration in CONFIGURATIONS:
        model = fit_xgboost(fitting_values, configuration)
        validation_forecast = recursive_forecast(
            model.predict, fitting_values, LAGS, horizon=len(validation_actual)
        )
        candidates.append((configuration, regression_metrics(validation_actual, validation_forecast)["mae"]))

    return min(candidates, key=lambda candidate: candidate[1])


def main() -> None:
    """Select inside training, refit, then evaluate once on the final test period."""

    series = load_and_validate_series()
    train, test, _ = chronological_split(series)
    training_values = train["value"].to_numpy(dtype=float)
    test_values = test["value"].to_numpy(dtype=float)

    selected, validation_mae = choose_configuration(training_values)
    final_model = fit_xgboost(training_values, selected)
    forecast = recursive_forecast(final_model.predict, training_values, LAGS, horizon=len(test))
    metrics = regression_metrics(test_values, forecast)

    output = pd.DataFrame(
        {
            "timestamp": test["timestamp"].to_numpy(),
            "actual": test_values,
            "xgboost_forecast": forecast,
        }
    )
    FORECAST_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(FORECAST_OUTPUT_PATH, index=False)

    print(f"Selected configuration: {selected}")
    print(f"Training-only validation MAE: {validation_mae:.4f}")
    print(f"MAE: {metrics['mae']:.4f}")
    print(f"RMSE: {metrics['rmse']:.4f}")
    print(f"MAPE: {metrics['mape']:.4f}%")
    print(f"Saved holdout forecast: {FORECAST_OUTPUT_PATH}")


if __name__ == "__main__":
    main()

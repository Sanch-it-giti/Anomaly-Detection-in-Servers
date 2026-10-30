"""Fit and evaluate the reproducible Phase 2 ARIMA baseline."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from classical_models import regression_metrics, select_arima_by_aic
from data_preparation import chronological_split, load_and_validate_series


FORECAST_OUTPUT_PATH = Path("data/processed/arima_212_holdout_forecast.csv")
FIGURE_OUTPUT_PATH = Path("reports/figures/02_arima_holdout_forecast.png")


def save_forecast_plot(output: pd.DataFrame) -> None:
    """Save a visual comparison after the final forecast has been produced.

    Plotting is intentionally separate from model selection and evaluation.
    Some minimal Python environments cannot initialise a plotting backend, so
    a plotting problem must not prevent the numerical experiment from running.
    """

    import matplotlib.pyplot as plt

    FIGURE_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(output["timestamp"], output["actual"], label="Actual CPU utilization", color="#2A6F97")
    ax.plot(output["timestamp"], output["arima_forecast"], label="ARIMA(2,1,2) forecast", color="#E76F51")
    ax.fill_between(
        output["timestamp"],
        output["lower_95"],
        output["upper_95"],
        color="#E76F51",
        alpha=0.18,
        label="95% forecast interval",
    )
    ax.set_title("ARIMA Hold-out Forecast: Actual vs Predicted CPU Utilization")
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("CPU utilization")
    ax.legend()
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(FIGURE_OUTPUT_PATH, dpi=150)
    plt.close(fig)


def main(save_plot: bool = False) -> None:
    """Select on training data, then evaluate one forecast on the held-out period."""

    series = load_and_validate_series()
    train, test, _ = chronological_split(series)

    selection = select_arima_by_aic(train["value"])
    forecast_result = selection.result.get_forecast(steps=len(test))
    forecast = forecast_result.predicted_mean
    intervals = forecast_result.conf_int(alpha=0.05)
    metrics = regression_metrics(test["value"], forecast)

    output = pd.DataFrame(
        {
            "timestamp": test["timestamp"].to_numpy(),
            "actual": test["value"].to_numpy(),
            "arima_forecast": forecast.to_numpy(),
            "lower_95": intervals.iloc[:, 0].to_numpy(),
            "upper_95": intervals.iloc[:, 1].to_numpy(),
        }
    )
    FORECAST_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(FORECAST_OUTPUT_PATH, index=False)

    print(f"Selected order: ARIMA{selection.order}")
    print(f"Training AIC: {selection.aic:.4f}")
    print(f"MAE: {metrics['mae']:.4f}")
    print(f"RMSE: {metrics['rmse']:.4f}")
    print(f"MAPE: {metrics['mape']:.4f}%")
    print(f"Saved holdout forecast: {FORECAST_OUTPUT_PATH}")
    if save_plot:
        # This communication aid uses the already saved final holdout forecast;
        # it does not influence model selection or metrics.
        save_forecast_plot(output)
        print(f"Saved forecast figure: {FIGURE_OUTPUT_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Also save a hold-out plot (requires a working Matplotlib backend).",
    )
    arguments = parser.parse_args()
    main(save_plot=arguments.plot)

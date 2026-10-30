"""Training-only stationarity diagnostics for the selected CPU time series."""

from __future__ import annotations

from pathlib import Path
import warnings

import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss

from data_preparation import chronological_split, load_and_validate_series


FIGURE_DIR = Path("reports/figures")


def adf_result(values: pd.Series) -> dict[str, float | int]:
    """Return Augmented Dickey-Fuller test results for a numeric series."""

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        statistic, p_value, used_lag, observations, critical_values, _ = adfuller(
            values, autolag="AIC", result_object=False
        )
    return {
        "statistic": float(statistic),
        "p_value": float(p_value),
        "used_lag": int(used_lag),
        "observations": int(observations),
        "critical_1_percent": float(critical_values["1%"]),
        "critical_5_percent": float(critical_values["5%"]),
        "critical_10_percent": float(critical_values["10%"]),
    }


def kpss_result(values: pd.Series) -> dict[str, float | int]:
    """Return KPSS level-stationarity test results for a numeric series."""

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        statistic, p_value, used_lag, critical_values = kpss(
            values, regression="c", nlags="auto", result_object=False
        )
    return {
        "statistic": float(statistic),
        "p_value": float(p_value),
        "used_lag": int(used_lag),
        "critical_1_percent": float(critical_values["1%"]),
        "critical_5_percent": float(critical_values["5%"]),
        "critical_10_percent": float(critical_values["10%"]),
    }


def save_diagnostic_plots(train: pd.DataFrame, output_dir: Path = FIGURE_DIR) -> None:
    """Save raw/differenced and ACF/PACF training-only diagnostic figures."""

    # Import plotting libraries only when figures are needed. This keeps the
    # statistical tests usable even while Matplotlib creates a local font cache.
    import matplotlib.pyplot as plt
    from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

    output_dir.mkdir(parents=True, exist_ok=True)
    values = train["value"]
    first_difference = values.diff().dropna()

    fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=False)
    axes[0].plot(train["timestamp"], values, color="#2A6F97", linewidth=0.8)
    axes[0].set_title("Training CPU Utilization")
    axes[0].set_ylabel("CPU utilization")
    axes[1].plot(train["timestamp"].iloc[1:], first_difference, color="#E76F51", linewidth=0.8)
    axes[1].set_title("First Difference of Training CPU Utilization")
    axes[1].set_xlabel("Timestamp")
    axes[1].set_ylabel("Change from prior 5-minute value")
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(output_dir / "02_training_series_and_first_difference.png", dpi=150)
    plt.close(fig)

    max_lags = 100
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    plot_acf(values, lags=max_lags, ax=axes[0], zero=False)
    axes[0].set_title("Training-Series Autocorrelation (First 100 Lags)")
    plot_pacf(values, lags=max_lags, ax=axes[1], zero=False, method="ywm")
    axes[1].set_title("Training-Series Partial Autocorrelation (First 100 Lags)")
    plt.tight_layout()
    plt.savefig(output_dir / "02_training_acf_pacf.png", dpi=150)
    plt.close(fig)


def main() -> None:
    """Run diagnostics on the training partition and print reproducible results."""

    series = load_and_validate_series()
    train, _, _ = chronological_split(series)
    raw = train["value"]
    differenced = raw.diff().dropna()
    save_diagnostic_plots(train)

    for label, values in (("raw training series", raw), ("first difference", differenced)):
        print(f"\n{label}")
        print("ADF:", adf_result(values))
        print("KPSS:", kpss_result(values))


if __name__ == "__main__":
    main()

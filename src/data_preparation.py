"""Leakage-safe preparation for the selected NAB CPU-utilization series.

This module performs Phase 2 data validation and chronological splitting only.
It deliberately does not fit forecasting models or use NAB anomaly labels.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


RAW_DATA_PATH = Path(
    "data/external/NAB/data/realAWSCloudwatch/ec2_cpu_utilization_5f5533.csv"
)
PROCESSED_DATA_PATH = Path("data/processed/ec2_cpu_utilization_5f5533_phase2.csv")


@dataclass(frozen=True)
class SplitSummary:
    """Chronological boundaries and sizes of a train/test split."""

    train_observations: int
    test_observations: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


def load_and_validate_series(path: Path = RAW_DATA_PATH) -> pd.DataFrame:
    """Load the selected series and reject conditions that break time ordering.

    The returned frame contains only ``timestamp`` and ``value``, is sorted in
    ascending timestamp order, and has a regular five-minute index. This
    project has no missing values or duplicate timestamps, so this function
    raises an error instead of silently imputing or discarding observations.
    """

    if not path.exists():
        raise FileNotFoundError(f"Selected dataset was not found: {path}")

    series = pd.read_csv(path, parse_dates=["timestamp"])
    expected_columns = ["timestamp", "value"]
    if list(series.columns) != expected_columns:
        raise ValueError(
            f"Expected columns {expected_columns}, found {list(series.columns)}"
        )

    if series.isna().any().any():
        raise ValueError("Missing timestamps or CPU values require an explicit decision.")
    if series["timestamp"].duplicated().any():
        raise ValueError("Duplicate timestamps require an explicit decision.")

    series = series.sort_values("timestamp", kind="stable").reset_index(drop=True)
    intervals = series["timestamp"].diff().dropna()
    expected_interval = pd.Timedelta(minutes=5)
    if not intervals.eq(expected_interval).all():
        raise ValueError("The selected series is not regular at the expected five-minute interval.")

    return series


def chronological_split(
    series: pd.DataFrame, test_fraction: float = 0.20
) -> tuple[pd.DataFrame, pd.DataFrame, SplitSummary]:
    """Create a contiguous train/test split without shuffling observations.

    The latest 20% of observations form the held-out test period. No model,
    scaler, feature transformer, or diagnostic may use this test partition
    while being fitted or selected.
    """

    if not 0 < test_fraction < 0.5:
        raise ValueError("test_fraction must be greater than 0 and less than 0.5")
    if len(series) < 10:
        raise ValueError("At least 10 observations are required for a split.")

    test_size = int(len(series) * test_fraction)
    split_index = len(series) - test_size
    train = series.iloc[:split_index].copy()
    test = series.iloc[split_index:].copy()

    if train["timestamp"].iloc[-1] >= test["timestamp"].iloc[0]:
        raise ValueError("Train/test timestamps overlap or are out of order.")

    summary = SplitSummary(
        train_observations=len(train),
        test_observations=len(test),
        train_start=train["timestamp"].iloc[0],
        train_end=train["timestamp"].iloc[-1],
        test_start=test["timestamp"].iloc[0],
        test_end=test["timestamp"].iloc[-1],
    )
    return train, test, summary


def save_processed_series(series: pd.DataFrame, path: Path = PROCESSED_DATA_PATH) -> None:
    """Save the validated series for subsequent Phase 2 work."""

    path.parent.mkdir(parents=True, exist_ok=True)
    series.to_csv(path, index=False, date_format="%Y-%m-%d %H:%M:%S")


def main() -> None:
    """Validate the raw series, save the processed copy, and print split details."""

    series = load_and_validate_series()
    save_processed_series(series)
    _, _, summary = chronological_split(series)
    print(f"Saved validated data to: {PROCESSED_DATA_PATH}")
    print(f"Training observations: {summary.train_observations}")
    print(f"Training period: {summary.train_start} to {summary.train_end}")
    print(f"Test observations: {summary.test_observations}")
    print(f"Test period: {summary.test_start} to {summary.test_end}")


if __name__ == "__main__":
    main()

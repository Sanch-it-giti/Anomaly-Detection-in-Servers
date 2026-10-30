# Phase 2 Data Preparation Record

## Purpose

This record documents the first Phase 2 step: validating the selected NAB EC2 CPU-utilization series and defining a leakage-safe chronological holdout. It does not contain a fitted forecasting model.

## Preparation decisions

- **Input:** `ec2_cpu_utilization_5f5533.csv` from NAB's `realAWSCloudwatch` category.
- **Columns retained:** `timestamp` and `value` only. NAB anomaly labels are not read or used.
- **Validation policy:** reject missing values, duplicate timestamps, or non-five-minute intervals rather than silently changing data.
- **Split strategy:** the first 80% of observations are training data; the most recent 20% are a contiguous held-out test period. Observations are never shuffled.
- **Leakage policy:** later diagnostics, transformations, parameter selection, feature engineering, and model fitting must use the training partition only. The held-out period will be used only for final Phase 2 evaluation.

## Why this split is appropriate

A chronological split respects the direction of time and simulates forecasting future observations from earlier measurements. The selected series has a visible lower operating level near the end of the record, so a held-out latest period is also a realistic test of how methods respond to a change in level. It does not guarantee that any model can forecast this shift accurately.

## Verified split output

- **Validated processed file:** `data/processed/ec2_cpu_utilization_5f5533_phase2.csv`.
- **Training observations:** 3,226, from 2014-02-14 14:27:00 through 2014-02-25 19:12:00.
- **Held-out test observations:** 806, from 2014-02-25 19:17:00 through 2014-02-28 14:22:00.
- **Boundary check:** the final training timestamp precedes the first test timestamp by one five-minute interval.

## Next Phase 2 task

Run training-only stationarity diagnostics after `statsmodels` is installed successfully, then decide whether ARIMA is appropriate and whether there is any evidence to justify considering SARIMA.

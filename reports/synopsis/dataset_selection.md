# Phase 1 dataset selection record

## Source and scope

- **Source:** Official Numenta Anomaly Benchmark (NAB) repository, cloned from <https://github.com/numenta/NAB> on 8 October 2026.
- **Repository version inspected:** commit `ea702d75cc2258d9d7dd35ca8e5e2539d71f3140` (`chore: MIT License (#408)`, dated 3 December 2024), obtained as a shallow clone of the repository's default branch on 8 October 2026.
- **Selected file:** `data/external/NAB/data/realAWSCloudwatch/ec2_cpu_utilization_5f5533.csv`.
- **Use in this project:** CPU-utilization values and timestamps only. NAB's anomaly labels are not used for forecasting or evaluation.

## License

The repository's `LICENSE.txt` grants permission to use, copy, modify, merge, publish, distribute, sublicense, and sell copies of the software and associated documentation, provided that the copyright and permission notice are included. It is an MIT-style permissive license. Copyright: Numenta Inc., 2014–2024. Consult `data/external/NAB/LICENSE.txt` for the complete terms.

## CPU-series screening results

All ten `realAWSCloudwatch` CPU-utilization CSV files met the minimum of 500 observations. Each contained 4,032 observations and no missing timestamps, missing values, or duplicate timestamps. Their predominant sampling interval was five minutes; eight had 100% of intervals at five minutes and two had 99.95% due to a single irregular interval.

| File | Observations | Timestamp range | Five-minute regularity | Value standard deviation | Screening note |
|---|---:|---|---:|---:|---|
| `ec2_cpu_utilization_24ae8d.csv` | 4,032 | 2014-02-14 14:30 to 2014-02-28 14:25 | 100.00% | 0.095 | Very low baseline with a large maximum spike (2.344). |
| `ec2_cpu_utilization_53ea38.csv` | 4,032 | 2014-02-14 14:30 to 2014-02-28 14:25 | 100.00% | 0.102 | Narrow range (1.604–2.656). |
| `ec2_cpu_utilization_5f5533.csv` | 4,032 | 2014-02-14 14:27 to 2014-02-28 14:22 | 100.00% | 4.304 | Selected: sustained, non-trivial variation (34.766–68.092) without the near-zero/near-100 concentration of several alternatives. |
| `ec2_cpu_utilization_77c1ca.csv` | 4,032 | 2014-04-02 14:25 to 2014-04-16 14:20 | 100.00% | 26.929 | Extremely broad 0.064–99.898 range. |
| `ec2_cpu_utilization_825cc2.csv` | 4,032 | 2014-04-10 00:04 to 2014-04-24 00:09 | 99.95% | 12.079 | One irregular interval; values are high on average (mean 89.791). |
| `ec2_cpu_utilization_ac20cd.csv` | 4,032 | 2014-04-02 14:29 to 2014-04-16 14:49 | 99.95% | 21.921 | One irregular interval and a strong upward linear trend estimate. |
| `ec2_cpu_utilization_c6585a.csv` | 4,032 | 2014-04-02 14:29 to 2014-04-16 14:24 | 100.00% | 0.085 | Very low baseline with a large maximum spike (1.602). |
| `ec2_cpu_utilization_fe7f93.csv` | 4,032 | 2014-02-14 14:27 to 2014-02-28 14:22 | 100.00% | 11.812 | Very broad range with a maximum of 99.668. |
| `rds_cpu_utilization_cc0c53.csv` | 4,032 | 2014-02-14 14:30 to 2014-02-28 14:30 | 99.98% | 3.653 | One irregular interval; upward trend estimate present. |
| `rds_cpu_utilization_e47b3b.csv` | 4,032 | 2014-04-10 00:02 to 2014-04-23 23:57 | 100.00% | 5.605 | Moderate variation but a maximum of 76.230. |

## Verified statistics for the selected series

- Observations: **4,032**.
- Columns: `timestamp`, `value`.
- Timestamp range: **2014-02-14 14:27:00** through **2014-02-28 14:22:00** (13 days, 23:55:00 elapsed).
- Sampling: **5 minutes for all 4,031 consecutive intervals** (100% regular).
- Missing timestamps: **0**; missing values: **0**; duplicate timestamps: **0**.
- CPU-utilization mean: **43.110372**; standard deviation: **4.303565**; minimum: **34.766**; median: **42.918**; maximum: **68.092**.
- Linear least-squares slope estimate: **−0.7237 utilization units/day**. This is descriptive, not a stationarity result.
- Autocorrelation at a one-day lag (288 five-minute periods): **0.4644**; at a seven-day lag (2,016 periods): **0.2251**. With only approximately two weeks of coverage, these values are insufficient to establish seasonality. Formal stationarity and seasonality assessment are deferred to Phase 2.

## Selection rationale

`ec2_cpu_utilization_5f5533.csv` is recommended because it greatly exceeds the 500-observation requirement, is completely regular at a five-minute cadence, has no observed missing or duplicate timestamps, and has a moderate operating range with sustained variation. This provides enough history for an honest chronological holdout later, while avoiding selecting a series whose values are almost entirely flat or concentrated near the CPU bounds. The available history spans only about two weeks, so no seasonal pattern is claimed from Phase 1 screening.

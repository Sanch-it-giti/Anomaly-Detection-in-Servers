# Server Resource Utilization Forecasting Using Time Series Analysis and Machine Learning

## 1. Project Title

**Server Resource Utilization Forecasting Using Time Series Analysis and Machine Learning**

## 2. Introduction and Background

Server-resource monitoring produces measurements at regular points in time, such as CPU utilization. Forecasting these measurements can support earlier resource planning by estimating likely future demand from historical behaviour. This mini-project studies a univariate EC2 CPU-utilization time series from the Numenta Anomaly Benchmark (NAB) `realAWSCloudwatch` collection.

NAB is primarily an anomaly-detection benchmark. In this project, it is used only as a source of timestamped CPU-utilization observations. The work is explicitly forecasting-first: NAB anomaly labels are not loaded or used to train, validate, or evaluate forecasts.

## 3. Problem Statement and Motivation

Server teams need timely evidence when deciding whether available compute capacity is likely to be adequate. Raw monitoring charts describe the past but do not directly estimate future CPU utilization. The problem addressed by this project is to develop and compare time-series forecasting approaches that predict future CPU-utilization values from preceding observations.

The motivation is academic and practical: the project will demonstrate an end-to-end, leakage-aware forecasting workflow on server metrics, while illustrating how different classical, machine-learning, and deep-learning approaches behave on the same held-out period. It does not seek to detect anomalies.

## 4. Project Objectives — Phase 1 and Future Phases

### Phase 1: synopsis and exploratory analysis

- Select a suitable time-indexed server CPU-utilization dataset with at least 500 observations.
- Verify data coverage, sampling regularity, missing values, duplicate timestamps, descriptive statistics, and visual behaviour.
- Document an evidence-based dataset choice without building a forecasting model.

### Future Phase 2: classical forecasting

- Clean and prepare the selected time series while preserving chronological order.
- Create chronological training and held-out test periods to prevent future observations from influencing earlier modelling decisions.
- Test stationarity and assess whether a seasonal structure is supported by evidence.
- Develop ARIMA models and consider SARIMA only if the Phase 2 assessment justifies seasonal terms.
- Evaluate forecasts using MAE and RMSE, and MAPE only when it is valid for the values being evaluated.

### Future Phase 3: advanced forecasting and communication

- Develop XGBoost and LSTM forecasting models using training-only feature preparation and scaling.
- Compare ARIMA/SARIMA, XGBoost, and LSTM on the same chronological test period.
- Build a Streamlit dashboard to communicate forecasts and comparisons.
- Prepare the final report and presentation.

## 5. Dataset Description

The selected source file is `ec2_cpu_utilization_5f5533.csv` in NAB's `data/realAWSCloudwatch` directory. It contains two columns: `timestamp` and `value`, where `value` is the recorded CPU-utilization measurement.

Verified exploratory results are:

- **Observations:** 4,032.
- **Timestamp range:** 2014-02-14 14:27:00 through 2014-02-28 14:22:00, an elapsed range of 13 days 23 hours 55 minutes.
- **Sampling:** every 5 minutes for all 4,031 consecutive timestamp intervals (100% regular).
- **Data quality:** 0 missing timestamps, 0 missing values, and 0 duplicate timestamps.
- **CPU-utilization summary:** mean 43.110372; standard deviation 4.303565; minimum 34.766; median 42.918; maximum 68.092.
- **Descriptive trend indicator:** the linear least-squares slope is −0.7237 utilization units per day. This is not a stationarity test.
- **Autocorrelation indicators:** one-day lag autocorrelation is 0.4644 and seven-day lag autocorrelation is 0.2251.

The time-series plot shows variation around a higher level earlier in the observed period, a visibly lower level after approximately 25 February, and occasional spikes. These are observed features, not forecasting results. Approximately two weeks of data and the listed autocorrelations do not establish seasonality; formal testing is deferred to Phase 2.

## 6. Scope, Stakeholders, and Limitations

### Scope

The project focuses on univariate, short-horizon forecasting of the selected CPU-utilization series. The Phase 1 scope is limited to data selection, quality checks, descriptive statistics, and visual exploration. Future work will forecast the `value` series from past values only and compare planned model families fairly on a chronological holdout.

### Stakeholders

- **System administrators and operations teams:** potential users of expected CPU-demand information for capacity planning.
- **Cloud or infrastructure managers:** potential users of utilization forecasts when reviewing resource allocation.
- **University project evaluators and students:** users of the documented time-series methodology and model comparison.

### Limitations

- The selected history spans about two weeks, which restricts the evidence available for long-period seasonal patterns and long-horizon generalisation.
- The series contains only CPU-utilization values; it does not include workload, memory, network, deployment, or configuration variables that may explain changes.
- The observed level change near 25 February can make a single stable-process assumption unsuitable; this must be assessed during preprocessing and validation.
- NAB was designed for anomaly detection. Its labels will not be used, so the project will not make claims about anomaly-detection performance.
- Findings from one historical EC2 series may not generalise to all servers or workloads.

## 7. Proposed Methodology

1. **Data handling:** retain timestamps and CPU-utilization values, order data chronologically, and re-check data quality before modelling. Any cleaning or transformation decisions will be fitted using training data only.
2. **Exploratory and diagnostic analysis:** inspect plots and descriptive measures, then perform Phase 2 stationarity testing. Seasonality will be modelled only if diagnostics justify it.
3. **Chronological validation:** reserve the latest observations as a held-out test period. No random train/test split will be used because it would leak later time information into training.
4. **Classical models:** fit ARIMA and, conditionally, SARIMA models using only the training period.
5. **Advanced models:** engineer lagged/time features for XGBoost and construct sequential training examples for LSTM without crossing the training/test boundary. Scaling, where required, will be fitted on training observations and then applied to the test period.
6. **Evaluation:** produce forecasts for the identical held-out timestamps and compare them with MAE and RMSE; use MAPE only when its assumptions are suitable. Results will be interpreted alongside plots and limitations rather than as a single metric alone.

No forecasting model is implemented in Phase 1.

## 8. Expected Outcomes

- A documented, reproducible dataset choice and Phase 1 EDA record.
- A cleaned, chronologically split dataset prepared in Phase 2.
- A like-for-like comparison of planned classical and advanced forecasting approaches in Phase 3.
- A Streamlit dashboard that presents historical values, held-out forecasts, and evaluation results.
- A final report and presentation that clearly distinguishes observed results from methodological choices and limitations.

These are expected deliverables, not completed results or performance claims.

## 9. Anticipated Challenges and Future Work

Potential challenges include the short observation window, the visible level change, selecting model parameters without looking at held-out outcomes, and maintaining identical evaluation windows across models. LSTM models may require more data or careful regularisation to avoid overfitting. MAPE requires caution because percentage errors can be unstable near zero, although the selected values observed in Phase 1 are positive.

Future work within the project will test stationarity, investigate evidence for seasonal structure, choose model settings using training data, and compare forecasts. Possible work beyond the mini-project includes testing multiple servers, incorporating additional resource metrics and workload variables, collecting longer histories, and assessing forecast performance after operational deployment.

## 10. References and Sources

1. Numenta. *Numenta Anomaly Benchmark (NAB)* repository. <https://github.com/numenta/NAB>. Accessed 8 October 2026; inspected commit `ea702d75cc2258d9d7dd35ca8e5e2539d71f3140`.
2. Numenta. `data/realAWSCloudwatch/ec2_cpu_utilization_5f5533.csv`, included in the NAB repository above.
3. Numenta. `LICENSE.txt`, NAB repository. Copyright 2014–2024 Numenta Inc.; permissive MIT-style license text. <https://github.com/numenta/NAB/blob/master/LICENSE.txt>.
4. Project Phase 1 EDA notebook: `notebooks/01_phase1_eda.ipynb`.
5. Project Phase 1 screening record: `reports/synopsis/dataset_selection.md`.

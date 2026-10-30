# Project Feasibility Analysis

## Decision summary

The proposed university mini-project is **feasible with stated limits**. The selected CPU series is clean, regularly sampled, and sufficiently long for a small chronological holdout and model comparison. The main feasibility risks are not data corruption but limited history, a possible regime change, uncertain seasonality, and the greater data demand of LSTM. These risks can be managed by treating advanced methods as comparisons against well-specified baselines rather than guaranteed improvements.

## 1. Data feasibility

The selected NAB EC2 CPU-utilization file has the following verified Phase 1 properties:

| Item | Verified finding | Feasibility implication |
|---|---|---|
| Observation count | 4,032 | Exceeds the project minimum of 500 and provides many five-minute observations for training and a later chronological test period. |
| Time span | 2014-02-14 14:27:00 to 2014-02-28 14:22:00 (13 days, 23 hours, 55 minutes) | Adequate for a mini-project demonstration, but short for evaluating longer cycles or generalisation across workloads. |
| Sampling | 5 minutes for all 4,031 consecutive intervals | Supports standard regularly sampled univariate time-series preparation. |
| Missing values | 0 in `timestamp`; 0 in `value` | No Phase 1 imputation is required. This reduces preprocessing complexity but must be rechecked before modelling. |
| Duplicate timestamps | 0 | Supports an unambiguous chronological order. |
| Value range and variation | Min 34.766; median 42.918; mean 43.110372; max 68.092; standard deviation 4.303565 | Contains more useful variation than a near-flat series, while still being a single target variable. |

The dataset is therefore suitable for demonstrating forecasting workflow and model comparison. It is not sufficient to claim that a selected model will generalise to all EC2 instances, all seasons, or other operational contexts.

## 2. Technical feasibility

### Available now

The project uses VS Code and a working Python 3.11 virtual environment. Phase 1 has already verified the following installed libraries: pandas, NumPy, Matplotlib, Seaborn, Jupyter, and IPython kernel support. The executed notebook can load the selected CSV and generate the required figures. This is adequate for data inspection, visualisation, and notebook-based documentation.

### Planned later dependencies

At the end of Phase 1, the virtual environment does **not** yet contain `statsmodels`, `xgboost`, TensorFlow/Keras, or Streamlit. This is not a failure: ARIMA/SARIMA, XGBoost, LSTM, and dashboard work are explicitly scheduled for later phases. Before Phase 2/3 implementation, compatible versions of the needed libraries must be installed and import-tested. The environment should also be recorded in a later dependency file to support reproducibility.

The data volume is small enough for local execution on a normal development machine. XGBoost and ARIMA/SARIMA should be computationally modest at this scale. LSTM training is feasible for an educational experiment but should use small architectures, fixed random seeds where applicable, early stopping/validation designed without test leakage, and a limited hyperparameter search.

## 3. Methodological feasibility and safeguards

The proposed model set is feasible only if evaluation remains chronological and comparable:

1. Sort by timestamp and reserve the most recent contiguous observations as the test period.
2. Use only the training portion for stationarity testing, model selection, scaling, and feature construction decisions.
3. Fit transformations/scalers on training data and apply them unchanged to later data.
4. Build XGBoost lags and LSTM sequences so that no feature uses a later timestamp than its prediction target.
5. Forecast the same held-out timestamps for every candidate model.
6. Report MAE and RMSE; use MAPE only after confirming that it is meaningful for the evaluation values.

This approach makes the comparison achievable without claiming real-time deployment readiness.

## 4. Time and delivery feasibility

| Phase | Scheduled period | Feasible deliverable |
|---|---|---|
| Phase 1 — Synopsis | 28 September–9 October 2026 | Dataset selection, EDA, systems/literature review, feasibility assessment, synopsis material. |
| Phase 2 — Classical Forecasting | 19–30 October 2026 | Preprocessing, chronological split, diagnostics, ARIMA and conditional SARIMA, held-out evaluation. |
| Phase 3 — Advanced Forecasting | 16–27 November 2026 | XGBoost and LSTM comparisons on the same test period, Streamlit dashboard, final report, and presentation. |

The schedule is realistic if Phase 2 first delivers the simpler classical baseline and Phase 3 treats the dashboard and LSTM as planned work with verification milestones. A model that cannot be validated honestly within the available time should be documented as incomplete rather than replaced with fabricated results.

## 5. Key limitations and mitigation plan

| Limitation or risk | Evidence / reason | Planned mitigation |
|---|---|---|
| Short history | The series spans about two weeks. | Use short-horizon, explicit conclusions; avoid broad seasonal and long-term claims; describe limited external validity. |
| Possible regime change | The Phase 1 time plot shows a visibly lower level after approximately 25 February; the linear slope is −0.7237 utilization units/day. | Preserve time order; inspect training/test placement; use diagnostics and report whether a model misses the shift. Do not shuffle data. |
| Seasonality uncertain | One-day autocorrelation is 0.4644 and seven-day autocorrelation is 0.2251, but only about two weeks are available. | Do not assume seasonal terms. Use SARIMA only after Phase 2 diagnostics offer adequate evidence. |
| Spikes and non-normal behaviour | The plot includes occasional spikes. | Compare error plots and MAE/RMSE; avoid interpreting one average metric as complete operational risk assessment. |
| LSTM overfitting | A single short univariate series provides less training diversity than large multi-series datasets. | Keep the network small, use a validation procedure inside the training history, and compare against ARIMA/XGBoost. |
| Leakage | Time-series preprocessing can accidentally use future observations. | Apply the chronological safeguards above and document split boundaries and fitted preprocessing. |
| Limited explanatory variables | Only timestamp and CPU utilization are available. | Frame the project as univariate forecasting; list workload, memory, network, and deployment data as future extensions. |

## 6. Overall feasibility conclusion

The project can responsibly meet its educational objectives: construct a reproducible pipeline, evaluate classical and advanced forecasting methods on an identical held-out period, and communicate the comparison. It cannot, from this dataset alone, establish a universal capacity-planning policy, prove seasonality, or guarantee production performance. Those boundaries are part of the project’s feasibility, not omissions to hide.

## Sources consulted

- Project EDA notebook: `notebooks/01_phase1_eda.ipynb`.
- Project selection record: `reports/synopsis/dataset_selection.md`.
- Project synopsis: `reports/synopsis/synopsis_content.md`.
- Literature and systems sources: `reports/synopsis/literature_review.md`.

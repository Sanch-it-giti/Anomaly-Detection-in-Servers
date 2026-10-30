# Existing Systems Review and Literature Review

## Purpose and project boundary

This review supports the forecasting-first project *Server Resource Utilization Forecasting Using Time Series Analysis and Machine Learning*. It concerns prediction of future CPU-utilization values from past time-indexed observations. It does **not** treat anomaly labels as forecasting targets or evaluate anomaly-detection methods.

The selected project series is NAB `ec2_cpu_utilization_5f5533.csv`: 4,032 five-minute CPU-utilization observations with no missing or duplicate timestamps. The Phase 1 EDA shows a visible lower operating level after approximately 25 February and occasional spikes. These observed characteristics inform the review but do not establish seasonality or a final model choice.

## 1. Existing systems for cloud CPU monitoring and planning

Cloud-monitoring systems commonly collect CPU and other resource metrics, visualise them in dashboards, and create alarms or scaling actions. A reactive configuration evaluates a recent metric value against a rule, such as a CPU threshold or target. For example, AWS documents dynamic scaling that changes desired capacity when a related CloudWatch alarm enters the `ALARM` state; it also documents predictive scaling, which uses collected data to forecast future load and capacity ([AWS dynamic scaling documentation](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scale-based-on-demand.html); [AWS predictive-scaling monitoring documentation](https://docs.aws.amazon.com/autoscaling/ec2/userguide/monitor-predictive-scaling-cloudwatch.html)).

Therefore, it would be inaccurate to state that existing cloud systems do not offer forecasting. Instead, reactive monitoring and forecast-based planning solve related but different problems and can be used together.

| Aspect | Reactive threshold/target-based monitoring | Forecasting-based resource planning |
|---|---|---|
| Main input | Current or recently aggregated metric relative to a configured rule | Historical time-ordered observations, optionally with known future inputs |
| Timing of response | After a threshold/target condition is observed | Before the forecast horizon, subject to forecast uncertainty |
| Typical action | Alert, scale, or investigate a current breach | Plan capacity or trigger a proactive scaling decision |
| Strength | Transparent, direct, and useful for abrupt or safety-critical conditions | Can allow capacity preparation before a predictable rise in demand |
| Main risk | May react only after load has risen; scaling has delay | Can make incorrect estimates, especially during regime changes or unusual spikes |
| Project role | Context for why CPU is monitored | Central focus: compare future forecasting methods on one held-out period |

Forecasting does not replace operational safeguards. In a realistic system, forecasts would complement thresholds, service-level objectives, capacity limits, and human oversight.

## 2. Relevant forecasting approaches

The following methods are proposed for later phases. None is implemented or evaluated in Phase 1.

| Approach | Basic idea | Strengths for this project | Constraints and safeguards |
|---|---|---|---|
| **ARIMA** | Models autocorrelation and moving-average error structure after differencing as needed. | Clear statistical baseline for a single regularly sampled series; parameters are interpretable. | Requires diagnostic work and training-only parameter selection; a level change may challenge a stable-process assumption. |
| **SARIMA** | Extends ARIMA with seasonal autoregressive, differencing, and moving-average terms. | Appropriate only when a repeatable seasonal period is supported by Phase 2 diagnostics. | The current approximately two-week record and Phase 1 autocorrelations do **not** establish seasonality. SARIMA will be omitted if evidence is inadequate. |
| **XGBoost** | Gradient-boosted decision trees trained on supervised features such as lagged CPU values and calendar features. | Can model nonlinear relationships and interactions in explicitly engineered lags; efficient on tabular data. | Lag features must be constructed without using future rows. Calendar features should be justified, not assumed to prove seasonality. |
| **LSTM** | A gated recurrent neural network that learns sequential representations. | Can represent longer temporal dependencies without manually choosing every lag. | Greater risk of overfitting on one short univariate series; scaling must be fitted on training data only; results must be compared against simpler baselines. |

All methods will use the same chronologically later held-out period. Candidate selection, transformations, scaling, and feature construction must avoid incorporating observations from that test period.

## 3. Research literature

The following nine references were checked against a DOI resolver, publisher page, conference page, institutional repository, or an author/publisher-hosted publication record. Each is relevant either to cloud resource prediction, forecasting evaluation, or a proposed method. No unverified references are included in the numbered list.

1. **Islam, S., Keung, J., Lee, K., & Liu, A. (2011).** “Empirical Prediction Models for Adaptive Resource Provisioning in the Cloud.” *Future Generation Computer Systems*, 28(1), 155–162. https://doi.org/10.1016/j.future.2011.05.027. The paper studies prediction-based cloud provisioning using neural-network and linear-regression approaches. Verified through the [CSIRO publication record](https://publications.csiro.au/publications/publication/PInicta%3A4963) and DOI.
2. **Calheiros, R. N., Masoumi, E., Ranjan, R., & Buyya, R. (2015).** “Workload Prediction Using ARIMA Model and Its Impact on Cloud Applications’ QoS.” *IEEE Transactions on Cloud Computing*, 3(4), 449–458. https://doi.org/10.1109/TCC.2014.2350475. It is directly relevant to using ARIMA for proactive cloud workload planning. Verified through the [IEEE Xplore record](https://ieeexplore.ieee.org/document/6881647).
3. **Gong, Z., Gu, X., & Wilkes, J. (2010).** “PRESS: PRedictive Elastic ReSource Scaling for Cloud Systems.” *6th IEEE/IFIP International Conference on Network and Service Management (CNSM 2010)*. Reliable publication page: [Google Research](https://research.google/pubs/press-predictive-elastic-resource-scaling-for-cloud-systems/). This conference paper presents predictive elastic scaling using signal processing and statistical learning. A DOI was not located during verification, so the official publication page is supplied instead.
4. **Hyndman, R. J., & Khandakar, Y. (2008).** “Automatic Time Series Forecasting: The forecast Package for R.” *Journal of Statistical Software*, 27(3), 1–22. https://doi.org/10.18637/jss.v027.i03. The paper describes automated ARIMA-oriented forecasting procedures and is useful background for classical-model identification and evaluation. Verified at the [Journal of Statistical Software citation record](https://www.jstatsoft.org/article/view/v027i03).
5. **Chen, T., & Guestrin, C. (2016).** “XGBoost: A Scalable Tree Boosting System.” *Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*, 785–794. https://doi.org/10.1145/2939672.2939785. This is the primary publication for XGBoost. Verified through the [ACM Digital Library](https://dl.acm.org/doi/10.1145/2939672.2939785).
6. **Hochreiter, S., & Schmidhuber, J. (1997).** “Long Short-Term Memory.” *Neural Computation*, 9(8), 1735–1780. https://doi.org/10.1162/neco.1997.9.8.1735. This is the foundational LSTM paper. Verified through [MIT Press Direct](https://direct.mit.edu/neco/article/9/8/1735/6109/Long-Short-Term-Memory).
7. **Taylor, S. J., & Letham, B. (2018).** “Forecasting at Scale.” *The American Statistician*, 72(1), 37–45. https://doi.org/10.1080/00031305.2017.1380080. It provides practical discussion of scalable forecasting workflows and analyst review. Verified at the [publisher page](https://www.tandfonline.com/doi/abs/10.1080/00031305.2017.1380080).
8. **Makridakis, S., Spiliotis, E., & Assimakopoulos, V. (2020).** “The M4 Competition: 100,000 Time Series and 61 Forecasting Methods.” *International Journal of Forecasting*, 36(1), 54–74. https://doi.org/10.1016/j.ijforecast.2019.04.014. This large comparison cautions against assuming that one model family is universally best. Verified through the [publisher DOI page](https://doi.org/10.1016/j.ijforecast.2019.04.014).
9. **Lim, B., & Zohren, S. (2021).** “Time-series Forecasting with Deep Learning: A Survey.” *Philosophical Transactions of the Royal Society A*, 379(2194), 20200209. https://doi.org/10.1098/rsta.2020.0209. The survey reviews deep-learning designs for one-step and multi-horizon forecasting. Verified through [PubMed](https://pubmed.ncbi.nlm.nih.gov/33583273/).

### References not verified

None are cited as supporting literature in this document without verification. In particular, no claim is made here that a paper has tested ARIMA, SARIMA, XGBoost, or LSTM on the selected NAB series; this project will conduct its own later comparison.

## 4. Synthesis for the proposed project

The literature supports studying both classical and learning-based methods, but it does not justify presuming that a more complex method will win on this dataset. The M4 competition paper and the short, univariate nature of the selected series reinforce the value of transparent baselines and a fair chronological comparison. Cloud-provisioning papers motivate proactive prediction, while the observed level change shows why forecasts need careful validation and cautious operational interpretation.

For this project, ARIMA is a necessary baseline; SARIMA is conditional on evidence; XGBoost offers a lag-feature regression alternative; and LSTM is an advanced sequential model to be assessed for feasibility rather than assumed to be superior.

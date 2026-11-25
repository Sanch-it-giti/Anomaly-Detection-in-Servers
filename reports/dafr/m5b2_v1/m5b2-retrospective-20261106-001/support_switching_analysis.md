# RETROSPECTIVE DEVELOPMENT DIAGNOSTIC — support and switching

Run `m5b2-retrospective-20261106-001`. This analysis describes the frozen policy after execution; it does not propose thresholds selected from these outcomes.

## Readiness and age expiry

Origins use the original five-minute grid index. Every stream starts with zero matched errors; only genuine expert pairs from this block count. The minimum 100 means 100 target-matched errors from each expert, not 100 arrivals or 200 independent observations.

| Machine | h | First 100-pair origin | Ready ticks | Eligible to consider switch | Maximum / final support | Age-expired pairs |
|---|---:|---:|---:|---:|---|---:|
| m_505 | 1 | 1282 | 330 | 330 | 288 / 288 | 141 |
| m_505 | 12 | 1294 | 318 | 272 | 288 / 288 | 129 |
| m_1426 | 1 | 1252 | 360 | 336 | 288 / 263 | 171 |
| m_1426 | 12 | 1263 | 349 | 323 | 288 / 272 | 160 |
| m_3028 | 1 | 1252 | 360 | 336 | 288 / 263 | 171 |
| m_3028 | 12 | 1263 | 349 | 325 | 288 / 263 | 160 |

Ready means support ≥100. Eligibility additionally requires the original genuine-history gate, both current expert predictions and elapsed dwell ≥24. It does not mean the improvement margin is met. All streams become eligible at least once, but h=1 never switches. Missing observations/history recovery and switch dwell explain the difference between ready and eligible counts.

Support ages at every grid tick, including missing ones, using target indices current−287 through current. A total of 932 pairs expire by age. There are zero additional capacity evictions: at most one pair per horizon can mature per tick, so the 288-tick age bound already enforces the 288-pair capacity in this replay. Lower final supports on m_1426/m_3028 reflect missing targets and closed input gates inside the recent window. No support minimum is relaxed.

## Every loss-based switch

All three switches are at h=12. Source event timestamps are stored in [switch_events.csv](switch_events.csv); they use the inherited artificial UTC epoch. No h=1 expert switch, telemetry reset or drift alert occurs in this real block.

| Machine | Origin | Change | Matched pairs | ARIMA / XGBoost mean loss | Required improvement | Elapsed dwell |
|---|---:|---|---:|---|---:|---:|
| m_505 | 1294 | ARIMA → XGBoost | 100 | 6.184555 / 5.846375 | 0.309228 | 142 |
| m_505 | 1440 | XGBoost → ARIMA | 246 | 5.588524 / 5.905568 | 0.295278 | 146 |
| m_1426 | 1582 | ARIMA → XGBoost | 288 | 7.252036 / 6.889423 | 0.362602 | 430 |

The first m_505 switch occurs as h=12 reaches 100 pairs. The challenger had lower past mean loss by the frozen margin, but its ensuing selected forecasts worsen the whole-period m_505 MAE/RMSE compared with fixed ARIMA. Selecting the lower past loss does not guarantee lower future error. The return to ARIMA is also based only on then-matured errors; no previous choice is revised.

The late m_1426 switch barely exceeds the 5% boundary in full precision. Displayed values are rounded for readability; the exact recorded numbers and 1e−12 tolerance determine the decision. This observation is not used to alter the margin, dwell or window. Its small favorable m_1426 difference does not outweigh m_505's unfavorable difference in the equal-machine macro.

Persistence fallback during the common gate is attributed separately from the incumbent identity. Recovery from fallback is not an expert switch. Only original expert-issued genuine errors enter comparison support; persistence errors during recovery remain policy outcomes. Thus the 77 fallback origins per horizon never supply artificial expert feedback.

## Availability and limitations

All three policies had the same expert opportunity in the original M4A block: 431,436,436 expert origins per horizon, respectively. The adaptive policy preserves that opportunity and the documented persistence fallback, with zero abstentions. All 39 adaptive boundary-pending forecasts remain pending; missing exact targets have no error and are never shifted to a later observation.

Four isolated missing bins provide limited evidence about quality disruptions. There is no long real-data outage or era boundary. Separate synthetic tests verify the fourth-missing reset, default restart, 24-genuine recovery, old-era outcome accounting and stale abstention. These are engineering checks, not evidence of workload/concept drift in Alibaba.

The six private forecast/error plots show recorded five-minute positions and genuine gaps. Three private support plots mark the minimum and actual switches. The aggregate expert-matched and complete-policy figures use equal-machine errors with identical target sets within each scope. All figures are labeled RETROSPECTIVE DEVELOPMENT DIAGNOSTIC and make no independent generalization claim.

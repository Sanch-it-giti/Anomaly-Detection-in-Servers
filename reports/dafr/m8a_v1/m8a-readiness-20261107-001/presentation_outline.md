# Presentation outline and existing-figure inventory

Suggested12 slides for approximately12–15minutes. This is an outline, not a new PPTX, rendered slide deck or invented research figure. Use the original university title with a subtitle identifying the **two-expert chronological engineering/development pilot**. Student, ID, guide and institution remain placeholders.

| Slide | Concise message | Evidence / figure to use | Qualification to state |
|---|---|---|---|
|1. Title and question|Can adaptive forecasting improve accuracy/reliability without leakage?|Original title; plain research question|DAF-R is proposed, not proven novel|
|2. Objectives versus delivered scope|Real ARIMA/XGBoost, causal selection, monitoring and intervals|[Status matrix](project_status_matrix.md)|LSTM/full drift/reliability response/dashboard absent|
|3. Data and initial EDA|NAB4032 five-minute values; later Alibaba source|Existing NAB time-series/histogram|NAB is inspected; no seasonality claim|
|4. Missing-data decision|All15 failed v1; separately versioned V2 pilot|M2B/M3B-1 qualification tables|Three development admissions do not qualify confirmation|
|5. Chronology and gap handling|Reveal→mature→support→state→forecast/interval|Textual workflow, exact h1/h12 example from reports|No new diagram claimed as an existing artifact|
|6. Model and training protocol|Fit864; development selection through1151; fixed parameters|Existing M3B-2 h1/h12 comparison figures|Development validation, not final independent results|
|7. Forward fixed benchmark|Compare ARIMA/XGBoost/persistence on matched targets|Existing M4A matched macro MAE figure|Origins[1152,1612) already inspected|
|8. Adaptive diagnostic|h1 equal; h12 worse than ARIMA|Both M5B-2 expert and complete-policy figures|RETROSPECTIVE DEVELOPMENT DIAGNOSTIC; no gain|
|9. Drift mechanics and failures|Independent persistence-error channel; h1 step miss, repeated alarms|M6A saved alarm/delay table|No real-world drift truth or automatic response|
|10. Intervals and unfavorable coverage|Both90/95, support/availability/width together|M7A/M7B existing diagnostic tables|Growing variation undercovers; no guarantee|
|11. Verification and reproducibility|Historical409 tests; fresh no-fit304 pass/105 skips; hashes|M8A regression and preservation receipts|Do not describe409 as a fresh all-pass M8A rerun|
|12. Conclusion and next gates|Engineering contribution plus negative findings; independent NO-GO|Qualification readiness, proposed protocol and references|Zero fully verified V2 confirmation machines; protected blocks closed|

## Actual reusable figure files

The [figure receipt](figure_inventory.json) verifies existence, PNG headers, dimensions and SHA-256. M8A did not generate plots or conduct a fresh visual-layout review; check readability/legends when building an actual deck. Sources remain within their original evidence domain.

| Existing artifact | Intended use | Evidence domain |
|---|---|---|
|[NAB CPU line plot](../../../figures/01_ec2_cpu_5f5533_time_series.png)|Initial time-indexed CPU context|Historical NAB EDA|
|[NAB histogram](../../../figures/01_ec2_cpu_5f5533_histogram.png)|Distribution/context|Historical NAB EDA|
|[NAB missing summary](../../../figures/01_ec2_cpu_5f5533_missing_data_summary.png)|Zero missing columns in that selected series|NAB only; not Alibaba completeness|
|[M3B-2 h1 MAE](../../m3b2_v1/m3b2-development-20261030-001/matched_mae_h1.png)|Candidate development comparison|Inner development validation|
|[M3B-2 h12 MAE](../../m3b2_v1/m3b2-development-20261030-001/matched_mae_h12.png)|Secondary horizon|Inner development validation|
|[M4A matched macro MAE](../../m4a_v1/m4a-development-20261031-001/matched_macro_mae.png)|Fixed-model forward benchmark|Inspected development|
|[M5B-2 expert matched](../../m5b2_v1/m5b2-retrospective-20261106-001/expert_matched.png)|Expert-only negative finding|Retrospective development|
|[M5B-2 complete policy](../../m5b2_v1/m5b2-retrospective-20261106-001/complete_policy_matched.png)|Fallback-inclusive negative finding|Retrospective development|

No existing independent final/confirmation plot, LSTM result or calibrated real-data interval band is available. Synthetic interval-band, coverage-versus-nominal, width/availability and support/reset plots could later be drawn from already saved synthetic ledgers under an explicitly scoped presentation task; they are not claimed created here. Never substitute a synthetic band for observed Alibaba confirmation performance. Reuse existing verified references from the report draft, not invented supporting papers.

## Likely viva questions

- Why is past observed test data allowed? A value may update a later forecast after genuine arrival; it cannot change the earlier forecast targeting that value.
- Why not compress gaps? It changes elapsed horizons, lag meaning and error maturity; exact grid targets must survive.
- Did adaptation help? Not in M5B-2: h1 matched ARIMA; h12 was worse. State that directly.
- Are intervals calibrated? Only synthetic diagnostics exist, and growing variation undercovered. No formal/real-world guarantee is established.
- Why not say full DAF-R is complete? Monitoring does not implement drift response or reliability-based selection; LSTM/independent confirmation are absent.
- What is the next legitimate step? Separate prefix-mask qualification/provenance approval and final protocol/integration decisions, not automatic protected evaluation.

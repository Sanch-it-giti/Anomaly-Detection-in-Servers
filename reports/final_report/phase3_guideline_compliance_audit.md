# Phase 3 guideline and report compliance audit

**Reviewed:** 20 November 2026  
**Evidence currently in the repository:** through 7 November 2026 (M8A readiness package)  
**Scope:** final Phase 3 notice, source-code presence, current report and current viva presentation.

## Overall assessment

The project has substantial, reproducible implementation evidence. The report has now been revised to align with the supplied research-paper outline: it contains a 180-word abstract, a standalone literature review, preprocessing details, methodology/tools, a saved forecast-versus-actual figure, discussion, and ten numbered IEEE-style references within the ten-page limit. It is **not ready for final submission until the real team names/roll numbers, guide/institution details and individual contribution plan are supplied**. The presentation should be rehearsed to fit 10–12 minutes and divided among all team members.

The report and presentation reflect evidence only through **7 November**, while the Phase 3 evaluation window is **16–27 November**. They should not be presented as documenting work completed after that evidence cutoff.

## Phase 3 project-work requirements

| Requirement | Status | Repository evidence and notes |
|---|---|---|
| Complete and stable implementation | **Partial** | ARIMA/XGBoost, chronology simulator, selection, drift and interval infrastructure exist. Independent confirmation is NO-GO. No LSTM/GRU or Prophet training, live forecast service, or operational alert system is present. |
| Implement at least one advanced model | **Met** | XGBoost is trained and compared. See [src/run_xgboost_forecast.py](../../src/run_xgboost_forecast.py), [src/dafr/run_m3b2_v1.py](../../src/dafr/run_m3b2_v1.py), and the M3B-2 completion report. LSTM/GRU and Prophet are not implemented; they are examples in the guideline, not evidence of work completed. |
| Basic hyperparameter tuning and training/validation | **Met for the Alibaba development pilot** | The report documents the 27 candidate fits / 18 validation replays, training and validation boundaries, and development-only selection. Do not imply tuning on confirmation data. |
| Compare classical and advanced models | **Met with scope limitations** | The NAB holdout compares ARIMA and XGBoost on the same 806-point period. M4A compares ARIMA, XGBoost and persistence on common Alibaba targets at h=1 and h=12. Alibaba results are development evidence; M5B-2 is a retrospective replay, not an independent test. |
| Use MAE, RMSE, MAPE and explain differences | **Partial** | NAB reports all three metrics and the Alibaba report explicitly says MAPE is not available in the saved comparison output. The revised report explains dataset/horizon/protocol differences and the distinct loss weighting of MAE vs RMSE. Do not infer a single universal winner. |
| Interpret patterns and relate them to the real-world problem | **Met** | The report includes a verified actual-versus-saved-forecast figure, describes the NAB level change and lack of established seasonality, distinguishes the NAB and Alibaba protocols, and links missingness/abstention to safe planning use. |
| Limitations and improvements | **Met** | Missingness, short selected data, dependence, confirmation status, undercoverage, drift misses/repeated alarms, absent neural models, and future gates are documented. |
| Equal participation in demonstration and viva | **Not verifiable / action required** | The repository has no confirmed team-member list or role/contribution log. Each member must be assigned a speaking section and be ready to explain their own code and results. |

### Verified project result summary

- **NAB Phase 2 holdout (n=806):** ARIMA MAE 0.7671, RMSE 0.9763, MAPE 1.9966%; XGBoost MAE 0.7578, RMSE 1.0601, MAPE 1.9489%. XGBoost has lower MAE/MAPE; ARIMA has lower RMSE.
- **Alibaba M4A development block:** fixed ARIMA has the lowest matched macro MAE and RMSE at both horizons among persistence, ARIMA and XGBoost. Results are not confirmation evidence.
- **M5B-2 adaptive selector:** h=1 equals fixed ARIMA; h=12 is worse on the matched diagnostic. Do not claim an adaptive improvement.
- **M6/M7:** drift and interval checks are synthetic/generated-fixture engineering evidence. Undercoverage and detector failure cases are retained; they are not operational performance claims.

## Report-format audit

The prescribed format is a research-paper structure. The revised DOCX is ten pages (the maximum) and follows the requested main sections; identity/contribution details remain the outstanding title-page and viva items.

| Prescribed report item | Current report | Assessment / correction needed |
|---|---|---|
| Title page: title, team members and roll numbers | Exact project title is present. Student/team, guide and institution details are called out as unavailable. | **Partial.** Fill in every team member’s name and roll number and the official guide/institution details before submission. Do not submit placeholders. |
| Abstract, 150–200 words | 180-word Abstract covering problem, dataset, methods, findings and application. | **Met.** |
| Introduction: background, importance, motivation, objectives and report structure | Background, motivation, objectives and a section roadmap are included. | **Met.** |
| Literature review: 4–5 related works and research gap | Dedicated section discusses five related works and states a bounded engineering gap. | **Met.** No novelty claim is made. |
| Dataset description and preprocessing; source, type, time range, features, preprocessing, plot/snapshot | Exact selected NAB range, fields/units, regularity, missingness, split, raw Alibaba binning/missing treatment, and EDA figures are included. | **Met.** Dataset scopes are distinguished. |
| Methodology: classical + advanced models, split, tuning, tools, workflow | Event-order workflow, splits, model settings, tuning counts, validation and recorded software versions are included. | **Met.** |
| Results and discussion: MAE/RMSE/MAPE, forecast plots, interpretation and comparison | NAB has MAE/RMSE/MAPE; Alibaba reports available MAE/RMSE and explicitly notes MAPE is absent from saved output. Saved NAB actual-versus-forecast and comparison plots are included. | **Mostly met.** No MAPE was fabricated for Alibaba; its absence is transparent. |
| Conclusion and future work | Present and accurate. | **Met.** It covers relevance, limits and next steps. |
| References: 9–10 sources in IEEE format | Ten total references: eight research papers and the two official dataset sources, with bracketed in-text citations. | **Met in structure/style.** |
| Appendix, optional | None. | **Compliant; optional.** No appendix is required. |
| File type and maximum length | DOCX, rendered and visually checked at 10 pages. | **Met at the limit.** Verify that any later edits do not add a page. |

## Presentation and submission audit

| Requirement | Status | Notes |
|---|---|---|
| Problem overview | **Met** | Slide 3. |
| Dataset summary | **Met** | Slides 5–6; use the labels to distinguish the NAB series from Alibaba development records. |
| Phase 2 recap | **Met** | Slide 9 shows the NAB ARIMA/XGBoost comparison. |
| Advanced models used | **Partial but accurately disclosed** | Slide 8 presents trained ARIMA/XGBoost configurations and explicitly says LSTM/GRU/Prophet were not trained. XGBoost is the advanced model actually implemented. |
| Comparative results | **Met with evidence labels** | Slides 9–11 separate NAB holdout, Alibaba development and retrospective diagnostics. |
| Key insights | **Met** | Slide 14. |
| Challenges and limitations | **Met** | Slides 12–15. |
| Conclusion | **Met** | Slide 17. |
| 10–12-minute lab demonstration and Q&A | **Needs rehearsal** | There are 19 slides, including two reference slides. Keep references as backup/quickly skimmed slides and time the 17 main slides. |
| All team members participate | **Not verifiable / action required** | Add a speaking order and equal, realistic contributions; names and roles are not in the repository. |
| Required submission files | **Partial bundle** | Report and PPTX are present. Source code exists in the repository, including [notebooks/01_phase1_eda.ipynb](../../notebooks/01_phase1_eda.ipynb), [src/run_arima_baseline.py](../../src/run_arima_baseline.py), [src/run_xgboost_forecast.py](../../src/run_xgboost_forecast.py), and versioned DAF-R modules under `src/dafr/`. The final output folders do not contain a separate source-code submission archive; ensure the repository or selected `.py`/`.ipynb` files are submitted as required. |

## Priority fixes before submission

1. Fill in team members’ names/roll numbers, guide, institution, and a verified member contribution/speaking plan.
2. Rehearse the 19-slide deck to the 10–12-minute limit; use the two reference slides as quick/backup slides if needed.
3. Submit the relevant `.py`/`.ipynb` source files or repository alongside the DOCX and PPTX.
4. Keep MAPE absent for Alibaba unless a source-backed result is available; do not derive or invent it for cosmetic completeness.

## Evidence checked

- `reports/final_report/DAFR_Phase3_Final_Report.docx` and `presentations/final_presentation/DAFR_Phase3_Final_Viva.pptx`.
- `reports/dafr/m8a_v1/m8a-readiness-20261107-001/` readiness, status, protocol and report records.
- M3B-2, M4A and M5B-2 completion reports and the existing source-code/notebook inventory.
- Final report render: ten pages; abstract count: 180 words; reference count: ten.
- Presentation package: 19 slides with presenter notes.
- Saved NAB forecast outputs: 806 ARIMA and 806 XGBoost rows with identical timestamp indices; report figure generated from those saved predictions without refitting.


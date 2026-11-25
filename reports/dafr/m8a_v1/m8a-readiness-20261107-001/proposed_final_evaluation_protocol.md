# Proposed final evaluation protocol — frozen review candidate, no execution

This document and [machine-readable proposal](../../../../configs/dafr_m8a_proposed_final_protocol_v1.json) specify a reproducible candidate for approval. They do not amend prior protocols, enable a driver, qualify a machine or authorize any data access/training. All new execution flags are false. Existing scientific configurations and historical locks remain unchanged. The primary endpoint is five-minute h1; h12 means the exact five-minute mean ending60minutes after the origin, not an average over the next hour.

## Matrix and scope

| Policy | Point rule | Failure/gap behavior | Uncertainty |
|---|---|---|---|
| P | Latest genuine CPU | Only age≤3 ticks; otherwise abstain | Own-policy90/95 residual intervals |
| F-A | Fixed registered ARIMA(1,1,1) | Common24-genuine gate; own persistence fallback/abstention | Own complete-policy90/95 buffers; separate expert-only shadow |
| F-X | Fixed selected XGBoost C1; direct h1/h12 | Same gate and fallback | Own complete-policy90/95 buffers; separate expert-only shadow |
| A | Frozen M5A hard selector | Unavailable incumbent uses persistence/abstention, no unsupported emergency switch | Own actual adaptive-center90/95 buffers, including its own fallback |

All four have the same non-intervening persistence-error drift observer, or one shared equivalent observer linked identically to each variant. Monitoring-on/off is an engineering parity control, not a distinct forecasting algorithm or evidence of drift-response benefit. CPU-level channel, drift-triggered short-memory selection, reliability-based expert exclusion, weighting, ACI, retraining and LSTM remain absent; P/F/A/D/R/Full superiority cannot be claimed from this reduced matrix.

M7B's fixed expert intervals are **shadow-only**, not complete fixed-expert-plus-fallback intervals. A separately approved real-data contract must add F-A/F-X complete policies with their own issued centers, interval buffers and provenance; retaining auxiliary expert shadows gives six policy identities, not a licence to borrow their residuals. Existing four-policy M7B records must never be relabelled. This missing integration is a go/no-go blocker.

## Settings retained exactly

Sources: [M3B-1 training protocol](../../m3b1_training_validation_protocol_v1.md), [M5A](../../../../configs/dafr_m5a_synthetic_v1.json), [M6A](../../../../configs/dafr_m6a_synthetic_v1.json), [M7A](../../../../configs/dafr_m7a_synthetic_v1.json).

- ARIMA selected C3=(1,1,1), no trend/seasonality; regular missing grid retained, common burn24, enforced stationarity/invertibility, fixed fitted parameters. Training acceptance/initialization/optimizer requirements remain those of M3B-1; no new fitting is performed here.
- XGBoost selected C1: depth2,100 estimators, learning rate0.05; origin-relative genuine offsets[0,1,2,5,11,23], distinct direct h1/h12 models, identity scaling. Preserve objective, sampling, regularization, histogram algorithm, seed42 and single-thread settings in the source manifest. No recursive h12 substitution, early stopping or outcome-based candidate search.
- Model hyperparameters were selected globally using development primaries and[864,1152), with selection cutoff1151. Never backdate that selection or choose new hyperparameters from confirmation/warm-up/final values. New per-machine parameter fitting requires separate approval and fit-cutoff hashes; a shared hyperparameter choice is not a transferable fitted machine model.
- Selector: ARIMA default; minimum100 matched genuine **expert** error pairs; max288; target recency288 elapsed ticks; dwell24; improvement max(0.1 CPU points,5% incumbent mean loss); incumbent-retaining ties/tolerance1e-12; independent horizons; current-era support only. Fallback errors are not expert ranking pairs.
- Drift: fixed persistence/rule_v2 absolute error, first32 current-era genuine errors median/MAD normalization, scale floor0.1, multiplier1.4826, clipping±4, PH delta0.05, warning4/alarm8, minimum64 recent errors,288-tick support,24-tick cooldown; original reset/rearm/old-era conventions. It is monitoring only, not demonstrated concept-drift identification.
- Intervals:90/95; minimum100, capacity288, targets in[current−287,current]; own complete policy/version/horizon/era; exact rank ceil((n+1)p/100), no interpolation; raw center±q with no clipping; null bounds if insufficient/rank unavailable. Failed/absent centers have unavailable intervals. Model-version change is rejected pending a new approved convention, not a silent reset. Genuine zero residual/zero width is valid.
- Five-minute positions never compress; no imputing missing targets. Learned gate24 genuine positions, age-three persistence, one telemetry-era reset on fourth missing tick. No old-era error enters active new-era buffers. A missing target creates unavailable outcome, not shifted scoring or a zero error/miss. Delivery delay is assumed zero at the grid label; later data/revisions require a new explicit contract.

The original design proposed EWMA/context-dependent selection, initial-fit normalization and full drift/reliability responses. Later authorized engineering milestones froze the different choices above. M8A neither reverts to those provisional original choices nor pretends all original objectives were completed.

## Machines, training and boundaries

Development roles remain m_505,m_1426,m_3028; reserves remain m_3276,m_1029,m_2104. Confirmation roles/order are in [qualification readiness](confirmation_qualification_readiness.md). At least six **fully qualified** confirmation machines are required for this proposed independent-machine study; currently zero are verified. Shared-cluster dependence and short records still limit inference even if six pass.

| Grid indices | Established role / evidence |
|---|---|
|[0,1152)|Original research fit prefix; development masks/values inspected|
|[0,864)|Actual completed development parameter fitting|
|[864,1152)|Actual inner development hyperparameter selection; no selected-winner hindsight validation claim|
|[1152,1612)|Already examined M4A forward benchmark/M5B-2 retrospective diagnostic|
|[1612,1842)|Restricted230-tick calibration/warm-up; no access in M8A|
|[1842,2304)|Restricted462-tick final block; no access in M8A|

**Training-boundary adoption requires a decision before execution.** Preferred compatibility proposal: retain the completed per-machine parameter-fit procedure[0,864), select no new hyperparameters on confirmation, causally advance state[864,1612), then warm up. On development machines reuse the exact existing checkpoint files; no refit. For future qualified confirmation machines this would mean new separately approved fits on their own[0,864), with training targets strictly inside864 and original fit acceptance rules. No confirmation model exists merely because a development checkpoint exists.

This compatibility proposal is **not automatically approved confirmation training** and does not silently supersede the original generic design's proposed combined fit+development refit before warm-up. That different1612-row refit would require a different explicitly approved training scope and new checkpoint registry; it has never happened in the current evidence. The JSON keeps the approved confirmation training boundary null. Adopt one track explicitly and version it before any protected values. Global scientific hyperparameters and development-selection cutoff remain unchanged either way; no final-outcome choice between tracks is permitted.

## Initialization and causal evaluation

Reconstruct ARIMA fitted state through its training cutoff once; bootstrap required lag history without assimilating fit observations twice. Advance fixed state across every allowed index864..1611, including missing events; no smoothing with future data, forecasts, residuals, interval support or retrospectively selected policy losses are imported during reconstruction. Preserve/check the genuine/missing streak, last genuine timestamp/age and telemetry-era state at entry. The new real-data driver must support validated initial era/history instead of weakening existing synthetic constructors. Record state/model/registry hashes and all cutoffs.

At1612 start ARIMA incumbent with empty matched losses, cold detector normalization/support and empty policy calibration; bind them to the provenance-checked current era. This is a proposed cold-start convention, not permission to import convenient M4A/M5B-2 outcomes. Issue warm-up forecasts only after their observations arrive and collect each policy's genuinely matured exact-target residuals. Missing targets/old-era scores cannot manufacture support;230 ticks do not guarantee100 usable recent errors after gaps/gates/resets. Do not lower support if intervals remain unavailable.

At1842 carry valid warm-up state, pending forecasts, drift/cooldown, loss/calibration buffers and telemetry era unchanged. Warm-up-origin outcomes may mature and update causal state during final arrival ticks but are excluded from final-origin performance metrics. Score only final **origins** i∈[1842,2304) with genuine exact targets i+h≤2303; last scoreable origin is2302 at h1 and2291 at h12. Later issued targets remain pending; do not open more data to finish them. Count unissued attempts separately.

Each tick: reveal genuine/missing → resolve earlier exact targets → telemetry reset/age, matched selector feedback, genuine drift/calibration updates → update each fixed model once → expert shadows → frozen selection and actual full-policy centers →90/95 interval issuance → immutable record before next reveal. No interval/coverage/drift feedback changes centers or selection. Genuine target losses become available only at their exact arrival. All source versions, model availability, training/scaling/state cutoffs must be≤origin.

## Denominators and metrics

Retain individual machine/policy/horizon/nominal outputs before any aggregate:

1. **Own policy:** all declared origins, issued points, genuine exact-target scores, missing targets, pending, abstentions, genuine interval-unavailable counts, fallback/numerical failures and gate reasons. Own interval availability=available intervals/issued centers, plus available genuine-scored intervals/all genuine matured centers. Coverage=covered/available genuine-scored intervals; null if denominator zero. Never count missing/pending as hits, misses or zero widths.
2. **Expert-matched:** identical origin/horizon/exact target/context, genuine target and genuine expert-issued ARIMA/XGBoost/adaptive centers; persistence baseline is matched on those same origins. Exclude fallback from expert ranking/comparison, while still disclosing its complete-policy effects.
3. **Complete-policy point comparison:** common genuine targets with all P/F-A/F-X/A actual centers, including each policy's own fallback. Retain own-policy masks alongside this common mask. Do not substitute later observations for unavailable models or hide abstentions.
4. **Intervals:** each own-policy result plus a common genuine-available interval mask at each horizon/nominal level. Report both masks' sample counts and exclusions. Narrow intervals on an easier mask do not establish reliability superiority.

For error e=y−prediction, MAE=mean|e|; RMSE=sqrt(mean e²), CPU percentage points. Coverage uses inclusive L≤y≤U. Width=U−L; report mean/median at issuance and genuine-scored width separately. Interval score IS=(U−L)+(2/alpha)max(L−y,0,y−U), alpha0.10/0.05. Report absolute coverage gap, raw endpoints outside[0,100], zero/unavailable/unbounded cases honestly. MAPE is optional only away from zero, with exclusions; it is not the primary result.

Report current/lifetime genuine support, earliest/latest target, clipping, normalization count, warning/alarm timestamps/rates per elapsed day, switches per100 policy decisions, default resets distinct from switches, fallback/abstention denominators, model update/forecast failures, no-refit attempt counts, total/segmented runtime and process RSS. Measure latency percentiles if instrumented before execution; otherwise mark unmeasured. A detector alarm alone is not labelled true concept drift on real data.

Aggregate **equal-machine arithmetic means of per-machine metrics**, including mean per-machine RMSE, not pooled target-weighted RMSE. If any prespecified machine has an undefined primary metric, mark the primary macro incomplete/null and report valid/planned counts; an explicitly secondary available-machine mean must not masquerade as the planned macro. Zero valid targets are not perfect performance. Report failures for every eligible prespecified machine; never replace by final performance. Do not treat adjacent/overlapping h12 errors as independent replications. Current plan is descriptive; inferential significance/bootstrap choices are not invented after viewing final data.

## Integrity acceptance and go/no-go

Require suffix-perturbation invariance, exact h12 delay, no duplicate assimilation, no fitting during replay, fixed parameter/scaler hashes, schema/grid/value rules, no-overwrite and policy/interval provenance. Reconcile complete point attempts=issued+abstained; issued=genuine scored+missing target+pending. Reconcile shadows' separate gated/numerical/unavailable attempts. For each interval level distinguish center-unavailable, null-support, genuinely scored, missing and pending. Replay saved calibration/selector/drift decisions independently; verify95/90 nesting and all protected historical hashes before/after.

**NO-GO now.** Gates required before any protected data: (a) approved qualification-only scope and trusted prefix hashes, (b)≥6 full confirmation admissions with frozen roles/order, (c) approved training-boundary track/permission and registry of valid per-machine checkpoints, (d) separately verified real-data typed driver including complete fixed policies and boundary initialization, (e) accepted globally frozen protocol/settings/metrics, (f) explicit block/machine execution authorization and immutable manifest. Qualification, training, warm-up/final and confirmation evaluation are separate permissions. The proposed JSON deliberately leaves them false. A subsequent inspected-data revision must be called exploratory and needs a new untouched set for independent confirmation.

# Confirmation qualification readiness and separate authorization proposal

**NO-GO for independent evaluation.** This M8A document uses existing M2B/M2C metadata only. No new confirmation observation, mask, raw source, restricted suffix or key has been opened. Nomination is not qualification. The original M2B result remains15 failures under strict complete-prefix v1; it is not rewritten by the later V2 engineering protocol.

## Frozen V2 rules

Sources: [M2D protocol](../../../../configs/dafr_engineering_pilot_v2.json), [M3B-1 development-only admission](../../m3b1_development_qualification_v1.md), [M2C evidence](../../m2c_missing_data_feasibility.md). Use the original1152-bin prefix, zero-based indices[0,1152), raw elapsed[0,345600), right-edge labels300..345600 seconds at300-second cadence. Preserve all failed positions; never choose the longest clean subset or compress time.

Every bin keeps M2B validity: at least24 valid unique raw samples, no conflicting CPU duplicates, internal/leading/trailing gaps at most30 seconds; invalid/nonfinite/out-of-range raw CPU excluded under the original rules, no imputation/clipping/recovery of failed means. Existing hash-verified M2B status is authoritative; M8A does not resample or revalidate CPU values.

All six screens must pass: at least500 genuine bins; coverage at least75% (864/1152); longest genuine run at least48 bins; at least40% learned origins divided by **all1152 grid positions**; at least400 potential genuine exact-target pairs separately h1/h12. Origin i is eligible only if i≥23 and all mask[i−23:i+1] are genuine. A pair additionally needs i+h<1152 and mask[i+h] genuine. Future target-mask access is permitted only for this offline quality count, never a forecasting issuance gate. Missing runs, leading/trailing gaps and complete timeline checks must also be recorded. Thresholds are development-informed engineering choices, not validated optimal screens or a guarantee of sufficient calibration support.

## What existing metadata prove

| Machine | Original nomination | Genuine bins | Coverage | Verdict now |
|---|---|---:|---:|---|
| m_295 | primary1 |891|77.34%|Incomplete: other structural screens unknown|
| m_66 | primary2 |926|80.38%|Incomplete: other structural screens unknown|
| m_1878 | primary3 |815|70.75%|Known failure of necessary coverage gate|
| m_197 | primary4 |919|79.77%|Incomplete: other structural screens unknown|
| m_3836 | primary5 |812|70.49%|Known failure of necessary coverage gate|
| m_1022 | primary6 |935|81.16%|Incomplete: other structural screens unknown|
| m_1194 | reserve1 |912|79.17%|Incomplete: other structural screens unknown|
| m_1059 | reserve2 |915|79.43%|Incomplete: other structural screens unknown|
| m_2502 | reserve3 |872|75.69%|Incomplete: other structural screens unknown|

**Zero verified full V2 confirmation admissions; two known necessary-gate failures; seven incomplete candidates.** Existing aggregate raw counts and duplicate/CPU-cell checks do not identify the chronological1152-bit validity mask. They cannot determine longest genuine runs or24-slot-origin/target pairs. No such full-screen evidence was found in the reviewed authorized reports/configurations. Thus metadata alone cannot establish the seven remaining admissions. The [machine-readable inventory](confirmation_metadata_inventory.json) retains unknowns as null, not fabricated passes or zeros.

Development primaries m_505,m_1426,m_3028 have separate prefix-only V2 admission; reserves m_3276,m_1029,m_2104 are not promoted. Their admission is not transferable to confirmation. Maintain six confirmation primary slots and reserve order. Fill a failed slot only with the next eligible same-role reserve after **every** screen is checked; do not promote by forecasting performance. With only seven aggregate-coverage passers, six qualified machines are possible but not established. If fewer than six ultimately qualify, stop the proposed independent study and seek new independently nominated data under a new frozen plan; do not lower screens.

## Proposed qualification-only authorization — NOT EXECUTED

This is the precise scope of a **future separate request**, not permission conferred by M8A:

1. Permit only the seven incomplete IDs m_295,m_66,m_197,m_1022,m_1194,m_1059,m_2502. Keep m_1878/m_3836 excluded using existing evidence; no further observations are needed to establish those failures.
2. Canonical candidate containers are `data/processed/dafr/m2b_v1/qualification_20261030_001/five_minute_prefix/<machine_id>.csv`, each exactly1152 rows, indices[0,1152). Do not open any suffix, raw archive/subset, SQLite stage, encrypted artifact, key or path outside this allowlist. Reject symlink redirection, duplicate/skipped/off-grid timestamps, truncation and overflow.
3. First obtain **prefix-only original digest receipts** from trusted existing acquisition provenance or an approved metadata-only export. Reviewed public aggregate metadata do not supply those per-file digests; M8A has not opened a technical qualification payload to retrieve them. Freeze those expected hashes before access and refuse if missing/mismatched. Hashes newly computed from an unknown file alone are not a trusted provenance comparison. Use the existing official archive SHA only as source-release provenance, not a substitute for a per-prefix integrity receipt.
4. Approve a bounded **mask-only projection**, retaining `timestamp`, `bin_end_seconds`, `quality_status` and original failure-reason categories. The current CSV schema also contains `value`. Reading its container bytes is a narrow additional data-access permission even if numerical CPU is never used; do not disguise it as metadata already authorized. The preferred implementation is an isolated extractor that projects the approved fields, discards the CPU token without numerical conversion, never logs/displays/stores it and exports a hashed1152-row mask receipt. If that physical container read is not approved, provide a trusted mask-only export instead. Original CPU-range/per-bin validity is inherited from authenticated M2B status, not silently rechecked by examining CPU values.
5. Compute only structural counts/runs and the exact frozen screens; no CPU mean/distribution/plot/correlation, lag-feature values, model predictions, residuals, intervals, drift state, outcome ranking or hyperparameter tuning. Read at most8064 mask positions for the seven machines. Prefix-mask target availability may count potential pairs but must not affect actual forecast issuance rules.
6. Produce new versioned per-machine counts, pass/fail reasons, aggregate/source hashes, all original roles/order, fixed-order reserve decisions and provenance. Do not modify M2B/M2C/M2D or promote a machine before all screens pass. Qualification does not prove model convergence, sufficient out-of-sample intervals, independent workloads or suffix quality.
7. Use no key and perform no decryption. Keep all execution/training/evaluation flags false. Prefix qualification, parameter fitting, real-data integration and suffix evaluation are **separate authorizations**, not one blanket permission. Hash old artifacts before/after; exclusive outputs only.

Even a successful mask check would not authorize independent M8B execution. A fully frozen accepted protocol, actual real-data typed integration, prespecified per-machine model-fitting authorization/artifacts, state reconstruction, warm-up policy and an explicit protected-block execution request remain necessary. See [proposed final evaluation](proposed_final_evaluation_protocol.md).

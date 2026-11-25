# F2 — Visual refinement and presentation readiness

## Outcome
The approved navy/teal research observatory foundation is preserved. F2 changes only frontend presentation components/styles and frontend QA documentation. No research execution, protected observations, fitting, calibration, backend service or authentication was introduced.

## Exact UI changes
- Shortened desktop hero through reduced padding, headline margins and orbit dimensions; retained headline, grid, orbit illustration and CTA. At 1440 × 1000 the hero measures 256.47 px and the comparison panel begins at y=666.56 (approximately 80 px earlier than the F1 capture).
- Increased sidebar metadata, navigation, source links, status text, scope badges, chart annotations, rules, captions and table text. Source links have additional vertical hit space.
- Standardized metric card spacing, baseline-aligned numerical values and explicitly labeled both error metrics in CPU percentage points (`CPU pp`). Retained tabular numerals and genuine counts.
- Renamed the comparison heading to “Fixed and adaptive forecast errors.” Shortened only the plotted adaptive label to “Adaptive” to prevent mobile label collision; the table retains “Frozen adaptive.”
- Clarified NO-GO as a research qualification/approval boundary. Kept two necessary coverage failures, seven incomplete candidates and zero verified full qualifications visible.
- Improved panel heading hierarchy and alignment, dropdown/segmented-control sizes, chart ticks/legends, figure-opening affordances, supporting explanations and table typography across all four pages.
- Preserved scope colors/labels for development, retrospective development and synthetic engineering. Kept the negative adaptive result, drift misses and interval undercoverage explicit.
- Kept restrained existing hover/focus effects; reduced hover lift. Preserved prefers-reduced-motion overrides. Added keyboard focusability and visible focus outlines to horizontally scrollable evidence tables.

## Verification
- Adapter suite: **8/8 passed**; TypeScript: **passed**; ESLint: **passed**; production build: **passed**. See build.log. Initial terminal path mistakes were corrected; the final checks ran from frontend/ and passed.
- All **34** available allowlisted exports are byte-identical to originals and their recorded SHA-256 hashes. See source_verification.json. Source registry/adapter code and allowlist unchanged.
- **998/998** protected research hashes match, zero mismatches. Review-package ZIP and manifest hashes also unchanged. See preservation.json.
- All four routes at **1440 × 1000**, **820 × 1180**, **390 × 844**: correct heading, zero broken loaded images, document scroll width equal to viewport width. See responsive.json and 12 full-page JPGs.
- Visual review: overview desktop/mobile, adaptation desktop and reliability mobile confirmed readable stacking/scopes and intact charts. Wide evidence tables and the synthetic drift chart deliberately scroll within their own containers rather than overflowing the document.
- Navigation and filters exercised: h=12, m_505 and macro comparison; source dialog opens with 34 links and Escape closes it. Mobile navigation works; Escape restores menu-button focus. Skip link focuses main-content without changing the active route.
- Checked rendered h=12 expert-matched macro: ARIMA MAE **6.797972**, adaptive **6.896834**, common genuine targets **1,272**. m_505 ARIMA **6.069862**, adaptive **6.372762**, common targets **417**. Overview delta remains **+0.0989 CPU pp**, higher is worse.
- Checked M7B growing/adaptive h=12: interval availability **237/348 = 68.10%**; 90% observed coverage **162/237 = 68.35%**; 95% observed coverage **185/237 = 78.06%**. Availability and coverage denominators remain distinct.
- Browser console returned no warnings/errors during control verification. Existing CSS reduced-motion and visible keyboard focus rules retained; no animation introduced.

## Limits
This is responsive/manual accessibility QA, not a formal WCAG audit or screen-reader certification. Reduced-motion behavior was inspected in CSS rather than OS-preference emulation. Original figure raster labels remain as published; full-resolution opening is available. Build retains upstream dependency directive/chunk-size notices, with no build failure. No research tests/experiments were rerun; only the eight read-only adapter tests ran. Archived traces/interval bands remain explicitly unavailable where no approved source exists.

## Files
Modified: frontend/src/App.tsx and frontend/src/styles.css. Added: frontend/qa/f2/QA_REPORT.md, build.log, preservation.json, responsive.json, source_verification.json, screenshots (four pages × three widths), overview-preview.jpg and file_manifest.json. Existing F1 screenshots/reports remain preserved.

F2 is complete. No backend, live data, training or new research milestone is authorized by this UI work.

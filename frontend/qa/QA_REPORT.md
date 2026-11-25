# Frontend F1 — implementation and QA report

**Complete; stop for visual review.** Local development URL: **http://127.0.0.1:5173/**. No remote deployment or research execution was performed. All created/modified project files are isolated under `frontend/`.

## Delivered interface

Four working hash-navigated pages: Overview, Forecast comparisons, Adaptation & drift, Reliability & evidence. Dark navy/charcoal surfaces, teal/cyan accents, restrained amber limitation signals, responsive cards/charts/tables, original verified figures and a source-provenance modal. Decorative hero geometry is not a CPU observation chart. No live telemetry or production-health claim is shown.

Forecast comparison controls cover h1/h12, MAE/RMSE, expert/complete-policy masks and macro/per-machine reports. The interpretation explicitly labels the negative result as **macro**, so a selected machine's better/worse values are not confused with the aggregate. The adaptation view uses the actual three saved switch rows, separately from synthetic drift counts. Reliability keeps M7A mocks separate from M7B real-backend synthetic inputs, shows both90/95 levels and genuine denominators, and retains undercoverage. Unsupported traces, raw drift timelines and interval bands are unavailable rather than invented.

## Data integrity and boundaries

-34 explicit existing CSV/JSON/Markdown/PNG sources; no dataset/model/private-ledger reader or research-module import.
- Build-time static adapter; no runtime filesystem picker, model API, upload, database, training, forecasting, rule-editing or confirmation endpoint.
- Schema checks reject nonfinite/duplicate/invalid metrics, incorrect coverage/availability ratios, fabricated qualification counts and execution-enabled research settings. Missing sources remain unavailable. Null support produces unavailable coverage, not a zero.
- Five PNGs are checked against the existing M8A figure hash inventory. All34 public copies match their original SHA-256 and were fetched from the local server byte-identically.
- The development server accepts only the frontend filesystem root. A local HTTP request for the nonprivate parent repository README returned403; no private file was requested to test the boundary.
- [Metric provenance map](provenance-map.json) records displayed groups, columns, filters, derivations, paths, scopes and hashes. The in-app Sources dialog exposes the same artifact provenance. Historical research configurations are references, not execution authority.

## Automated frontend checks

| Check | Result |
|---|---|
| `npm run typecheck` | Passed |
| `npm run lint` | Passed |
| `npm run test:data` |8 passed,0 failures |
| `npm run build` | Passed; actual static production bundle created |
| All allowlisted report sources |34/34 available and validated |
| Local static HTTP hash checks |34/34 match |
| Outside-root filesystem request |403 |
| Final npm audit |0 known vulnerabilities |

Only frontend report-adapter tests were executed. The historical409-test research suite was not rerun because it can build/train synthetic fixture models. F1 does not borrow that historic count as new UI verification.

Initial dependency installation failed under sandbox DNS restrictions; network permission resolved it. Local listening also needed permission and then succeeded on127.0.0.1:5173. A missing CSS type declaration was fixed with the Vite client types. A patched development-only minimatch override removed the initial npm advisory chain, with lint/typecheck/tests/build verified after installation. No research artifact or Python environment was altered to resolve frontend issues.

## Observed browser QA

Tested in the Codex in-app browser, desktop1440×1000, tablet900×1000 and mobile390×844. Document widths matched viewport widths (1440/900/390); no page-wide horizontal overflow. Dense tables and the drift chart use contained horizontal scroll; on390px mobile, the drift chart's324px viewport contains760px of legible chart content.

Verified navigation between all four pages; h1/h12 and MAE/RMSE toggles; m_505 and macro comparison; expert and complete-policy masks; M7A/M7B selection; fixture selection; source modal open/Escape close. Concrete rendered checks included:

- h12 expert macro ARIMA MAE6.797972 versus adaptive6.896834; complete-policy common count1340.
- All three h12 switch summaries at indices1294,1440,1582, with actual support/dwell fields.
- M7B growing h12 coverage68.35% at90% nominal, with237 available intervals /348 genuine matured centers (availability68.10%). Coverage's denominator is available intervals, not all348 centers.
- M7A insufficient-support h12: coverage/width/interval score **Unavailable**, available0 /48 genuine matured; no fabricated observed-coverage bar. Forecast availability remains a separate100% issued/attempted ratio.
- Historical milestone counts315/341/381/409 and M8A304/105. Missing skip-count fields display “Not recorded,” not an invented zero.
- Mobile menu opens/closes, closed navigation is removed from keyboard reach via visibility, focus wraps within the open menu, Escape restores the opener, page navigation focuses the heading. Skip-to-content focuses main without resetting the route. Sources uses native modal focus handling.
- Captured final browser logs contained0 errors and0 warnings. Viewport override was reset; the dashboard was left open as a deliverable.

Reduced-motion CSS disables transitions/animations and hover transforms; chart animation is disabled. The OS reduced-motion preference was not changed/emulated. Text tables accompany charts. This is not formal WCAG certification, a full assistive-technology audit or cross-browser/device certification.

## Screenshots

- [Desktop overview](01-overview-desktop.jpg)
- [Desktop forecast comparison](02-forecasts-desktop.jpg)
- [Desktop adaptation/drift](03-adaptation-desktop.jpg)
- [Desktop reliability](04-reliability-desktop.jpg)
- [Insufficient-support unavailable state](05-insufficient-support.jpg)
- [Mobile reliability](06-reliability-mobile.jpg)
- [Mobile overview](07-overview-mobile.jpg)
- [Mobile forecast comparisons](08-forecasts-mobile.jpg)
- [Mobile adaptation/drift](09-adaptation-mobile.jpg)
- [Tablet layout](10-tablet.jpg)

Screenshots are real UI captures; no research trace or band was fabricated. Some screenshots precede final wording-only accessibility/interpretation adjustments; the final DOM checks above use the completed interface. Metrics and evidence remain identical.

## Files and remaining limits

Primary new files: package/lock files, TypeScript/Vite/ESLint configuration, `index.html`, `src/App.tsx`, `src/data.ts`, `src/main.tsx`, `src/styles.css`, `src/vite-env.d.ts`, `scripts/build_evidence.py`, `tests/test_evidence.py`, isolated `.gitignore`, README and this QA/provenance/screenshots directory. Build-time public exports/generated JSON and installed dependencies/build/cache are local generated outputs; they do not replace research sources. `final_verification.json` and `file_inventory.json` enumerate delivered files/checksums.

Final preservation verifies **998 pre-existing research artifact hashes**, including historical model fingerprints and all prior milestones. Original ARIMA/XGBoost outputs, configs, code, reports, checkpoints and protected blocks are unchanged. The existing review ZIP/manifest checksums are also checked. No original file was modified; no Git commit/push was performed. Only allowlisted public reports/figures were copied into the app's presentation assets.

Non-blocking build notices remain: a roughly890kB JavaScript chunk (about221kB gzip) and Lucide's upstream `use client` directive notices in a client-only bundle. The production build succeeds; chunk-size suppression was not used. Performance splitting, wider browser/contrast testing and visual refinements are deferred until user review. Current scope is an archived research dashboard—not full DAF-R efficacy, independent confirmation, calibrated real-world coverage or a live CPU service. No further research/frontend milestone starts automatically.

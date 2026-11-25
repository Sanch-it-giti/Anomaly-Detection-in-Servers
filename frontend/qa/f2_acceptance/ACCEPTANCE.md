# F2 final frontend acceptance

Status: **PASS — scoped final acceptance QA complete**.

## Verified defect and minimal correction
The Reliability & Evidence coverage chart used the default Recharts tooltip cursor. Keyboard activation reproduced a `.recharts-tooltip-cursor` SVG path with `fill="#ccc"`, covering one category's full plotting height. This was an intentional library interaction highlight, not corrupt chart rendering, but it was visually intrusive in this dashboard.

The only application change in this acceptance pass is the coverage chart Tooltip `cursor={{ fill: '#4adecb0d' }}` in frontend/src/App.tsx (teal at approximately 5% opacity). No CSS, chart data, tooltip formatter, accessibilityLayer, axes, scales, model code or research source changed. Keyboard ArrowRight again produced the same tooltip (95% nominal, nominal 95.000, observed 87.645), with the new cursor fill verified in the rendered SVG. See coverage-keyboard-highlight.jpg.

## Verification receipts
- Eight adapter tests passed: tests.log.
- TypeScript passed: typecheck.log.
- ESLint passed: lint.log.
- Production build passed: build.log. Existing upstream dependency directive and chunk-size notices remain non-blocking.
- All 34 allowlisted source hashes and byte-identical public exports match. All 998 protected research hashes match, with zero mismatches: integrity.json.
- All four routes checked at 1440×1000, 820×1180 and 390×844. Document width equals viewport width in every case; no page-level horizontal overflow. At each check scrollY=0, tooltip count=0, cursor overlay count=0: responsive.json.
- Four clean desktop top-of-page viewport screenshots captured at 1440×1000: overview-desktop-top.jpg, forecasts-desktop-top.jpg, adaptation-desktop-top.jpg, reliability-desktop-top.jpg. No tooltip overlays are present. Keyboard focus styling may remain visible; this is an accessibility affordance.
- Keyboard checks: skip link focuses main-content; mobile menu navigation and Escape restore the opener; horizontally scrollable table accepts keyboard ArrowRight (40 px movement) with a solid visible focus outline. Chart arrow navigation retains tooltip output: keyboard.json and the highlighted screenshot.

## Remaining defects and scope limits
No blocking frontend defect found in this pass. Wide evidence tables and drift labels retain intentional local horizontal scrolling on small screens. Existing research-source limitations, independent-confirmation NO-GO, negative adaptive results and unavailable trace/interval bands are preserved. No formal screen-reader certification or full WCAG audit is claimed. The drift chart's separate default cursor was not changed by this narrowly scoped coverage correction.

No models, experiments, calibration, protected evaluation blocks or new milestone were executed. Existing F1/F2 QA receipts were preserved; this acceptance evidence is separate.

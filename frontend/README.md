# DAF-R Research Observatory — Frontend F1

An isolated, read-only research dashboard built with React, Vite, TypeScript, Tailwind CSS, Recharts and Lucide. It presents existing reports; it is not a live forecasting service or research execution interface.

## Start locally

Tested here with Node24.14.1, npm11.11.0 and Python3.13 (standard library only for the adapter).

```bash
cd /Users/sanchitkhandelwal/Desktop/server-resource-forecasting/frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173/**. The development server is loopback-only. In this managed environment, package installation and local socket binding required network/listen permission; those steps succeeded. On an ordinary local terminal they should use the terminal's normal permissions. If port5173 is occupied, the server fails explicitly rather than silently choosing another URL.

`predev` and `prebuild` run `scripts/build_evidence.py`, which reads only34 explicit report/configuration/figure paths. It copies approved artifacts into `public/evidence/` and writes a typed-consumed static snapshot to `src/generated/evidence.json`. No Python research module, dataset loader, trained checkpoint or private ledger is imported. Missing files become unavailable; malformed present sources fail validation rather than invent values. Generated exports can be regenerated; original artifacts are never written.

## Pages

- **Overview:** project/component status, retrospective macro metrics and independent confirmation NO-GO.
- **Forecast comparisons:** h1/h12, MAE/RMSE, equal-machine/per-machine and expert/complete-policy masks, original verified figures and negative adaptive result.
- **Adaptation & drift:** frozen rules, three actual saved h12 switch summaries and separately labelled synthetic alarm/warning findings. No fabricated raw drift timeline.
- **Reliability & evidence:** M7A/M7B selectors kept separate,90/95 coverage/width/interval scores, genuine denominators, availability, missing/pending counts, historical test milestones and qualification blockers. Interval bands are explicitly unavailable.

Every metric group has source links. The Sources dialog shows original path, scope, availability and SHA-256. `qa/provenance-map.json` describes selectors, columns and derivations. Human interpretations cite existing reports; no model/rule is tuned to improve the presentation. M7B's full409-test result is historical; M8A's304 passes/105 fitting-dependent skips remain separate.

## Checks and production output

```bash
npm run typecheck
npm run lint
npm run test:data
npm run build
npm run preview
```

Preview serves the static build at **http://127.0.0.1:4173/**. There is no production API/server code in this app. The development Vite filesystem allowlist is restricted to `frontend/`; a request for the parent repository README was verified403. No upload, arbitrary-path picker, parameter editing, training, forecast execution, database write or confirmation route exists. No public deployment was performed.

Eight adapter tests cover actual CSV/JSON schemas, missing artifacts, invalid ratios, duplicate comparisons, finite numbers, source boundaries, invented qualification counts and execution-enabled configurations. The eight tests operate only on existing report copies and temporary output directories; they fit no models. Historical research tests/experiments are not rerun by F1.

The initial npm advisories originated in a development-only minimatch dependency. A patched `minimatch:^11.0.1` override was installed and verified with the full frontend checks; the saved final npm audit reports zero known vulnerabilities. The lockfile records actual resolved versions. No force-downgrade of the application stack was used.

Vite's production build succeeds with a non-blocking large-chunk warning (about890kB JavaScript /221kB gzip) and upstream Lucide `use client` directive notices. This client-only app does not implement React Server Components. Code-splitting can be considered after visual review; no warning threshold was raised to hide the message.

## Accessibility and responsive behavior

Desktop, tablet and mobile layouts; responsive/off-canvas navigation; native select controls; visible focus styles; a skip-to-main link; keyboard focus wrapping and Escape for the mobile menu; native modal focus trapping; text tables alongside charts; and reduced-motion CSS. Dense tables and the eleven-category drift chart scroll **within** their panels on mobile. A formal WCAG/assistive-technology certification and multi-browser test matrix are outside F1.

## Files and evidence boundary

All new project files are inside `frontend/`. Existing research code, configuration, results, data and review package were not edited. `qa/QA_REPORT.md` contains observed browser checks, limitations and screenshot links; `qa/final_verification.json` records preservation and check results. Node modules, local npm cache, build output and generated report exports are ignored by the isolated `.gitignore`.

The public report exports contain **only** the approved allowlist, not an arbitrary filesystem mirror. Do not broaden that allowlist to include archives, raw CPU, keys, encrypted suffixes, checkpoints or JSONL event ledgers. Incomplete artifacts should stay unavailable. This presentation does not authorize independent evaluation, qualification, model fitting or M8B. F1 ends with visual review before further refinement.

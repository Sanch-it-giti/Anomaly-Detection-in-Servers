# M7B runtime and memory

Whole saved run including synthetic checkpoint build, three-control replay and independent audits: **160.846943seconds**. Peak process high-water RSS: **729448448bytes =695.65625MiB**. Full409-test suite ran separately in182.178seconds.

| Fixture | Replay/write seconds, before later audit |
|---|---:|
| continuous | 50.583673 |
| growing | 42.841418 |
| gaps_failures | 41.652014 |
| update_failure | 19.192149 |

Numbers include interval-on, interval-off and unchanged M6B real-backend controls, plus immutable output writing. Process high-water RSS is cumulative across models, prior fixtures and audits; it is not isolated calibration memory. The guard is4GiB per replay tick, with a2304-tick per-fixture cap. Current active calibration is at most eight buffers ×288 errors; full small-run audit ledgers remain in memory. Production p95 issuance latency and long-duration storage were not measured. No8GB resource failure occurred.

Synthetic checkpoint generation happens once before replay:96 generated fit values, actual ARIMA(1,1,1) filtering with known coefficients (no optimizer), and two small direct-horizon native XGBoost fits. There were zero replay fit attempts, no real-data fitting, no historical model refitting and no dependency installation. The isolated synthetic checkpoint bank is retained only in this new run for reproducibility and is never added to the historical registry.

# M7A runtime and memory

Synthetic execution only. Whole saved run, including independent audits: **55.365015seconds**. Peak process high-water RSS: **301.125MiB** (315752448bytes). All ten fixtures are serial, containing3430 total ticks; each fixture is below the2304-tick cap. The replay guard checks process RSS against4GiB each tick. Detector/selector code is unchanged. No model is fitted or loaded by this interval runner.

| Fixture | Ticks | Replay/write seconds, excluding later audit |
|---|---:|---:|
| stable | 360 | 4.969315 |
| growing_variation | 360 | 4.788826 |
| shrinking_variation | 360 | 4.742448 |
| abrupt_change | 360 | 4.876837 |
| isolated_extreme | 360 | 4.841214 |
| short_gaps | 360 | 4.746453 |
| long_gap_recovery | 360 | 4.043606 |
| insufficient_support | 60 | 0.558169 |
| numerical_failures | 360 | 4.775449 |
| calibration_expiry | 490 | 9.960270 |

Times include paired enabled/disabled point/selector/drift replay and immutable ledger writing; process high-water RSS includes interpreter/auditor overhead and previous fixtures. The test suite ran separately,381 tests in106.042seconds. These numbers are not isolated calibrator latency, p95 issuance latency, production throughput or an OS memory profile; those are unmeasured. Active calibration support is bounded at eight policy/horizon buffers ×288 residuals, with separate immutable90/95 records. Full small-run audit ledgers remain in memory; production long-duration storage is outside scope. No TensorFlow installation, real-data training or dependency installation occurred.

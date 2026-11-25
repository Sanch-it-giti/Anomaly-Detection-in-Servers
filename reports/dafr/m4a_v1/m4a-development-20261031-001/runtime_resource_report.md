# M4A runtime and resource report

Serial run `m4a-development-20261031-001` completed its measured work in **103.377 seconds**, including reconstruction, scoped extraction, ledgers, metrics, twelve figures and checkpoint checks. Peak process RSS was **223,821,824 bytes (213.45 MiB)**. This is below the enforced **4 GiB** limit and suitable for the project's 8 GiB Mac budget for this measured workload.

Numeric thread environment limits were one. A separate watcher checked the operating-system process high-water RSS every 50 ms; replay/plot boundaries also checked it. This is a process RSS guard, not a guarantee against system-wide memory contention or a kernel allocation between samples. No other workload or larger scale was benchmarked.

| Machine | State reconstruction (s) | Replay incl. buffered ledger writes (s) | Whole-tick p95, no I/O (ms) | Whole-tick p95 with serialization/writes (ms) |
|---|---:|---:|---:|---:|
| m_505 | 2.705 | 23.216 | 51.424 | 54.566 |
| m_1426 | 2.565 | 23.468 | 51.778 | 54.951 |
| m_3028 | 2.538 | 23.328 | 50.124 | 53.171 |

Reconstruction includes loading/checking selected artifacts, rebuilding the fitted state from fixed parameters and 288 chronological updates through index 1151. It issues zero forecasts. Replay timing includes metrics bookkeeping but excludes the later plot generation. Initial imports, preflight historical-inventory/gate checks, final historical recheck, independent ledger auditing and test execution are outside the runtime JSON timer. Peak RSS is cumulative over the benchmark process, not incremental per-machine model memory.

Maximum measured policy-issuance p95 across machines, separately by horizon:

| Policy | h=1 (ms) | h=12 (ms) |
|---|---:|---:|
| Persistence | 0.0476 | 0.0364 |
| ARIMA | 1.1203 | 1.1407 |
| XGBoost | 18.7085 | 18.6691 |

Policy issuance includes gating, validation, parameter/state fingerprints, forecast creation and ledger insertion; it excludes tick assimilation, scoring and file writes. Each distribution includes gated fallback decisions. Backend forecast-only p95 (successful attempted experts, both horizons combined) was at most 0.875 ms for ARIMA and 8.116 ms for XGBoost. These latency scopes must not be interchanged.

Each learned adapter recorded **748 updates** (288 historical reconstruction + 460 new ticks), preserving missing-event steps. Successful expert forecast calls per adapter were 862,872,872 for the three machines (both horizons). State/hash validation overhead explains some of the difference between backend and whole-policy times.

No numerical update failures, numerical forecast failures, stale-state responses, quarantined state, RSS stops, or fitting calls occurred. An explicit fitting guard blocked optimizer/training entry points during the benchmark. The parameter fingerprints were validated throughout replay and checkpoint bytes were verified afterward. No TensorFlow, LSTM or new dependency was installed.

Matplotlib built its font cache in the permitted temporary directory during the run. No plotting error remains. All twelve images were produced; representative forecast/error and temporal-loss plots were visually reviewed. Detailed exact timings, counters and scope definitions are in [runtime.json](runtime.json). Resource reporting describes this offline replay, not an end-to-end deployed service or a training benchmark.

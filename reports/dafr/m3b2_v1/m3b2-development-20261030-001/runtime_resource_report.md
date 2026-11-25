# M3B-2 runtime and resource report

Run: m3b2-development-20261030-001. All figures below are observed development execution costs, not estimated LSTM or production costs.

| Measurement | Observed |
|---|---:|
| Prespecified parameter fits | 27: 9 ARIMA and 18 direct XGBoost heads |
| Candidate streaming replays | 18 |
| Grid ticks per replay | 288 |
| Sum of recorded candidate fit wall times | 0.8364 seconds |
| Fit/replay/report-preparation stage before plotting | 168.1297 seconds |
| Full completion including plotting/font cache/integrity checks | 191.8276 seconds |
| Peak process RSS | 217,497,600 bytes (207.42 MiB) |
| Frozen RSS stop budget | 4 GiB |
| Maximum per-trial p95 adapter forecast duration | 0.015703 seconds |
| Numerical forecast/update failures | 0 |
| Rejected fits / captured fit warnings | 0 / 0 |

Run serially with OPENBLAS_NUM_THREADS=1, OMP_NUM_THREADS=1, MKL_NUM_THREADS=1 and VECLIB_MAXIMUM_THREADS=1. XGBoost training n_jobs=1 and loaded-booster nthread=1. No TensorFlow, GPU or parallel candidate fitting was used.

The memory guard samples the process high-water RSS every 50 milliseconds and checks it between operations. An excess would stop the worker and leave a versioned resource-stop receipt. The measured high-water mark remained far below 4 GiB. RSS values in individual fit/trial receipts are cumulative process maxima, not independently attributable model memory; native-library caches and plotting imports are included.

The p95 above covers adapter forecast calls, including their internal state/fingerprint checks. It excludes outer-driver context validation, all JSONL writes and other per-tick overhead. Whole-tick p95 was not separately instrumented, so the original end-to-end p95 target is not certified by this number. Replays include substantial provenance/hash and audit-I/O work; backend fit times alone are not total system latency.

runtime.json retains each machine/candidate's replay duration, model update/forecast counts and runtime, p95 forecast duration and peak RSS. runtime_metrics.csv presents those measurements alongside fit costs. The resource monitor did not trigger; no memory failure was hidden by fallback.

Matplotlib could not write its default user cache directory, and automatically used an allowed temporary cache. Font-cache construction contributed to the one-time plotting overhead; both figures were generated and visually verified. No dependency installation or permission workaround was performed.

This demonstrates computational feasibility for these small ARIMA/XGBoost candidates on the current Mac. It does not validate LSTM feasibility, cluster-scale processing, online refitting, or production latency.


# M3B-1 — LSTM sample and resource feasibility v1
Prepared 30 October 2026. No TensorFlow installation, neural network construction or training.

## Recommendation

**Defer LSTM from the initial M3B-2 training recommendation.** ARIMA and XGBoost provide a more defensible small first pilot while real-adapter behavior is verified. Label that pilot explicitly as two-expert development work, not a completed three-expert DAF-R evaluation.

LSTM fitting is not mathematically impossible with these samples, and parameter count alone is not a universal sample-size theorem. The limitation is whether a short, highly overlapping set of windows supports a meaningful neural comparison and generalization claim. Current evidence does not establish that. Do not address this by stacking a large network, duplicating sequences, or counting overlapping windows as independent samples.

## Genuine sequence support

Use the unchanged 24-genuine-bin input gate and exact genuine targets. The prefix-only split is fit [0,864), validation [864,1152), with first validation origin 864.

| Selected primary | Fit sequences h=1 / h=12 | Common validation targets h=1 / h=12 | Greedy disjoint fit spans h=1 / h=12 |
|---|---:|---:|---:|
| m_505 | 329 / 314 | 206 / 204 | 15 / 11 |
| m_1426 | 303 / 284 | 236 / 224 | 14 / 10 |
| m_3028 | 243 / 223 | 254 / 242 | 16 / 12 |

The disjoint-span diagnostic greedily counts nonoverlapping full input-to-target intervals [i−23,i+h]. It is **not** a statistical effective sample size, and separated intervals can remain correlated. It illustrates that 223–329 training windows are not that many independent workload episodes. Repeated seeds likewise do not create new workload samples.

There are three machines from one production cluster and only three days in each inner fit fold. The original four-day prefix is not four uninterrupted days. Missingness may relate to load, and a near-complete last-day validation block can differ from the earlier fit regime. Neither stationarity nor seasonality is established. Reserves remain unused for tuning, and no confirmation suffix is examined.

## Small optional architecture, if separately approved later

- Input: 24 elapsed grid slots × one genuine CPU feature, oldest first.
- One stateless LSTM layer with **8 units**, then a linear Dense(1).
- Separate direct h=1 and h=12 models; no pooling across machines.
- Batch size 32, Adam learning rate 0.001, MSE, 20 fixed epochs, shuffle=false.
- No dropout, recurrent dropout, bidirectionality or additional recurrent layers.
- Genuine-inner-fit min/max scaler, frozen and hashed; no whole-prefix fitting or clipping.
- Proposed sensitivity seeds 42,43,44, with every result retained. No best-seed selection.

For the standard four-gate LSTM parameterization with one input feature and u units, parameter count is 4u(u+1+1), plus u+1 for Dense(1). This is **329 parameters at u=8**, versus 1,169 at the research design's earlier 16-unit proposal. These are architecture arithmetic, not measured model behavior or a fit-quality guarantee.

The [official TensorFlow LSTM interface](https://www.tensorflow.org/api_docs/python/tf/keras/layers/LSTM) documents units, sequence/state behavior and inference options. Runtime/version compatibility on this Mac has not been verified. TensorFlow/Keras metadata remain absent in the current Python 3.11 arm64 environment.

Twenty fixed epochs are a proposed tiny exploratory budget, not validation-selected optimization. Do not use outer-validation early stopping to backdate a checkpoint selected with future validation labels. Fit-only nested stopping would require another explicit chronological split and verified counts, reducing already limited support.

## Tensor storage versus real process memory

At the largest selected h=1 training count, a float32 input tensor of shape (329,24,1) needs **31,584 bytes**; its scalar targets need 1,316 bytes. The largest selected validation feature tensor (254,24,1) needs 24,384 bytes. A single 329-parameter float32 weight vector needs 1,316 bytes before gradients, optimizer slots, activations and framework overhead.

These are deterministic storage estimates, not allocations or RAM benchmarks. TensorFlow installation/runtime, graph compilation, activations, temporary copies and allocator behavior can dominate the tiny model tensors. Fit one horizon, seed and machine at a time; release backend state between candidates. No GPU/Metal plugin is required by this proposal.

The project hardware budget is **8 GiB RAM**, verified in the earlier M2B evidence. A fresh hw.memsize query was denied by the current sandbox, so no new RAM-capacity measurement is claimed. This did not block read-only prefix analysis. Future fitting should record process RSS and macOS memory pressure, enforce the proposed 4 GiB process budget and stop rather than swap excessively.

The completed qualification/counting pass uses standard-library CSV/masks and modest memory; that cost does not establish neural-runtime feasibility. Likewise the M3A mock process peak is not an LSTM benchmark.

## What would improve the assessment

Longer independently nominated CPU series, more diverse predeclared development machines and longer genuine contiguous histories would support a stronger neural experiment. Such expansion must preserve confirmation isolation and source usage terms; no data were acquired here. More overlapping windows or reusing inspected NAB test outcomes are not substitutes.

Before any optional LSTM pilot: authorize the dependency step, verify compatible TensorFlow import and a tiny tensor operation, implement the real provenance/adapter contract, verify deterministic causal inference and memory limits, and approve a new execution configuration. No such action is authorized or performed in M3B-1.

There is **no validated statistical support threshold** declared here. The recommendation to defer is a conservative design judgment from the measured support and missing runtime verification, not a claim that an LSTM cannot fit.


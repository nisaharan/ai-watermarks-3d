# Apple M4 Pro device benchmark for Phase 2

Date: 1 September 2026  
Status: planning evidence only; no GPU execution is authorized by this benchmark

## Hardware and environment

- MacBook Pro `Mac16,7`
- Apple M4 Pro
- 14 CPU cores: 10 performance and four efficiency
- 20 GPU cores
- 48 GB unified memory
- PyTorch 2.13.0
- Metal/MPS is available outside the Codex filesystem sandbox
- Model: pinned `HuggingFaceTB/SmolLM2-135M-Instruct`

All completed frozen experiments used `device: cpu`. They remain valid and do not
need to be repeated merely because MPS is available.

## Measured benchmark

The benchmark used five real project prompts, 512 generated tokens per prompt,
temperature 0.8, top-k 40, and the actual Phase 2 generation and compact-scoring
code. Model loading and the short warm-up were excluded from the timed interval.

| Execution path | Generation | Twenty-key, three-length scoring | Total per five outputs |
|---|---:|---:|---:|
| CPU generation and CPU scoring | 21.27 s | 3.26 s | 24.54 s |
| MPS generation and MPS scoring | 18.04 s | 14.18 s | 32.23 s |
| MPS generation and CPU scoring, component estimate | 18.04 s | 3.26 s | 21.31 s |

Clean text generation was approximately 15% faster on MPS. Compact watermark
scoring was approximately 4.3 times slower on MPS because it consists of many
small, sequential keyed operations. Moving the entire pipeline to MPS would
therefore make this workload slower.

## Full-run planning estimate

The existing CPU estimate for two 20,000-prompt splits is approximately 39.5
hours. Scaling by the measured end-to-end ratios gives:

- CPU generation plus CPU scoring: approximately 39.5 hours;
- MPS generation plus MPS scoring: approximately 52 hours;
- proposed hybrid MPS generation plus CPU scoring: approximately 34-35 hours.

The defensible expected saving from the hybrid path is about five hours, or 13%.
Larger GPU generation batches and decoupled scoring might improve this further,
possibly toward 30-33 hours, but that range is unvalidated and must not be used as
a committed estimate.

## Authorization and reproducibility boundary

This benchmark does not change any frozen run or authorize the v2 null study. If a
future protocol uses MPS generation, it must first:

1. implement an explicit hybrid generation/scoring path;
2. validate native/compact parity on CPU scoring;
3. test deterministic restart and exact batch reuse on MPS;
4. benchmark the final prompt lengths and batch size;
5. freeze the device, PyTorch version, batch policy and environment fingerprints
   in the new protocol;
6. use the same frozen execution path for calibration and untouched confirmation.

Changing the device will change sampled texts. That is acceptable only for a new,
freshly preregistered study; it is not a reason to rerun or replace completed CPU
evidence.

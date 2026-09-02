# Novelty Matrix

Scale: **direct** = prior work already makes substantially the same contribution;
**partial** = important components exist but the proposed test differs; **adjacent**
= related method or evaluation; **open** = not found as a central contribution in
the targeted review. “Open” is not proof of novelty.

| Proposed contribution | Closest prior work | Overlap | Phase 1 judgement | Required differentiation |
|---|---|---|---|---|
| Context/n-gram survival explains robustness | [Kirchenbauer et al., ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/file/d78e9e4316e1714fbb0f20be66f8044c-Paper-Conference.pdf) | Direct | Withdraw as novelty claim | Cite as motivation and prior mechanism. |
| Detection as a function of attacked length | Kirchenbauer et al. 2024; [MarkMyWords](https://arxiv.org/abs/2312.00273); [WaterBench](https://aclanthology.org/2024.acl-long.83/) | Direct | Retain only as required control | Predeclare length interactions and fixed-length comparisons. |
| Cross-scheme robustness benchmark | MarkMyWords; WaterBench; [WaterPark](https://aclanthology.org/2025.findings-emnlp.1148/) | Direct | Do not position as primary contribution | Use existing benchmarks as comparators and narrow the aim to explanation/calibration. |
| Exact scheme-native effective-context measure | KGW reliability analysis and SynthID repeated-context logic | Partial | Candidate contribution | Mirror native tokenization, seed selection, masking, and eligibility; publish executable tests. |
| Incremental prediction beyond edit/lexical/semantic distance | Robustness papers report several attack and quality metrics, but do not centre this nested predictive test | Partial/open | Core confirmatory contribution | Compare predeclared nested models on held-out attack/model cells. |
| Transfer law across watermark families | Existing taxonomies distinguish context-dependent, context-free, and alignment detectors | Partial | Too broad as stated | Test heterogeneity; expect family-specific coefficients and explicit non-transfer. |
| Context destruction per unit attack cost | Benchmarks already assess robustness and quality/cost dimensions | Partial | Secondary contribution | Define denominator, quality frontier, uncertainty, and avoid a single opaque score. |
| Watermark vs generic detector independence | Reliability work and WaterPark compare detector families | Partial/direct | Secondary replication/extension | Report joint outcomes and error correlation; do not imply novelty from simple comparison. |
| Generic-detector subgroup fairness | [Liang et al. 2023](https://doi.org/10.1016/j.patter.2023.100779) and later audits | Direct | Replication only | Predeclare subgroup audit; state scope by detector, language, and corpus. |
| Public educational visualization | Many demos/toolkits exist | Adjacent | Communication output, not research novelty | Generate only from validated result tables and label scope. |

## Contribution statement approved for protocol use

> We evaluate whether exact survival of watermark-relevant seed contexts is a
> calibrated, scheme-aware predictor of post-edit detection, beyond length and
> conventional text-similarity measures, and characterize where that explanation
> fails across watermark families and attack mechanisms.

## Claims that are not approved

- “We discovered that context survival determines watermark detection.”
- “Context survival predicts any proprietary or unknown watermark.”
- “Our benchmark is the first comprehensive watermark robustness evaluation.”
- “A high watermark score proves authorship or misconduct.”
- “Generic AI detectors and keyed watermark detectors measure the same signal.”


# Source Register

This register contains the primary sources that materially affected the Phase 1
decision. “Verified” means the cited source was inspected for the stated point; it
does not reproduce or independently validate the paper's empirical findings.

| ID | Source | Type | Phase 1 use | Status |
|---|---|---|---|---|
| S01 | [Kirchenbauer et al., A Watermark for Large Language Models](https://proceedings.mlr.press/v202/kirchenbauer23a.html) | ICML 2023 | Foundational KGW mechanism | Verified |
| S02 | [Official KGW implementation](https://github.com/jwkirchenbauer/lm-watermarking) | Author code | Phase 2 implementation and configuration | Verified |
| S03 | [Kirchenbauer et al., On the Reliability of Watermarks](https://proceedings.iclr.cc/paper_files/paper/2024/file/d78e9e4316e1714fbb0f20be66f8044c-Paper-Conference.pdf) | ICLR 2024 | N-gram leakage, length, SelfHash, WinMax | Verified; closest prior art |
| S04 | [Dathathri et al., SynthID-Text](https://www.nature.com/articles/s41586-024-08025-4) | Nature 2024 | Structurally distinct production-scale scheme | Verified |
| S05 | [Google DeepMind SynthID-Text](https://github.com/google-deepmind/synthid-text) | Official code | Reference scoring and detector behavior | Verified |
| S06 | [Transformers SynthID-Text API](https://huggingface.co/docs/transformers/internal/generation_utils#transformers.SynthIDTextWatermarkingConfig) | Official docs/code | Preferred integration path and exposed context config | Verified |
| S07 | [Kuditipudi et al., Robust Distortion-free Watermarks](https://arxiv.org/abs/2307.15593) | TMLR-era primary manuscript | Edit-aligned contrast and transfer boundary | Verified at abstract/method level |
| S08 | [Sadasivan et al., Can AI-Generated Text be Reliably Detected?](https://arxiv.org/abs/2303.11156) | Primary manuscript | Recursive paraphrase threat baseline | Verified |
| S09 | [Krishna et al., DIPPER](https://arxiv.org/abs/2303.13408) | Primary manuscript | Controllable paraphrase baseline | Verified |
| S10 | [Rastogi and Pruthi, Revisiting Paraphrase Robustness](https://aclanthology.org/2024.emnlp-main.1005/) | EMNLP 2024 | Adaptive/reverse-engineering threat | Verified |
| S11 | [Piet et al., MarkMyWords](https://arxiv.org/abs/2312.00273) | Benchmark paper | Existing benchmark and metrics | Verified |
| S12 | [MarkMyWords repository](https://github.com/wagner-group/MarkMyWords) | Author code | Benchmark comparator | Verified |
| S13 | [Tu et al., WaterBench](https://aclanthology.org/2024.acl-long.83/) | ACL 2024 | Comparable-strength evaluation and task/length coverage | Verified |
| S14 | [Pan et al., MarkLLM](https://aclanthology.org/2024.emnlp-demo.7/) | EMNLP 2024 demo | Toolkit comparator | Verified |
| S15 | [MarkLLM repository](https://github.com/THU-BPM/MarkLLM) | Author code | Integration and attacks | Verified |
| S16 | [Liang et al., Watermark under Fire / WaterPark](https://aclanthology.org/2025.findings-emnlp.1148/) | Findings EMNLP 2025 | Broad robustness benchmark and evaluation guidance | Verified |
| S17 | [Mitchell et al., DetectGPT](https://proceedings.mlr.press/v202/mitchell23a.html) | ICML 2023 | Generic detector baseline taxonomy | Verified |
| S18 | [Bao et al., Fast-DetectGPT](https://proceedings.iclr.cc/paper_files/paper/2024/file/6b8c6f846c3575e1d1ad496abea28826-Paper-Conference.pdf) | ICLR 2024 | Generic zero-shot baseline | Verified |
| S19 | [Hans et al., Binoculars](https://icml.cc/virtual/2024/poster/33662) | ICML 2024 | Generic zero-shot baseline | Verified |
| S20 | [Liang et al., detector bias](https://doi.org/10.1016/j.patter.2023.100779) | Patterns 2023 | Non-native-English fairness risk | Verified |
| S21 | [Al Ali et al., Czech reassessment](https://aclanthology.org/2026.eacl-srw.20/) | EACL SRW 2026 | Evidence that bias is not uniform across settings | Verified |
| S22 | [Stowe et al., detector bias audit](https://aclanthology.org/2026.acl-long.109/) | ACL 2026 | Multi-attribute fairness audit | Verified |
| S23 | [Li et al., robust detection under human edits](https://arxiv.org/abs/2411.13868) | Primary manuscript | Detector-statistic robustness and Tr-GoF comparison | Verified at abstract/method level |
| S24 | [Li et al., A Statistical Framework of Watermarks for Large Language Models](https://arxiv.org/abs/2404.01245) | Primary manuscript | Pivotal statistics, detection efficiency, and explicit type-I error control | Verified at abstract level for publication refresh |
| S25 | [WaterJudge](https://aclanthology.org/2024.findings-naacl.223/) | Findings NAACL 2024 | Quality–detection frontier across watermark settings | Verified at abstract level for publication refresh |
| S26 | [Tamim and Khan, AI Watermark Evidence Fails Forensic Readiness](https://arxiv.org/abs/2607.16010) | 2026 preprint | Recent adjacent negative/operational framing | Verified at abstract level; not treated as canonical parity or calibration evidence |

## Search and interpretation notes

- Searches combined `watermark`, `context width`, `n-gram`, `survival`, `edit`,
  `paraphrase`, `robustness`, `benchmark`, and `detector`, then followed citations
  and official code links from relevant primary work.
- Search coverage is targeted rather than exhaustive. No quantitative meta-analysis
  was attempted because studies use incompatible schemes, strengths, models,
  lengths, attacks, quality constraints, and false-positive operating points.
- Therefore the Phase 1 report uses comparison tables and an author-coded novelty
  overlap chart, not a chart aggregating incompatible performance numbers.
- Preprints were used where they are foundational or no inspected proceedings page
  supplied the needed method detail. Peer-reviewed sources and official code were
  preferred when available.

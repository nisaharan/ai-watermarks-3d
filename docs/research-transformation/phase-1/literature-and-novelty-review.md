# Literature and Novelty Review

## Technical summary

The original project direction is important but over-broad. Three established
results materially constrain its positioning:

1. Context-conditioned token sampling is foundational to several statistical text
   watermarks. KGW recomputes a keyed green list from a token context, while
   SynthID-Text derives watermark scores from recent context and a key.
2. The survival of original n-grams under paraphrase is already an explicit
   explanation for residual watermark detectability. The ICLR 2024 reliability
   paper states that a paraphraser must avoid recycling original n-grams to fully
   remove the signal and evaluates detection as a function of observed length.
3. Broad benchmark novelty is unavailable. Existing work already compares open
   schemes, model/task settings, output quality, attacks, detectors, and watermark
   design choices.

The defensible research question is consequently not whether context matters. It
is whether **exact scheme-native context survival can serve as a quantitatively
useful, calibrated explanatory variable** across attack mechanisms and whether its
incremental value survives comparison with simpler distance measures.

## 1. Foundational mechanisms

Kirchenbauer et al. introduce a keyed green-list watermark that biases sampling
toward a pseudorandom token subset and detects the resulting excess with a
statistical test. Their official implementation supports extended hashing variants
and recommends a moderate context width for the stronger SelfHash setting
([paper](https://proceedings.mlr.press/v202/kirchenbauer23a.html),
[official code](https://github.com/jwkirchenbauer/lm-watermarking)).

The follow-up reliability paper formalizes a context width `h`, recomputes the
green list at each token position, studies human and machine paraphrases, and
states directly that recycled n-grams can preserve watermark evidence. It also
shows why sequence length must be modelled rather than held implicit
([ICLR 2024 paper](https://proceedings.iclr.cc/paper_files/paper/2024/file/d78e9e4316e1714fbb0f20be66f8044c-Paper-Conference.pdf)).

SynthID-Text provides a structurally distinct production-scale comparator. Its
seed generator can depend on recent context and a key, while tournament sampling
embeds multiple watermarking functions. The paper evaluates quality, detection,
edits, and paraphrasing; the released implementations expose `ngram_len`, keys,
and repeated-context handling
([Nature paper](https://www.nature.com/articles/s41586-024-08025-4),
[official repository](https://github.com/google-deepmind/synthid-text),
[Transformers documentation](https://huggingface.co/docs/transformers/internal/generation_utils#transformers.SynthIDTextWatermarkingConfig)).

Kuditipudi et al. provide an important contrast: distortion-free sampling and an
edit-distance-aware detector explicitly target insertions, deletions, and
substitutions. This demonstrates that the relationship between literal local
context survival and detection cannot be assumed to transfer unchanged to aligned
or context-free schemes
([paper](https://arxiv.org/abs/2307.15593)).

## 2. Robustness and attacks

Paraphrase vulnerability and survival are both established. Sadasivan et al.
stress-test watermark, classifier, zero-shot, and retrieval detectors with
recursive paraphrasing; Krishna et al. introduce DIPPER, an 11B paraphraser with
controllable lexical diversity and reordering
([Sadasivan et al.](https://arxiv.org/abs/2303.11156),
[DIPPER paper](https://arxiv.org/abs/2303.13408)). These establish strong attack
baselines, but neither makes the proposed scheme-native predictor comparison the
centre of the study.

Later work raises the adversarial standard. Rastogi and Pruthi show that purported
semantic robustness may weaken when the attacker reverse-engineers a watermark
from limited generations. WaterPark systematizes ten watermarkers and twelve
attacks and studies how design choices affect robustness
([EMNLP 2024](https://aclanthology.org/2024.emnlp-main.1005/),
[Findings of EMNLP 2025](https://aclanthology.org/2025.findings-emnlp.1148/)).
The present project must therefore distinguish ordinary, adaptive, and
key-aware/white-box threat models and cannot equate one paraphrase result with
general robustness.

## 3. Existing benchmarks and tooling

MarkMyWords evaluates watermark quality, detection sample size, and tamper
resistance and supplies an extensible benchmark
([paper](https://arxiv.org/abs/2312.00273),
[repository](https://github.com/wagner-group/MarkMyWords)). WaterBench calibrates
methods to comparable watermark strength before jointly evaluating generation and
detection over varied tasks and output lengths
([ACL 2024](https://aclanthology.org/2024.acl-long.83/)). MarkLLM offers a broad,
actively maintained implementation and evaluation toolkit, including KGW,
SynthID-Text, edit attacks, and paraphrasers
([EMNLP demo paper](https://aclanthology.org/2024.emnlp-demo.7/),
[repository](https://github.com/THU-BPM/MarkLLM)).

These projects are benchmark comparators and engineering accelerators. They also
mean this project cannot claim novelty from assembling several schemes and attacks
alone.

## 4. Detector scope

Watermark detectors verify evidence tied to a particular embedding scheme and
key. Generic AI-text detectors infer whether text resembles a model distribution;
they are not interchangeable provenance tests. DetectGPT uses probability
curvature, Fast-DetectGPT replaces perturbation with conditional sampling, and
Binoculars compares scores from a pair of language models
([DetectGPT](https://proceedings.mlr.press/v202/mitchell23a.html),
[Fast-DetectGPT](https://proceedings.iclr.cc/paper_files/paper/2024/file/6b8c6f846c3575e1d1ad496abea28826-Paper-Conference.pdf),
[Binoculars](https://icml.cc/virtual/2024/poster/33662)). They belong in a secondary
analysis for RQ5, not in the primary watermark validation loop.

## 5. Fairness and decision risk

The 2023 non-native-English study found severe false positives for several generic
detectors on its TOEFL sample. Newer work shows the issue is not uniform across
languages or systems: a 2026 Czech study found no systematic non-native-speaker
bias in its tested setting, while a broader ACL 2026 study found detector-specific
disparities, including elevated classifications for English-language learners
([Patterns 2023](https://doi.org/10.1016/j.patter.2023.100779),
[EACL 2026](https://aclanthology.org/2026.eacl-srw.20/),
[ACL 2026](https://aclanthology.org/2026.acl-long.109/)).

Accordingly, the protocol treats fairness as an empirical subgroup audit. It will
not state that all detectors are biased, nor infer that a calibrated keyed
watermark detector inherits the same failure mode as a generic stylometric
detector.

## 6. Contribution boundary

### Not novel

- Watermark detection weakens after edits or paraphrase.
- Original n-grams may survive paraphrase and carry watermark evidence.
- Detection power depends on text length.
- Watermark families differ in robustness and quality.
- Multi-attack, multi-scheme benchmarking.

### Potentially defensible if demonstrated

- A precise alignment-based definition of **effective seed-context survival** that
  mirrors each scheme's tokenizer, context selection, repeated-context masking,
  and eligible scoring positions.
- A preregistered test of its incremental predictive value over length, edit
  distance, lexical overlap, and semantic similarity.
- Calibration and residual analysis showing when the relationship transfers—and
  where it fails—across context-conditioned, context-free, and edit-aligned
  families.
- Attack efficiency expressed as destroyed effective contexts per unit of
  semantic/factual degradation and computational cost.

### Required language

Until Phase 6 is complete, describe this as a **candidate mechanistic predictor**.
Do not call it a universal law, estimator of a secret production detector, or a
novel discovery that n-grams survive paraphrase.

## 7. Review limitations

This was a targeted, decision-oriented review, not a PRISMA systematic review or
meta-analysis. It prioritized peer-reviewed primary work, official proceedings,
official repositories, and official library documentation through 26 August 2026.
The absence of an identical formulation in the reviewed sources does not prove
global novelty. A venue-specific related-work refresh and citation chaining remain
mandatory immediately before submission.


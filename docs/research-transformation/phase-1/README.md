# Phase 1 — Establish the Thesis

Status: complete for protocol design; empirical claims remain untested  
Review date: 26 August 2026  
Literature scope: targeted review of primary papers, proceedings, official code,
and official framework documentation available by the review date

## Outcome

**Decision: conditional go, with repositioning.**

The broad observation that paraphrases preserve watermark-bearing n-grams is not
novel. It is explicit in Kirchenbauer et al.'s ICLR 2024 reliability study. Broad
cross-scheme attack benchmarking is also occupied by MarkMyWords, WaterBench,
MarkLLM, and WaterPark.

The project will therefore test a narrower contribution:

> Whether an exact, scheme-native measure of surviving watermark-seeding
> contexts provides a calibrated and transferable explanation of post-attack
> detector behavior beyond attacked length, token edit distance, lexical overlap,
> and semantic similarity.

This is a candidate contribution, not yet a novelty claim. It survives Phase 1
because the reviewed work motivates context preservation but does not, in the
sources reviewed, establish the proposed preregistered cross-attack predictive
comparison. Phase 2 must prove that the measure can be implemented exactly from
native scheme logic before the research expands.

## Phase 1 deliverables

- [Literature and novelty review](literature-and-novelty-review.md)
- [Novelty matrix](novelty-matrix.md)
- [Implementation shortlist](implementation-shortlist.md)
- [Research protocol v1](research-protocol-v1.md)
- [Source register](source-register.md)
- [Decision memo](decision-memo.md)
- [Portable technical report](phase-1-report.html)
- [Canonical report artifact](artifact.json)

## Frozen choices for Phase 2

- Primary scheme: KGW SelfHash/minhash family, using the authors' implementation.
- Contrast scheme: SynthID-Text, using the official implementation in
  Transformers or Google DeepMind's reference repository.
- Primary outcome: scheme-native continuous detector score, evaluated with
  empirical null calibration and operating curves.
- Core predictor: aligned, position-level survival of the exact context used to
  seed or score the attacked token.
- Initial attacks: substitution, deletion, insertion, truncation, and one
  controlled paraphraser. Stronger and adaptive attacks enter only after the
  measurement pipeline passes validation.
- Venue class: ACL/EMNLP Findings-quality empirical paper; a main-conference or
  TMLR submission requires broader validation and a stronger general result.

## Phase 2 entry gate

Proceed only if both native implementations can generate keyed positives and
matched unwatermarked controls, reproduce deterministic scores from stored
configurations, pass empirical-null tests, and expose enough tokenizer/context
state to compute the proposed predictor without substituting a proxy.


# Phase 2 empirical-null calibration decision

Decision date: 30 August 2026  
Status: frozen development-pilot design; not a preregistered publication threshold

## Decision

Run a 500-sample empirical-null development pilot on unwatermarked generations,
scoring every output with the two author-canonical variants:
`kgw_author_selfhash_v1` and `synthid_deepmind_hash_v1`.

The pilot uses 48-token outputs from the pinned SmolLM2 checkpoint and a balanced,
deterministic sample across the eight Databricks Dolly instruction categories. It
reports development estimates at 5% and 1% false-positive operating points. It
does not report 0.1% FPR and does not freeze a publication threshold.

The current Transformers tie-inclusive top-k decoder is frozen as part of the
tested end-to-end configuration. An exact-k DeepMind-style decoder is deferred to
a separately labelled sensitivity analysis; it is not required to validate the
canonical SynthID keyed primitive.

## Rationale

Watermark detection is a hypothesis-testing problem, so Type-I error must be
checked on text generated without knowledge of the key. The KGW reliability work
shows that repeated n-grams can invalidate nominal p-values and that excluding
repeats materially improves agreement between theoretical and empirical false
positive rates. The statistical-framework literature likewise treats a pivotal
null statistic and explicit Type-I error control as central design requirements.
Both corrections remain enabled here.

Five hundred samples are adequate to reveal gross centring, variance, tail and
repetition failures. They are not a precise estimate of a 1% tail: only about five
exceedances are expected. The pilot therefore uses Wilson 95% binomial intervals
and is explicitly developmental. The confirmatory target is 5,000 independent
null samples per scheme/configuration for a primary 1% FPR analysis. A primary
0.1% claim would require a separate design of approximately 50,000 null samples
to yield roughly 50 expected tail events.

## Prompt source and sampling

The prompt source is `databricks/databricks-dolly-15k` at revision
`bdd27f4d94b9c1f951818a7da7fd7aeea5dbff1a`. The pinned source file SHA-256 is
`2df9083338b4abd6bceb5635764dab5d833b393b55759dffb0959b6fcbf794ec`.
The dataset is public, English, human-authored, ungated and CC BY-SA 3.0. Prompts
are selected by a frozen hash rank, deduplicated after formatting, capped at 1,024
model-token prompt length, and balanced 62–63 per category. Source row IDs, prompt
hashes, tokenizer revision and category labels are retained.

This balanced mixture is a stress and variance pilot, not an estimate of a real
deployment prompt distribution. Category-specific summaries must accompany the
pooled result.

## Evidence

- Kirchenbauer et al., [On the Reliability of Watermarks for Large Language
  Models](https://arxiv.org/abs/2306.04634).
- Li et al., [A Statistical Framework of Watermarks for Large Language Models:
  Pivot, Detection Efficiency and Optimal Rules](https://arxiv.org/abs/2404.01245).
- Dathathri et al., [Scalable watermarking for identifying large language model
  outputs](https://www.nature.com/articles/s41586-024-08025-4).
- Gillibert et al., [Binomial confidence intervals for rare events](https://arxiv.org/abs/2109.02516).
- Databricks, [databricks-dolly-15k dataset card](https://huggingface.co/datasets/databricks/databricks-dolly-15k).

## Gate after the pilot

The pilot may advance Phase 2 only after trace reconstruction, finite-score,
eligible-position, deterministic-repeat, null-centre, null-variance, upper-tail
and category-heterogeneity diagnostics are reviewed. Pilot thresholds must not be
used to classify the later confirmatory split.

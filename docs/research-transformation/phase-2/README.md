# Phase 2 — Build Watermark Ground Truth

Status: one-shot confirmatory-null gate failed; joint-KGW branch closed; publication preparation active  
Start date: 26 August 2026

## Objective

Build and validate real keyed KGW and SynthID-Text generation/detection before
creating a research corpus. This phase produces validation evidence, not benchmark
claims.

## Implemented foundation

- installable package under `src/ai_watermarks_phase2/`;
- deterministic token attacks with exact provenance maps;
- conservative inferred alignment for later non-deterministic attacks;
- scheme-aware effective-context survival with configurable repeated-context
  masking;
- Transformers-native KGW and SynthID-Text generation/scoring adapters;
- author-canonical KGW and SynthID-Text variants matching the pinned reference
  implementations exactly, selectable per run;
- reconstructable per-token KGW green-hit and SynthID g-value/mask traces;
- exactly ten smoke prompts across five registers;
- committed public-fixture keys and a validation-only configuration;
- unit tests for alignment, attacks, eligibility, context damage, config, variant
  selection, and exact parity against the pinned reference sources.

## Commands

Validate the lightweight core:

```bash
uv sync
uv run pytest
uv run phase2-smoke --dry-run
```

Install the optional ML stack and execute the ten-prompt run:

```bash
uv sync --extra ml
uv run phase2-smoke
```

Generated outputs go to `results/phase2-smoke/` and are ignored by Git until
reviewed. Model downloads use the normal Hugging Face cache and are not committed.

## Interpretation boundary

The smoke run asks whether the pipeline is wired correctly. Ten prompts and a
small model cannot support robustness, quality, fairness, or deployment claims.

## Gate

Phase 2 remains open until the native runs demonstrate reproducibility, sensible
null behavior, repeated-context handling, expected deterministic-attack direction,
and reviewed per-position traces for both schemes.

The ten-prompt native smoke, exact repeat, and automated per-position trace audit
have passed. See the [validation report](validation-report.md). The independent
official-reference [cross-check](reference-crosscheck-report.md) established that
the stock Transformers implementations are distinct keyed variants; canonical
adapters now reproduce both pinned references exactly on detection and step by step
on generation, and every score is labelled with the variant that produced it. One
decoder-level deviation in SynthID top-k tie handling is documented and quantified
rather than closed. Empirical-null calibration and untouched confirmation then
completed under the frozen protocol. The simultaneous 60-cell gate failed in 18
cells, so the full attack corpus and watermarked-positive pilot remain closed and
post-hoc retuning is prohibited. See the
[confirmatory-null gate report](confirmatory-null-gate-report.md).

Replacement-study development subsequently completed a separate fresh positive-
sensitivity screen. The proposed 0.5% design margin failed five canonical KGW
cells, concentrated at 128 tokens. Two targeted fresh KGW generation-bias brackets
then found no candidate that passed both detection and fixed quality guardrails;
bias-only tuning is closed. A formal [KGW feasibility/design decision](kgw-feasibility-design-decision.md)
now approves exactly one bounded, preregistered gamma-by-delta development study,
with a hard stop that closes or re-scopes the 128-token KGW claim if it fails.
That joint protocol was later frozen and authorized. Its development null and
threshold fitting completed, but Stage A was prospectively stopped at 1,935 of
5,200 outputs without score analysis when the project pivoted to publication. The
joint grid has no result and must not be described as failed. See the
[publication pivot](publication-pivot.md), [v2 planning](confirmatory-null-v2-planning.md), the
[KGW bias report](kgw-bias-development-report.md), and the portable
[positive-sensitivity report](../../../reports/phase2-positive-sensitivity/report.html).

Local compute planning is documented in the
[Apple M4 Pro device benchmark](apple-m4-pro-device-benchmark.md). The measured
recommendation is hybrid MPS generation plus CPU scoring, subject to validation in
any future protocol; completed CPU experiments remain unchanged.

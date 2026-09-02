# Phase 2 Smoke Validation Report

Status: smoke and trace-audit gates passed; Phase 2 ground-truth gate remains open  
Run date: 26 August 2026  
Scope: validation only; not a benchmark result

## Executive finding

The native pipeline is functioning for both declared watermark families on the
ten-prompt smoke set. A second complete run reproduced all 30 generation records,
native scores, deterministic attacks, context measurements, and per-position
detector traces exactly.

This result authorizes the next validation increment. It does not authorize a
robustness, quality, fairness, or deployment claim.

## Configuration

| Item | Frozen value |
|---|---|
| Model | `HuggingFaceTB/SmolLM2-135M-Instruct` |
| Model revision | `12fd25f77366fa6b3b4b768ec3050bf629380bac` |
| License | Apache-2.0 |
| Conditions | unwatermarked, KGW SelfHash, SynthID-Text |
| Prompts | 10 across explanation, factual, professional, academic, narrative, and instructional registers |
| Visible output length | 48 tokens |
| Repetitions | one primary run plus one exact reproducibility repeat |
| KGW | green fraction 0.25, bias 2.0, SelfHash, context width 4, public fixture key |
| SynthID-Text | n-gram length 5, depth 9, repeated-context masking, public fixture keys |
| Environment | Python 3.14.6, PyTorch 2.13.0, Transformers 5.16.0, Apple arm64 CPU |
| Source fingerprint | `bf214d21be05052b49e59bc61dcb5212f31a0c6af14cb7c3175fb9e1b474cc45` |

The source tree was dirty because Phase 0–2 work has not yet been committed. The
run therefore records both the repository commit and a SHA-256 fingerprint over
the Phase 2 code, tests, lockfile, configuration, and prompt set.

## Native-score sanity check

These are means over ten smoke prompts and are reported only to validate wiring.
They are not accuracy estimates and have no confidence intervals.

| Scorer | Unwatermarked condition | Intended watermarked condition | Difference |
|---|---:|---:|---:|
| KGW z-score | -0.203 | 3.198 | +3.401 |
| SynthID mean g-value | 0.509 | 0.594 | +0.085 |

The cross-scheme controls did not show the same intended elevation: mean KGW
z-score was -0.380 on SynthID text, and mean SynthID score was 0.504 on KGW text.
This is a useful smoke property, not evidence of statistical independence.

## Deterministic attack response

### KGW-conditioned outputs

| Attack | Mean effective-context survival | Mean KGW z-score |
|---|---:|---:|
| Identity | 1.000 | 3.198 |
| Insert every eighth token | 0.664 | 3.132 |
| Substitute every eighth token | 0.532 | 2.606 |
| Delete every eighth token | 0.532 | 2.395 |
| Truncate to half length | 0.483 | 2.041 |

### SynthID-conditioned outputs

| Attack | Mean effective-context survival | Mean SynthID score |
|---|---:|---:|
| Identity | 1.000 | 0.594 |
| Insert every eighth token | 0.543 | 0.549 |
| Substitute every eighth token | 0.406 | 0.541 |
| Delete every eighth token | 0.406 | 0.541 |
| Truncate to half length | 0.457 | 0.607 |

The SynthID mean statistic is an average rather than an accumulated-evidence
statistic, so truncation is not theoretically required to reduce its mean. Its
uncertainty and threshold behavior must be evaluated on a larger empirical null.

## Executable checks

All checks in `validation/phase2_smoke_checks.py` passed:

- 30 records and balanced conditions;
- exactly 48 generated tokens per record;
- finite native scores and positive eligible counts;
- one ordered trace row per candidate token for every native score;
- exact reconstruction of every base and attacked score from eligible trace rows;
- identity context survival equal to one;
- all declared edits reduce exact context survival;
- intended-scheme smoke separation from the matched control;
- aggregate edit direction for predeclared attacks where the statistic implies a
  direction;
- exact equality of the repeated run and environment manifest.

Thirteen unit tests also pass. The inferred identical-token aligner recovered at
least 99.5% of the exact provenance positions across 100 unique-token synthetic fixtures
for deletion, substitution, and insertion attacks. This does not validate
alignment for natural-language paraphrases with repeated or retokenized spans.

## What passed

- installable, locked Python environment;
- immutable model revision and public-fixture key scope;
- native Transformers KGW and SynthID-Text generation;
- standalone-continuation scoring without private prompt context;
- repeated-context-aware eligible-position measurement;
- deterministic attacks with exact provenance;
- repeatability on the current machine and source fingerprint;
- aggregate native-score and context-survival sanity checks;
- token-level KGW green-hit traces with insufficient-context and repeated-n-gram
  exclusions;
- token-level SynthID g-values with repetition and EOS masks;
- exact aggregate-score reconstruction from all base and attacked traces.

The complete run exports 2,880 base trace rows and 12,960 attacked trace rows.
Automated review verified contiguous token positions, mutually consistent
eligibility/exclusion metadata, eligible counts, and score reconstruction. This
is an internal audit of the Transformers-native implementation; it is not yet an
independent comparison with the watermark authors' repositories.

## What remains open

Phase 2 is not complete. The following gates remain:

1. Cross-check KGW outputs and scores against the authors' official repository.
2. Cross-check SynthID mean/weighted-mean scoring against the DeepMind reference
   implementation.
3. Run at least 500 held-out unwatermarked samples per configuration and compare
   empirical null mean, variance, tails, and repeated-context behavior.
4. Add randomized truncation, replacement, padding, and repeated-context fixtures
   with independently derived expectations.
5. Test reproducibility after a clean commit and on a second environment.
6. Perform a pilot precision/power simulation before selecting the corpus size.

## Gate decision

**Stage 2A smoke gate: pass.**  
**Stage 2B native trace-audit gate: pass.**  
**Overall Phase 2 ground-truth gate: remain open.**

Post-report update: the independent official-reference cross-check was executed
on 27 August 2026. It initially failed exact parity for both implementation
families, and passed after canonical adapters were added the same day. See the
[reference cross-check report](reference-crosscheck-report.md). Gates 1 and 2
below are therefore met for the canonical variants; gates 3 to 6 remain open, so
the overall ground-truth gate stays open and full corpus generation waits on
empirical-null calibration rather than on implementation parity.

The gate list above predates variant labelling. Read gates 1 and 2 as satisfied by
`kgw_author_selfhash_v1` and `synthid_deepmind_hash_v1`; the retained Transformers
variants are separate conditions and are not covered by them.

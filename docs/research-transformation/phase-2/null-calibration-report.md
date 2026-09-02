# Phase 2 empirical-null pilot report

Run date: 30 August 2026  
Status: SynthID centring diagnostic passes; KGW theoretical-null centring fails;
Phase 2 statistical gate remains open

## Decision

Do not change the canonical watermark implementations. Both remain exactly tied
to the pinned author references. Do not pool KGW keys into one null distribution
or use the theoretical standard-normal cutoff as though it were key-invariant.

Proceed with **key-conditional empirical calibration** and make key sensitivity
an explicit experimental factor. The current 500 samples remain a development
pilot and must not define the confirmatory threshold.

## Frozen pilot

- 500 unique, unwatermarked SmolLM2 generations;
- exactly 48 generated tokens each;
- balanced across eight Dolly instruction categories (62–63 each);
- canonical KGW SelfHash and canonical SynthID-Text scoring;
- repeated n-gram/context masking enabled;
- every native score reconstructed from its position trace;
- first ten records reproduced exactly in the independent execution check.

The prompt manifest is `data/phase2-null-calibration-prompts.json` (SHA-256
`fa8f52bb0203548d22ad5f761b2a18470cb04e88eee634b077918a47b055b60a`).

## Primary null findings

| Diagnostic | KGW | SynthID |
|---|---:|---:|
| Samples | 500 | 500 |
| Reference mean | 0.000 | 0.500 |
| Empirical mean | 0.210 | 0.50147 |
| Mean displacement | 4.29 SE | 1.25 SE |
| Sample variance | 1.196 | 0.000693 |
| Eligible-position range | 10–45 | 10–44 |
| Development 5% cutoff | 1.980 | 0.54472 |
| Development 1% cutoff | 3.029 | 0.56061 |

At the in-pilot 1% cutoff, both schemes have 5/500 exceedances. The Wilson 95%
interval is 0.43%–2.32%, demonstrating why this pilot is too small for a precise
publication threshold.

KGW's pooled eligible green-hit rate is 0.2636 rather than the nominal 0.25.
Removing the 44 records with fewer than 40 eligible positions does not remove the
shift: mean z remains 0.189. Category means are positive in every category, so
the result is not explained by one category alone.

SynthID remains close to its 0.5 null reference overall and within category. Its
pilot does not expose the same systematic centring issue.

## KGW key diagnostic

The same 500 frozen token sequences were rescored under five keys without
regeneration. The configured public-fixture key reproduced every stored score
exactly.

| KGW key | Mean z | Variance | Aggregate green rate |
|---:|---:|---:|---:|
| 15485863 | +0.210 | 1.196 | 0.2636 |
| 32452843 | −0.120 | 1.123 | 0.2419 |
| 49979687 | +0.251 | 1.258 | 0.2668 |
| 67867967 | −0.578 | 1.043 | 0.2119 |
| 86028121 | −0.269 | 1.096 | 0.2323 |

The direction and magnitude change by key. This is evidence of a key-conditional
null distribution for this short-text, model and decoder configuration, not an
implementation-parity failure. It is consistent with literature reporting large
performance variance over watermark keys and false-positive distortion from
linguistic repetition or mimicry.

## Root-cause assessment

The immediate numerical source of the configured-key shift is unequal keyed
green assignment among frequent model tokens and contexts. Several frequent
token IDs have empirical green rates far from 0.25. Exact repeated n-grams are
already excluded, but distinct contexts containing the same frequent tokens
remain structured rather than independent uniform draws.

The evidence supports this causal chain:

1. language-model output has highly non-uniform token/context frequencies;
2. a fixed key deterministically maps those contexts and targets to green/red;
3. short outputs sample that structured mapping unevenly;
4. different keys change the direction of the imbalance;
5. the theoretical standard-normal null is therefore not sufficiently
   key-invariant for this tested configuration.

This is an inference from the empirical key diagnostic, not a proof that every
model, length or KGW configuration behaves the same way.

## Required remediation and next gate

1. Retain the author-canonical implementation and no-repeat correction.
2. Freeze a key schedule before confirmatory generation; never select keys based
   on favourable pilot results.
3. Treat key as a configuration/random-effect factor and report key-specific
   null centring, variance and thresholds.
4. Use at least 5,000 independent null texts per primary scheme/configuration for
   the confirmatory 1% operating point.
5. Omit a 0.1% claim unless a separate approximately 50,000-sample null design is
   executed.
6. Add length bands before the confirmatory run, because 48-token calibration
   must not be transferred to 128/256/512-token outcomes.
7. Repeat on a second model family and a second environment before closing the
   overall Phase 2 ground-truth gate.

The next executable task is a frozen multi-key × length variance pilot followed
by simulation-based precision/power analysis. Full attack-corpus generation
remains blocked.

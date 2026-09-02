# Implementation Shortlist

> Superseded in part by Phase 2. This document names the Transformers
> implementations as primary. Phase 2 found they are not token-level compatible
> with the authors' reference code and split each family into a canonical and a
> secondary variant; the canonical pair is now primary. The SynthID sampling table
> seed and size recorded below are inert under the canonical variant. See
> [phase-2/reference-crosscheck-report.md](../phase-2/reference-crosscheck-report.md).


## Decision

Use native implementations first. Use MarkLLM as an integration comparator and
engineering reference, not as the sole source of truth for either scheme.

| Priority | Component | Selected implementation | Why selected | Phase 2 acceptance test |
|---:|---|---|---|---|
| 1 | KGW family | [Authors' `lm-watermarking`](https://github.com/jwkirchenbauer/lm-watermarking) | Official implementation; supports SelfHash/minhash variants, native detector, repeated n-gram controls | Reproduce fixed-seed tokens and detector scores; empirical null; no-repeat correction; exact context trace |
| 2 | SynthID-Text | [Transformers implementation](https://huggingface.co/docs/transformers/internal/generation_utils#transformers.SynthIDTextWatermarkingConfig), checked against [DeepMind reference code](https://github.com/google-deepmind/synthid-text) | Official/open, structurally distinct tournament sampler; exposes n-gram length and repeated-context state | Reproduce fixed configuration; compare mean/weighted-mean score behavior; verify context-history masking |
| 3 | Integration cross-check | [MarkLLM](https://github.com/THU-BPM/MarkLLM) | Unified APIs and several attacks; actively maintained | Scores agree with native implementation on a frozen fixture or discrepancy is documented |
| Hold | Edit-aligned watermark | [Kuditipudi et al.](https://arxiv.org/abs/2307.15593) via MarkLLM/MarkMyWords | Useful negative-boundary family, but adds alignment and runtime complexity | Add only after two primary schemes pass and predictor definition is generalized prospectively |
| Hold | Semantic watermark | SIR/SemaMark-class open implementation | Tests semantic-context boundary, but reverse-engineering and model dependencies complicate attribution | Add in extension study, not minimum viable experiment |

## Frozen KGW configuration envelope

- Scheme family: SelfHash with minhash-style context selection.
- Primary context width: `h = 4`, following the official authors' implementation
  guidance; include `h = 1` and one larger width as ablations.
- Primary green-list fraction and bias: begin from official baseline guidance
  (`gamma = 0.25`, `delta = 2.0`) and calibrate a lower-bias setting.
- Detector: native full-sequence statistic plus WinMax where mixed/cropped text is
  evaluated.
- Repeated contexts: score both native corrected behavior and a diagnostic raw
  variant; only corrected behavior is confirmatory.

These values are implementation starting points, not performance claims.

## Frozen SynthID-Text configuration envelope

- Use the official configuration object and record all keys, `ngram_len`, sampling
  table seed/size, context history size, tokenizer, Transformers commit/version,
  and model revision.
- Begin with `ngram_len = 5`, matching the official documentation example, then
  add one shorter context ablation.
- Use mean or weighted-mean scoring for the minimum study. A Bayesian detector is
  optional because it requires representative, key-specific training data and
  creates a second calibration problem.
- Respect repeated-context masking in both detection and the proposed survival
  measure.

## Attacks

### Tier A: deterministic validation attacks

- token substitution at fixed rates;
- token deletion at fixed rates;
- token insertion from matched unwatermarked text;
- prefix/suffix truncation;
- contiguous span replacement;
- copy-paste dilution.

These attacks isolate mechanism and make expected context destruction calculable.

### Tier B: semantic attacks

- DIPPER if hardware permits, otherwise a documented open paraphraser with frozen
  weights and controllable settings;
- one instruction-tuned open model with frozen prompt and decoding configuration;
- round-trip translation only after language/pivot quality checks.

### Tier C: adaptive attacks

- watermark-aware reverse engineering or score-guided editing;
- mixed attacks.

Tier C is a separate threat model and is excluded from the minimum Phase 2 build.

## Detector baselines

Primary results use scheme-native detectors. The generic suite is secondary:

- [Fast-DetectGPT](https://github.com/baoguangsheng/fast-detect-gpt);
- [Binoculars](https://github.com/ahans30/Binoculars);
- one frozen supervised detector with a public model card, training-data scope,
  and reproducible threshold;
- raw log-likelihood/perplexity as a historical baseline only.

Do not call a generic score a watermark score, and do not use a commercial API as
the only reproducible baseline.

## Environment and provenance requirements

Every run must store:

- repository URL and immutable commit;
- model and tokenizer identifiers plus revisions and licenses;
- watermark key/configuration in protected experiment metadata;
- prompt ID, seed, decoding parameters, device, precision, and library versions;
- original output, attacked output, token IDs, alignment map, eligible positions,
  per-token native score, and detector result;
- attack implementation/version, strength, prompt, runtime, and cost;
- content hashes and a machine-readable run manifest.

Secrets must never be committed. Release research keys only for explicitly public
benchmark fixtures.


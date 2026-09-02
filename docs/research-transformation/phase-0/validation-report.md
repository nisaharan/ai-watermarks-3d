# Phase 0 Validation Report

## Overall assessment: Needs revision

### Question evaluated

Are the repository's current methods, calculations, figures, and conclusions
trustworthy enough to support externally shareable findings about AI-text
watermark detection and removal?

### Evidence reviewed

- `README.md` and `AI-Watermarks-3D.md`.
- Three public-article variants under `article/`.
- Six analysis and figure-generation scripts.
- The human, AI, and rewrite texts under `example/`.
- `example/profiles.json` and `example/removal/analysis.json`.
- The vendored Unicode-removal implementation and attribution files.
- All twelve rendered GIFs and the two supplied stills.
- The existing `Context-Survival.pdf` critique.

The audit is based on repository state available on 26 August 2026. External
literature and vendor claims are not revalidated in Phase 0; that is Phase 1.

## What is reliable enough to retain

1. **Channel and tier taxonomy.** Separating keyed statistical watermarks, file
   provenance, generic statistical heuristics, and surface tells is conceptually
   useful when vendor-specific claims are carefully scoped.
2. **Epistemic labels.** Labelling figures as measured, modelled, simulated, or
   counted is a strong practice, although several captions currently overrun their
   own labels.
3. **Descriptive measurements.** Sentence lengths, paragraph shapes, regex hits,
   and GPT-2 surprisal are reproducible observations about the supplied samples.
4. **Layer A result.** The vendored Unicode pass produces byte-identical content for
   the supplied AI sample. This supports only the narrow claim that this pass found
   no removable carrier in that sample.
5. **Analytical separation.** Watermark evasion, generic detector response, output
   quality, and apparent human style should be evaluated as separate outcomes.
6. **Research hypothesis.** The intuition that a context-keyed scheme depends on
   survival of its seeding context is mechanistically plausible and testable.

## Issues found

### 1. Critical: the object of study is absent

`example/ai_generated.txt` has no documented generating model, watermark key,
green-list assignment, watermark parameters, or native detector result. The removal
analysis therefore cannot observe whether a watermark survives.

**Impact:** every `modelled_z`, “still caught,” and “evaded” statement is a
hypothetical projection, not an experimental watermark result.

### 2. Critical: the current estimator has the wrong padding behaviour

`analyse_removal.modelled_z` applies the inferred marked-token rate to every token
in the candidate. Because `bigram_survival` remains 1.0 when unrelated text is
appended, the score grows with the square root of candidate length.

Reproduced from repository code:

| Candidate | Tokens | Current `modelled_z` |
|---|---:|---:|
| Original AI sample | 336 | 8.07 |
| Plus 30 filler sentences | 456 | 9.40 |
| Plus 90 filler sentences | 696 | 11.61 |

Under the same hypothetical assumptions, the excess evidence is carried by a fixed
number of surviving original contexts while the null variance grows with candidate
length. The corresponding length-corrected projection decreases from 8.04 to 6.90
and then 5.59.

**Impact:** the formula can reverse the effect of insertion attacks and makes verdicts
near the threshold unreliable.

### 3. Critical: overlap is not keyed watermark evidence

The unrelated human comparison receives `modelled_z = 1.53` because its shared
topic creates 18.36% set-based bigram overlap with the AI reference. Phrases such as
“Sydney Opera House” contribute even though no watermark is present.

**Impact:** the proxy contains topic and chance-overlap terms and does not have the
claimed detector null distribution.

### 4. High: sample size does not support class-level findings

The study uses one human text, one AI text, and one output for each rewrite mode.
There is no within-condition variance, confidence interval, or defensible basis for
claims that rhythm separates human and AI writing or that one attack family is
generally weakest.

**Impact:** the measurements can be presented only as a worked example.

### 5. High: circular simulated-versus-measured comparison

The 3.4-bit “textbook” gap comes from the project's own illustrative parameters,
not a cited empirical textbook distribution. Comparing the observed 0.54-bit gap
against that value cannot support a finding that the textbook picture oversells the
signal.

### 6. High: attack generation is confounded and incompletely reproducible

The rewrite author knew the evaluation metrics. The generating and rewriting model,
revision, decoding settings, seeds, timestamps, and complete run records are not
available.

**Impact:** attack rankings and convergence claims cannot be independently reproduced
or interpreted as unbiased.

### 7. High: no real generic detector baseline is run

The project measures GPT-2 Large surprisal and writing-style features but describes
them as the measurements public detectors use. No DetectGPT-family, Binoculars,
supervised, or commercial detector is evaluated.

**Impact:** “more human than the human” is true only relative to selected one-sided
heuristics, not to a validated detector suite.

### 8. High: the Tier 3 instrument changes meaning under paraphrase

The scanner consists of regexes for named English phrasings. Backtranslation changes
“widely regarded” to “generally considered,” removing the hit without necessarily
removing the habit.

**Impact:** lower counts after rewriting may reflect lexical substitution rather than
less AI-like rhetoric.

### 9. Medium: inconsistent tokenization changes reported metrics

`measure_texts.py` and `analyse_removal.py` tokenize differently.

| Sample | Profile words | Removal words | Profile TTR | Removal TTR |
|---|---:|---:|---:|---:|
| Human | 345 | 346 | 0.548 | 0.535 |
| AI | 333 | 334 | 0.574 | 0.574 |

The README uses the profile TTR values, while the removal analysis uses the second
definition. Neither is inherently the one correct word tokenizer, but the metric name
is presented without the definition change.

### 10. Medium: “same length” is imprecise

The source texts contain 346 and 334 whitespace-delimited words and 2,206 and 2,086
characters after trailing whitespace is removed. They are approximately length
matched, not identical in length.

### 11. Medium: evidence labels and narrative verdicts conflict

GIF 11 is labelled `MODELLED`, yet it says “still detected,” “below threshold,” and
“two ... are still caught.” Similar wording appears in the README, main document,
and articles. The caveat does not neutralize the verdict.

### 12. Medium: provenance is incomplete

The human Wikipedia excerpt is attributed, but the AI sample and Layer B outputs do
not contain a complete generation manifest. Some literature entries are URLs or
reading notes rather than a publication-grade bibliography.

## Calculation spot-checks

- Layer A byte identity: **verified** for the stored AI and Layer A files.
- Sentence and paragraph measurements: **verified as sample descriptions**.
- GPT-2 mean surprisal values: **consistent across stored profiles and removal
  analysis**, but not rerun because model weights are not part of the repository.
- `modelled_z` arithmetic: **verified as implemented; methodology invalid for
  detector verdicts**.
- Padding response: **discrepancy found**; current score rises rather than falls.
- Human null comparison: **discrepancy found**; topic overlap produces positive
  projected evidence.
- TTR consistency: **discrepancy found** because of different tokenization.
- Facts-retained percentage: **not validated as factual preservation**; it is a
  crude presence test over automatically selected numbers and capitalized words.

## Visualization review

The figures are polished and unusually explicit about provenance. However:

- 3D presentation is sometimes used for one-dimensional or two-dimensional data;
- uncertainty and sample size are missing from result-oriented visuals;
- several titles and takeaways generalize from a single pair;
- red/green threshold semantics make modelled projections look like observations;
- simulated ranges need direct source support or must be labelled author-selected;
- accessible static alternatives and color-independent encodings are incomplete.

## Required corrections before external research use

1. Remove or quarantine all current detector verdicts.
2. Describe existing measurements only as observations about the supplied samples.
3. Replace the `modelled_z` result with a clearly named exploratory projection or
   retire it from public results.
4. Standardize metric definitions and tokenization.
5. Add complete provenance manifests for generation and rewriting.
6. Implement and validate real keyed watermark generation before Phase 3.
7. Run literature and novelty verification before claiming contribution.

## Required caveat for the current version

> This repository is an exploratory visual demonstration using one human and one AI
> sample. No keyed watermark was applied or detected. Its bigram-survival scores are
> hypothetical projections and must not be interpreted as evidence that an attack
> did or did not evade a real watermark detector.

## Confidence assessment

- **High confidence** in the identified formula, sample-size, provenance, and
  claim-alignment problems because they are directly observable in repository code
  and data.
- **Moderate confidence** in the proposed research novelty until Phase 1 verifies the
  current literature.
- **No confidence assigned** to real-world attack rankings or detector performance;
  the present design cannot estimate them.

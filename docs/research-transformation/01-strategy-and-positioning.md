# Strategy and Positioning

## 1. Strategic objective

Elevate the project into a credible research and thought-leadership asset that
connects watermarking theory, empirical attack evaluation, reproducible software,
and practical guidance for decision-makers.

The project should be valuable to four audiences:

| Audience | Primary need | Project response |
|---|---|---|
| Researchers | A novel, falsifiable contribution | Test context survival against measured watermark detection. |
| Engineers | Reproducible implementations and benchmarks | Release keyed generation, attacks, detectors, configurations, and tests. |
| AI leaders and policymakers | Clear implications and limitations | Separate provenance, authorship inference, evasion, and quality. |
| General readers | An accurate mental model | Retain the strongest visual explanations with disciplined evidence labels. |

## 2. Proposed research contribution

### Primary contribution

Introduce and evaluate **context survival** as a mechanistic predictor of
post-attack detectability for context-dependent text watermarks.

The paper should test whether measured detection scores can be explained by:

- the number of surviving watermark-seeding contexts;
- attacked-text length;
- the watermark scheme's context width and detection rule.

It should compare this explanation against common surface measures such as edit
distance, lexical overlap, BLEU-like measures, and semantic similarity.

### Supporting contributions

- A common attack-cost framework balancing evasion, semantic preservation,
  factual retention, readability, and computational cost.
- An empirical separation of watermark evasion from apparent human authorship.
- A reproducible attack benchmark spanning multiple registers, model families,
  text lengths, and watermark schemes.
- A transparent standard for labelling measured, modelled, simulated, and
  illustrative evidence.

## 3. Positioning statement

Preferred:

> We evaluate whether survival of watermark-seeding contexts provides a
> mechanistic and better-calibrated predictor of post-attack detectability than
> generic lexical or semantic change.

Avoid:

> We proved that watermark removers do not work.

The second framing is overly broad, treats all watermark schemes as equivalent,
and is not supported by the current evidence.

## 4. Scope boundaries

### In scope

- Text-generation watermarks with open or reproducible detection procedures.
- Automated transformation attacks and controlled mixed attacks.
- Detection robustness, output quality, and subgroup performance.
- Academic, engineering, governance, and communication outputs.

### Out of scope for the primary study

- Claims about undisclosed vendor watermark implementations.
- Inferring who authored a document from a watermark result.
- Image, audio, or video watermarking.
- Building tools whose primary purpose is covert misuse or evasion.
- Treating surface AI-writing habits as cryptographic evidence.

## 5. Measures of strategic success

- The contribution is distinguishable from established paraphrase-attack results.
- The central hypothesis has a predefined failure condition.
- Independent users can reproduce a small experiment from documented commands.
- A reviewer can trace every reported number to data, configuration, and code.
- The benchmark and package remain useful even if the hypothesis is refuted.
- Public communications preserve the limitations of the technical result.

## 6. Recommended product hierarchy

1. **Research core:** data, watermarking, attacks, detectors, analysis, and tests.
2. **Research paper:** primary scholarly argument and evidence.
3. **Benchmark/package:** reusable contribution for other researchers.
4. **Executive brief:** implications for provenance and organizational policy.
5. **Public explainer:** accurate visual narrative for a broad audience.

The current GIFs and articles should be treated as communication assets, not as
the evidentiary foundation of the study.

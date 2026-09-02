# Proposed Research Protocol

Status: draft for review; not preregistered

## 1. Research questions

### RQ1

How accurately do surviving watermark-seeding contexts and attacked-text length
predict measured post-attack watermark detection?

### RQ2

Does context survival explain detection better than lexical distance, edit
distance, or semantic similarity?

### RQ3

At equal semantic and factual quality, which attack families destroy the most
watermark-bearing context?

### RQ4

How stable is the context-survival relationship across watermark schemes, base
models, decoding settings, text lengths, topics, and registers?

### RQ5

How independent are watermark detection, generic AI-text detection, and perceived
human authorship?

## 2. Hypotheses

- **H1:** Surviving context count and candidate length predict measured
  post-attack detection with useful calibration.
- **H2:** Lexical and semantic distance add limited explanatory power once context
  survival and length are known.
- **H3:** Attack families differ materially in context destruction at equal
  semantic-preservation levels.
- **H4:** The relationship varies across watermark families and will not transfer
  unchanged to schemes that do not use equivalent context seeding.
- **H5:** Watermark evasion and generic AI-text appearance are empirically distinct
  outcomes.

Each hypothesis must be accepted, narrowed, or rejected using criteria fixed
before the final evaluation split is opened.

## 3. Experimental factors

### Watermark conditions

- Unwatermarked generation control.
- KGW-style keyed watermarking.
- SynthID-Text or another structurally distinct open implementation.
- More schemes may be added only after the first two pass validation.

### Generation conditions

- At least three model families where licensing and compute allow.
- At least two decoding temperatures.
- Identical prompts and decoding settings within matched comparisons.
- Several predeclared length bands.

### Registers

- Encyclopedic.
- News/reporting.
- Academic abstract.
- Explanatory or forum-style writing.
- Professional workplace communication, if a suitable licensed corpus exists.

### Human controls

- Topic-, register-, and length-matched human text.
- A non-native-English subset from a suitable licensed learner corpus.
- Documented provenance and exclusion criteria.

### Initial scale

Target at least 300 prompt-matched items per major condition. A formal power or
precision analysis should determine the final number before generation begins.

## 4. Attack families

- Unicode and metadata stripping as negative controls.
- Token substitution.
- Controlled paraphrasing at multiple strengths.
- DIPPER or a justified equivalent benchmark.
- Round-trip translation through several pivot languages.
- Sentence restructuring.
- Outline-and-regenerate.
- Truncation.
- Insertion and padding.
- Predeclared mixed attacks.

All attacks must be automated, seeded, versioned, and blinded to evaluation code.

## 5. Measurements

### Watermark outcomes

- Scheme-native detection statistic.
- AUROC.
- TPR at 1% and 5% FPR.
- Calibration by length and experimental subgroup.
- Detection degradation relative to the matched unattacked output.

### Context outcomes

- Surviving context count using the scheme's tokenizer.
- Context-survival rate at the scheme's actual context width.
- Candidate length.
- Context destruction per unit of attack cost.

### Output-quality outcomes

- Bidirectional entailment or another semantic-preservation measure.
- Factual retention and contradiction rate.
- Readability and grammatical quality.
- Lexical and structural change.
- Reference-free quality score.
- Stratified human review with a documented rubric.

### Baseline detection outcomes

- Fast-DetectGPT or a current equivalent.
- Binoculars or a current equivalent.
- A representative supervised detector.
- Raw perplexity retained only as a historical baseline.

## 6. Statistical analysis

- Use paired comparisons wherever prompts and source outputs are matched.
- Report effect sizes and bootstrap confidence intervals.
- Correct for multiple comparisons across attack families and subgroups.
- Report operating curves rather than relying on one binary threshold.
- Fit detection against context survival and length, then add lexical and semantic
  predictors in predeclared ablations.
- Report fit, calibration, uncertainty, and residuals by attack family and scheme.
- Perform sensitivity analyses for tokenizer, context width, length, register,
  decoding temperature, and quality threshold.

## 7. Validity tests required before main experiments

1. Unwatermarked detector scores are approximately centred at the theoretical null.
2. Null variance matches the expected distribution over at least 500 samples.
3. Appending chance-rate text weakens the detection statistic as theory predicts.
4. Truncation and replacement tests match independently derived expectations.
5. Generation and scoring repeat exactly from stored seeds and configurations.
6. No corpus leakage or near-duplicate contamination is present across splits.

Failure of any test blocks downstream result generation.

## 8. Reporting commitments

- Report negative and null results.
- Distinguish confirmatory from exploratory analyses.
- Identify all deviations from the frozen protocol.
- Report sample sizes, exclusions, uncertainty, compute, and model versions.
- Do not generalize a result beyond the watermark schemes actually tested.

# Research Protocol v1

Status: preregistration-ready draft; freeze after Phase 2 pilot and before opening
the confirmatory evaluation split

## 1. Contribution and scope

This study tests a candidate explanatory measure for **known, keyed, open text
watermarks**. It does not infer whether arbitrary text was written by AI, reverse
engineer vendor systems, prove authorship, or adjudicate misconduct.

The confirmatory contribution is the incremental and out-of-cell predictive value
of effective seed-context survival. Broad robustness comparisons, generic detector
results, and educational visualizations are supporting outputs.

## 2. Research questions

### RQ1 — explanatory validity

How much post-attack native detector behavior is explained by attacked length and
effective seed-context survival?

### RQ2 — incremental validity

Does effective seed-context survival improve held-out prediction beyond token edit
rate, lexical overlap, semantic similarity, and attacked length?

### RQ3 — boundary conditions

How do coefficients, calibration, and residuals vary across scheme, context width,
attack family, model, decoding entropy, length, task, and repeated-context policy?

### RQ4 — attack efficiency

At comparable semantic and factual quality, which attacks destroy the most
effective contexts per unit of compute and content degradation?

### RQ5 — signal independence

How strongly are keyed watermark outcomes associated with generic AI-text detector
scores before and after attack?

## 3. Estimands and definitions

Let the original token sequence be `x`, attacked sequence be `y`, and a monotonic
alignment map `a(j)` map attacked token position `j` to an original position or
null. For scheme `s`, let `C_s(i)` be the exact ordered or selected context that
the native scheme uses to score original position `i`; let `E_s(y, j)` indicate
that position `j` is eligible under the native detector's masking and repeated-
context rules.

An attacked position is an **effective surviving context** when:

1. `a(j)` is non-null;
2. the attacked token at `j` is aligned to the same original token identity;
3. the context reconstructed from aligned attacked predecessors is exactly equal
   to `C_s(a(j))` under the scheme's tokenizer and context-selection rule; and
4. `E_s(y, j) = 1`.

Define:

- `N_eff`: number of effective surviving scored positions;
- `R_eff = N_eff / N_eligible_original`: effective survival rate;
- `T_eff`: number of eligible attacked positions;
- `D_native`: continuous native detector statistic;
- `Y_tau`: detection at a threshold calibrated on held-out null text to target a
  specified false-positive rate.

For context-free schemes, `R_eff` is not forced into this definition. A separate
token-identity or alignment exposure measure must be declared before that scheme
is added.

## 4. Confirmatory hypotheses and falsification

### H1

Adding `N_eff` and its predeclared interaction with attacked length improves
held-out predictive performance for `D_native` over a length-only model.

**Falsified if:** median improvement in out-of-cell `R²` is less than 0.02 and the
95% bootstrap interval includes zero for both primary schemes.

### H2

The context model improves prediction beyond length, token edit rate, lexical
overlap, and semantic similarity.

**Falsified if:** the full context model fails to improve held-out log score by at
least 1% relative to the best non-context baseline, with a paired 95% bootstrap
interval above zero required for support.

### H3

The sign of the `N_eff` association is positive within both primary schemes, but
its magnitude is scheme- and attack-dependent.

**Falsified if:** either primary scheme has a non-positive pooled association or
the apparent relationship vanishes after attack-family blocking.

### H4

Quality-matched attack rankings by effective-context destruction differ from
rankings by token edit distance alone.

**Falsified if:** rankings are effectively identical (`Spearman rho >= 0.9`) and
do not identify materially different Pareto-efficient attacks.

### H5

Generic detector scores and native watermark scores are not interchangeable.

**Supported if:** their error sets and attack responses materially diverge under
predeclared joint analyses. This hypothesis is descriptive and secondary.

Thresholds are design commitments, not statements that smaller effects are
scientifically impossible. All effect sizes and intervals will be reported.

## 5. Experimental design

### Minimum viable confirmatory design

- 2 schemes: KGW SelfHash/minhash and SynthID-Text;
- 2 open model families, with one instruction-tuned checkpoint per family;
- 2 decoding temperatures chosen to produce meaningfully different entropy;
- 3 output-length bands: approximately 128, 256, and 512 scheme tokens;
- 3 task/register groups: open-ended explanation, constrained factual response,
  and summarization;
- 5 independent generation seeds per prompt-condition cell;
- at least 100 prompt families per task group in the confirmatory split.

The final sample count is determined after a Phase 2 variance pilot using
simulation-based power/precision analysis. Prompts, not individual attack variants,
are the unit used for split isolation and clustered uncertainty.

### Controls

- matched unwatermarked generations with identical model/decoding settings;
- human text matched by task, topic, and length for false-positive and generic
  detector evaluation;
- negative-control transformations that alter file metadata or Unicode formatting
  without changing native tokens where applicable;
- sham attacks that execute the pipeline but return identical text.

## 6. Attack matrix

Confirmatory attacks include deterministic substitution, deletion, insertion,
truncation, span replacement, copy-paste dilution, and one frozen open
paraphraser. Each has at least three intensity levels plus an unattacked level.

Semantic attacks are quality-matched after attack. Comparisons are made within
predeclared semantic-preservation and factual-consistency bands rather than at raw
prompt labels alone. Adaptive and key-aware attacks are exploratory unless a
separate protocol amendment freezes them before evaluation.

## 7. Outcomes and covariates

### Primary outcomes

- native continuous detector statistic;
- empirical p-value or calibrated score where the implementation supports it;
- TPR at empirical FPR targets of 1% and 0.1%;
- AUROC with prompt-clustered confidence intervals.

The 0.1% point is reported only when the held-out null sample is large enough to
estimate it responsibly. Otherwise it is labelled underpowered and omitted from
claims.

### Predictors

- `N_eff`, `R_eff`, and `T_eff`;
- attacked token length;
- token Levenshtein edit rate;
- unigram and scheme-context-length n-gram overlap;
- semantic similarity;
- attack family/intensity, model, task, temperature, scheme, and context width;
- original detector strength and original generation entropy.

### Quality and cost guardrails

- bidirectional entailment and contradiction;
- answer/fact retention on tasks with references;
- instruction fulfilment;
- grammar/readability and a blinded human subset;
- attack latency, accelerator time, model calls, and estimated energy/cost where
  feasible.

No single LLM judge is treated as ground truth. Judge prompts, versions, ordering,
and agreement with human review are recorded.

## 8. Statistical analysis

1. Calibrate thresholds independently for every scheme/configuration on held-out
   null text; never tune on attacked positives.
2. Fit a length-only baseline, a conventional-distance baseline, the context
   model, and a full combined model.
3. Use hierarchical regression with prompt-level random intercepts and fixed
   effects/interactions declared above. Use an appropriate bounded or transformed
   link if the detector statistic requires it.
4. Evaluate prediction by leaving out complete attack × model cells, not random
   rows, to test transport rather than memorization.
5. Report `R²`/deviance explained, held-out log score or RMSE, calibration slope
   and intercept, and residuals by scheme and attack.
6. Bootstrap by prompt family. Control the false discovery rate for secondary
   subgroup contrasts.
7. Treat cross-scheme coefficient pooling as an empirical question; publish
   scheme-specific estimates even if the pooled model looks strong.

## 9. Validation gates

Phase 2 blocks confirmatory data generation until all tests pass:

1. fixed seeds reproduce token IDs and scores;
2. native and independently recomputed eligible positions agree exactly;
3. unwatermarked scores match empirical null expectations;
4. repeated-context masking and no-repeat corrections behave as documented;
5. padding, truncation, insertion, and replacement move detector statistics in
   the theoretically expected direction over repeated samples;
6. alignment recovers known synthetic edits with at least 99.5% position accuracy;
7. content hashes and manifests reproduce every fixture;
8. no prompt family crosses development and confirmatory splits.

## 10. Fairness, ethics, and interpretation

Generic detectors receive a subgroup audit across English-language learner status
and available demographic/register strata. Results are reported per detector and
corpus because recent evidence is heterogeneous. Keyed watermark false positives
are also tested by subgroup, but the two detector classes are not conflated.

No detector result is evidence of plagiarism, intent, or sole authorship. Public
materials will state that a positive keyed result supports only the presence of a
scheme-consistent signal under the tested configuration and threshold.

Human review requires ethics approval or a documented exemption, consent,
appropriate compensation, and exclusion of disciplinary use.

## 11. Reporting and change control

- Freeze code commit, protocol, analysis plan, model revisions, keys/configs, and
  data splits before opening confirmatory results.
- Log every deviation and label added analyses exploratory.
- Report all exclusions, failed runs, null results, and negative findings.
- Release aggregate results and public-key fixtures where licensing and threat
  modelling permit; do not release operational secret keys.
- Refresh the related-work search immediately before submission.


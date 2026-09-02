# Roadmap and Decision Gates

## Overview

The phases are sequential because each gate establishes the validity of the work
that follows. Calendar estimates assume part-time research and will vary with
compute, licensing, and review availability.

| Phase | Indicative timing | Outcome |
|---|---:|---|
| 0. Reframe and stabilize | Weeks 1-2 | Claims, mathematics, scope, and project baseline are controlled. |
| 1. Establish the thesis | Weeks 2-4 | Novelty and falsifiable hypotheses are documented. |
| 2. Build watermark ground truth | Weeks 4-7 | Real keyed watermark generation and validated detection work. |
| 3. Construct the corpus | Weeks 6-10 | A licensed, matched, multi-register corpus with variance exists. |
| 4. Automate the attacks | Weeks 9-13 | Reproducible attacks are comparable on a common cost axis. |
| 5. Build evaluation | Weeks 12-16 | Watermark, detector, quality, and statistical evaluation are integrated. |
| 6. Test the thesis | Weeks 16-19 | Main results, ablations, and failure analysis are complete. |
| 7. Professionalize the repository | Weeks 4-20 | The codebase and release process meet research-software standards. |
| 8. Publish and communicate | Weeks 19-24 | Paper, benchmark, brief, visuals, and public narrative are aligned. |

## Phase 0: Reframe and stabilize

### Work

- Preserve the current project as an exploratory baseline.
- Inventory claims across documentation, articles, figures, and code.
- Correct the estimator specification and remove unsupported verdict language.
- Establish research, ethical, and communication boundaries.

### Gate

Every prominent claim has an evidence classification and an owner. Invalid or
unsupported claims are marked for correction before further publication.

## Phase 1: Establish the thesis

### Work

- Complete the focused literature review.
- Produce the novelty matrix.
- Freeze research questions, hypotheses, metrics, and falsification criteria.
- Choose the target venue class and benchmark comparators.

### Gate

The proposed contribution is not merely a repetition of established paraphrase
robustness findings.

## Phase 2: Build watermark ground truth

### Work

- Implement two open watermark schemes.
- Generate keyed watermarked and matched unwatermarked controls.
- Implement native detectors and formal sanity tests.
- Replace hypothetical detection verdicts with measurements.

### Gate

Null, padding, truncation, and reproducibility tests all pass. No downstream result
is accepted until they do.

## Phase 3: Construct the corpus

### Work

- Finalize sources, licenses, registers, models, temperatures, and length bands.
- Conduct power or precision analysis.
- Generate and validate the corpus.
- Freeze splits and publish a dataset card.

### Gate

Length, topic, register, and provenance are documented and acceptably balanced.

## Phase 4: Automate attacks

### Work

- Implement the predeclared attack families and strengths.
- Freeze attacker models, prompts, versions, and seeds.
- Measure semantic, factual, structural, and computational costs.

### Gate

Every attack is reproducible, blinded to evaluation code, and comparable at a
defined quality level.

## Phase 5: Build evaluation

### Work

- Integrate watermark detectors and generic AI-text detector baselines.
- Add quality, factuality, fairness, and subgroup evaluation.
- Implement confidence intervals and operating curves.

### Gate

The evaluation suite passes validation and generates a complete machine-readable
result table without manual editing.

## Phase 6: Test the thesis

### Work

- Fit the predeclared models.
- Run the context, lexical, semantic, and combined ablations.
- Examine calibration and residuals by attack and scheme.
- Complete sensitivity and subgroup analyses.

### Gate

Each hypothesis is reported as supported, qualified, or refuted using the frozen
criteria. Unexpected analyses are explicitly labelled exploratory.

## Phase 7: Professionalize the repository

### Work

- Package the code and standardize configurations.
- Add tests, CI, type checking, documentation, and release automation.
- Create a reproducible lightweight demonstration.

### Gate

An independent user can reproduce a representative result without undocumented
manual steps.

## Phase 8: Publish and communicate

### Work

- Draft and internally review the paper.
- Release the benchmark and package with documentation.
- Rebuild figures from final validated results.
- Produce the executive brief, public explainer, and presentation materials.

### Gate

The paper, repository, brief, and public narrative make consistent claims and link
to the same versioned evidence.

## Stop/go review points

1. **After Phase 1:** stop or reposition if novelty is not defensible.
2. **After Phase 2:** stop empirical expansion if ground-truth validation fails.
3. **After Phase 3:** redesign if corpus confounds cannot be controlled.
4. **After Phase 5:** delay analysis if detector or metric validity is inadequate.
5. **After Phase 6:** publish the result honestly even if the hypothesis is refuted.

## Resourcing decisions

Before implementation, document:

- project lead and statistical reviewer;
- engineering and data responsibilities;
- available GPU and storage budget;
- human-evaluation capacity;
- legal or ethics review requirements;
- publication and release owner.

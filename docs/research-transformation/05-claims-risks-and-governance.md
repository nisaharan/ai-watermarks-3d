# Claims, Risks, and Governance

## 1. Evidence classification

Every claim and figure should carry one of these labels:

| Label | Meaning |
|---|---|
| Measured | Directly produced by the validated experimental pipeline. |
| Derived | Calculated from measured values using a documented formula. |
| Modelled | Produced by a stated model and not directly observed. |
| Simulated | Generated from assumed parameters to test or illustrate behaviour. |
| Counted | Deterministic arithmetic over disclosed source material. |
| Illustrative | Designed only to teach a concept; not empirical evidence. |
| Literature | Supported by an explicitly cited external source. |

Labels describe provenance, not evidential quality. A measured result can still be
poorly designed, and a literature claim can still be contested.

## 2. Claim register template

| ID | Claim | Location | Evidence label | Source/result ID | Scope | Status | Owner |
|---|---|---|---|---|---|---|---|
| C-001 | Example placeholder | README | Measured | EXP-000 | Tested schemes only | Review | TBD |

The claim register should be created before revisions to the public narrative.

## 3. Known risks

### Research validity

- No real watermark or key in the current exploratory experiment.
- Incorrect or incomplete detector mathematics.
- Topic, register, length, model, and tokenizer confounds.
- Inadequate sample size or unreported selection effects.
- Attack models adapting to known evaluation metrics.
- Metric failure under the intervention being evaluated.

### Generalization

- Results from one watermark family may not transfer to another.
- Results from English may not transfer to other languages.
- Results from one model family or decoding regime may not transfer.
- Generic AI-text detector performance may change over time.

### Quality and fairness

- Detectors may disproportionately flag non-native-English writing.
- Automated quality metrics may reward fluent factual errors.
- Human ratings may be sensitive to register, identity cues, and evaluator expertise.

### Security and misuse

- Detailed attack tooling may facilitate evasion as well as evaluation.
- Public keys or configurations may be misinterpreted as vendor implementations.
- Benchmark optimization may encourage attacks tailored to the released metrics.

### Legal and provenance

- Human corpora, model outputs, and generated derivatives may have incompatible
  licenses or attribution requirements.
- Model terms may restrict redistribution of outputs or weights.
- Source provenance may be lost during pipeline transformations.

## 4. Mitigations

- Use open, documented schemes and clearly distinguish them from vendor systems.
- Require independent mathematical and code review of detector implementations.
- Freeze evaluation code and final splits before running confirmatory experiments.
- Use multiple registers, models, lengths, schemes, and subgroup controls.
- Pair automated quality measures with stratified human review.
- Maintain data lineage, licenses, checksums, and model revision identifiers.
- Conduct a misuse review before releasing high-strength attack components.
- Publish limitations adjacent to results, not only in an appendix.

## 5. Ethical framing

A watermark can provide evidence that a compatible generation system processed a
text. It does not, by itself, establish who authored the ideas, whether use was
permitted, or whether the text is true.

The project should avoid institutional recommendations based on a single detector
score. Practical guidance should require corroborating evidence, an appeal process,
and explicit consideration of subgroup error.

## 6. Release governance

### Required approvals

- Technical validation of watermark and detector implementations.
- Statistical review of the analysis plan and final results.
- Data licensing and provenance review.
- Responsible-release review for attack tooling.
- Claim audit across paper, README, figures, and public articles.

### Versioning

- Tag datasets, configurations, code, and results together.
- Link every publication artifact to a specific release.
- Preserve superseded results with a clear correction notice rather than silently
  replacing them.
- Maintain a changelog of material methodological and claim changes.

## 7. Completion criteria

The project is not release-ready until:

- every headline claim appears in the claim register;
- every result maps to a versioned experiment;
- known confounds are controlled or prominently disclosed;
- code, data, and statistical review are complete;
- communications use the same scope and uncertainty as the technical report.

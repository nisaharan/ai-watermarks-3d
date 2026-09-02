# Publication and Communications Plan

## Current Phase 2 publication decision — 2 September 2026

The active paper is now a calibration, implementation-parity, and validation-
design study. The attack/context-survival paper described in the historical plan
below is deferred because the preregistered null-control gate failed before attacks
were authorized. The current claim boundary and working manuscript are:

- `phase-2/publication-pivot.md`;
- `../../paper/phase2-calibration-manuscript.md`.

The partial joint-KGW Stage A run is excluded from results. No new generation is
required for the current publication package.

## 1. Publication strategy

The appropriate initial ambition is a strong findings paper or specialist workshop
submission, supported by a public preprint and benchmark release. Venue selection
should follow the literature and novelty review rather than precede it.

Potential venue classes include:

- ACL or EMNLP Findings;
- workshops at ACL, EMNLP, NeurIPS, or ICML focused on provenance, safety,
  trustworthy AI, or generative-model evaluation;
- a later full-conference submission if the cross-scheme evidence is sufficiently
  broad and the contribution proves substantial.

## 2. Current paper structure

1. **Introduction:** why nominal FPR and implementation labels are insufficient.
2. **Related work:** watermark null models, empirical calibration, implementation
   identity, and detection–quality trade-offs.
3. **Methods:** exact reference parity, multi-key pilots, and the frozen
   calibration/confirmation design.
4. **Results:** key/length dependence, one-shot gate outcome, and margin diagnosis.
5. **Development evidence:** positive sensitivity and bounded KGW feasibility.
6. **Discussion:** implications for watermark evaluation and staged research gates.
7. **Limitations:** named variants, small models, source scope, and no attacks.
8. **Reproducibility:** frozen configurations, manifests, hashes, code, and reports.

The original context-survival structure remains a future-paper plan only if a new
null-control protocol is prospectively authorized and passed.

## 3. Core release package

- Paper and supplementary material.
- Dataset or reproducible dataset-generation manifest.
- Installable evaluation package.
- Frozen experiment configurations.
- Machine-readable result tables.
- Reproduction guide and lightweight demonstration.
- Model card, dataset card, and responsible-use statement.

## 4. Executive brief

The executive brief should answer:

- What does a text watermark establish?
- What does it not establish?
- How should organizations assess watermark robustness?
- Why are evasion, text quality, and human appearance separate dimensions?
- What controls should precede operational or disciplinary use?
- What are the strategic implications for provenance systems and procurement?

The brief should prioritize decisions and risks rather than implementation detail.

## 5. Visual communication system

The existing visual identity can remain a differentiator, subject to these rules:

- Every empirical figure shows sample size and uncertainty.
- Every conceptual figure says `ILLUSTRATION` in its own caption or frame.
- Three-dimensional plots are used only when the third dimension carries data.
- Static, accessible alternatives accompany animation.
- Color choices remain legible in grayscale and for common color-vision differences.
- Axes, thresholds, and transformations are explicitly defined.
- Figures are generated from final machine-readable results, not manually copied.

## 6. Message hierarchy

### Academic message

Exact implementation parity and key- and length-conditional held-out null
validation must precede robustness claims for the tested text-watermark variants.

### Engineering message

Attack strength should be evaluated through scheme-relevant context destruction,
candidate length, and output quality—not through edit distance alone.

### Executive message

Watermark detection is evidence of compatible system processing, not proof of
authorship, misconduct, truth, or intent.

### Public message

Changing how text looks and removing a statistical watermark are different tasks.

## 7. Communication controls

- Do not use universal terms such as “AI watermarks” when only named schemes were
  tested.
- Do not describe detector output as proof of AI authorship.
- Do not promote a threshold result without its false-positive operating point.
- Do not turn subgroup averages into individual-level conclusions.
- Do not present a confirmed hypothesis until the frozen evaluation is complete.
- Keep caveats adjacent to the claim they limit.

## 8. Publication readiness checklist

- Contribution and novelty reviewed against current literature.
- Protocol deviations recorded.
- Main result independently reproduced.
- Statistical analysis reviewed.
- Licenses and attributions verified.
- All paper figures regenerated from final results.
- README and public articles pass the claim audit.
- Benchmark documentation supports independent reuse.
- Responsible-use and limitations sections approved.

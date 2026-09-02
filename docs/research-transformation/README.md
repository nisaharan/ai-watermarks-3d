# AI Watermarks Research Transformation

Status: Phase 1 complete; Phase 2 validation in progress  
Planning date: 26 August 2026  
Implementation status: remediation complete; native smoke and trace-audit gates passed

## Purpose

This folder defines the proposed transformation of the current AI Watermarks
repository from an exploratory visual explainer into a rigorous, reproducible,
publication-ready research project.

The proposed research thesis is:

> For context-dependent text watermarking schemes, post-attack detectability is
> primarily governed by survival of the watermark's seeding contexts and the
> length of the attacked text, rather than by lexical or semantic distance alone.

This is a hypothesis to test, not a result already established by this repository.

## Document map

| Document | Purpose |
|---|---|
| [01-strategy-and-positioning.md](01-strategy-and-positioning.md) | Defines the research opportunity, audiences, intended contribution, and boundaries. |
| [02-research-protocol.md](02-research-protocol.md) | Specifies research questions, hypotheses, experimental conditions, metrics, and statistical standards. |
| [03-technical-execution.md](03-technical-execution.md) | Describes the target repository architecture, experiment pipeline, testing, and reproducibility requirements. |
| [04-roadmap-and-gates.md](04-roadmap-and-gates.md) | Provides the phased delivery plan, dependencies, decision gates, timing, and outputs. |
| [05-claims-risks-and-governance.md](05-claims-risks-and-governance.md) | Establishes claim controls, known risks, ethics, provenance, and release governance. |
| [06-publication-and-communications.md](06-publication-and-communications.md) | Defines the paper, benchmark, executive brief, visual system, and public communication plan. |
| [metric-specification.md](metric-specification.md) | Defines legacy metrics, canonical units, namespaces, and rules for future measurements. |
| [phase-0/](phase-0/README.md) | Contains the completed baseline audit, claim register, corrected estimator specification, and remediation proposal. |
| [phase-1/](phase-1/README.md) | Contains the literature review, novelty decision, implementation shortlist, and preregistration-ready protocol. |
| [phase-2/](phase-2/README.md) | Contains the keyed ground-truth validation harness, commands, and Phase 2 gate status. |

## Intended final outputs

1. A paper testing the context-survival hypothesis across real keyed watermark schemes.
2. A versioned, documented benchmark of watermarked, unwatermarked, and attacked text.
3. An installable evaluation package with automated attacks and detector baselines.
4. A reproducible experiment pipeline with frozen configurations and statistical tests.
5. A concise executive brief explaining implications for provenance, policy, and AI strategy.
6. A public explainer and visual collection whose claims match the measured evidence.

## Approval decisions required before implementation

- Confirm the narrowed Phase 1 thesis: incremental predictive value of exact,
  scheme-native effective-context survival.
- Confirm the intended publication ambition and timeline.
- Confirm the available compute, budget, and human-review capacity.
- Approve the initial watermark schemes, models, corpora, and attack families.
- Decide whether the existing repository remains the main project or becomes a
  versioned `v0` explainer alongside a new research package.

## Governing principle

No public-facing result should be stronger than the evidence supporting it. Every
figure, table, and headline must identify whether it is measured, modelled,
simulated, counted, or illustrative.

# Phase 0 Review Package

Status: approved; immediate remediation applied  
Audit date: 26 August 2026  
Audited repository state: working tree based on commit `b5f831d`, with the
research-transformation planning documents and `Context-Survival.pdf` uncommitted

## Outcome

Phase 0 concludes that the repository is a strong exploratory explainer but is
**not ready to present its removal results as empirical watermark findings**.

The principal blocker is structural: `example/ai_generated.txt` has no documented
keyed watermark, yet Parts 10-12 convert a word-bigram overlap proxy into detection
scores and “caught” or “evaded” verdicts. The current formula also gives candidate
length the wrong effect under padding.

The proposed context-survival idea remains promising. It should become a hypothesis
tested against real keyed watermarks in Phase 2, rather than a substitute for an
unavailable detector.

## Package contents

| Document | Purpose |
|---|---|
| [validation-report.md](validation-report.md) | Overall confidence assessment, methodological findings, and reproduced checks. |
| [claim-register.md](claim-register.md) | Inventory and disposition of the repository's material claims. |
| [corrected-estimator-specification.md](corrected-estimator-specification.md) | Derivation of the length-corrected projection and requirements for a real detector. |
| [remediation-map.md](remediation-map.md) | File-by-file actions proposed after owner approval. |
| [remediation-implementation.md](remediation-implementation.md) | Records which remediation actions were applied and which remain gated. |
| [`validation/phase0_estimator_checks.py`](../../../validation/phase0_estimator_checks.py) | Read-only script reproducing the calculation checks. |

## Reproduce the checks

From the repository root:

```bash
python3 validation/phase0_estimator_checks.py
```

The script does not change the existing data, figures, or analysis outputs.

## Phase 0 decision requested

Approve or revise these recommendations:

1. Preserve the current materials as a versioned exploratory explainer.
2. Withdraw detector verdict language from the active research narrative.
3. Retain measured descriptive facts only as observations about the two supplied
   texts, not as human-versus-AI findings.
4. Retain context survival as the primary hypothesis for the new research program.
5. Proceed to Phase 1: literature review, novelty assessment, and preregistration-ready
   research protocol.

The underlying source texts and historical calculations remain preserved. Following
approval, active documentation and generators were relabelled so they no longer
present the withdrawn projections as research results.

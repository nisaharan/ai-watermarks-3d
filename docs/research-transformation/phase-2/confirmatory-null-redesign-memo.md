# Phase 2 confirmatory-null failure diagnosis and redesign memo

Date: 31 August 2026  
Status: descriptive diagnosis complete; no replacement threshold or new protocol frozen

## Recommendation

Do not begin another generation run yet. The failed gate is best explained first
by inadequate **validation margin**, especially for KGW, rather than by a broad
upward shift from calibration to confirmation.

If the project retains the same 1% false-positive target, 60-cell familywise gate,
and 95% confidence requirement, the next protocol must predeclare both:

1. a materially lower design false-positive rate than 1%; and
2. enough fresh observations for high probability of passing when that design
   rate is achieved.

The sample size cannot be chosen responsibly until the detection-sensitivity cost
of a more conservative threshold is assessed. No existing confirmation score may
be used to choose that threshold.

## Main diagnosis: KGW thresholds had almost no validation margin

The calibration rule selected the lowest threshold that still passed the exact
confidence gate. For KGW, 28 of 30 cells landed exactly at the maximum of 28
calibration exceedances; the mean was 27.9.

On confirmation, KGW's mean was slightly lower at 27.7 exceedances, yet 14 of 30
cells failed because individual cells fluctuated above 28. This is not evidence of
a broad KGW increase between splits. It is evidence that fitting almost every KGW
cell at the acceptance boundary gave the independent validation little power.

At the boundary rate of 28/5,000 = 0.56%, a new 5,000-sample cell has only about a
55.0% probability of producing 28 or fewer exceedances. Requiring all 60 cells to
pass makes that lack of margin consequential even though the Bonferroni confidence
procedure itself remains valid.

## SynthID was more conservative but had four local failures

Only three of 30 SynthID calibration cells were at the 28-exceedance boundary.
SynthID averaged 18.17 calibration and 18.90 confirmation exceedances, with a
calibration-confirmation cell correlation of 0.648. Four cells failed, concentrated
in keys `synthid-03` and `synthid-08`.

This is not a global SynthID instability result. It shows that the shared
length-specific threshold did not provide enough held-out confidence margin for
every key under the predeclared simultaneous rule.

## Length did not explain the gate by itself

| Prefix length | Failed cells | Mean calibration exceedances | Mean confirmation exceedances |
|---:|---:|---:|---:|
| 128 | 5/20 | 20.85 | 20.60 |
| 256 | 7/20 | 23.70 | 24.10 |
| 512 | 6/20 | 24.55 | 25.20 |

The worst individual result occurred at 512 tokens, but failure counts were not
monotonic with length. Length-specific thresholds addressed the earlier mean-shift
finding; they did not solve the independent-validation margin problem.

## Category structure is a diagnostic warning, not a tuning rule

Classification had the highest confirmation rate in 12 of the 18 failed cells.
Across score rows from those failed cells, its exceedance rate was 1.40% in
confirmation and 1.22% in calibration. Both frozen splits had exactly 729
classification prompts, so this is not a category-mix change.

These score rows are paired across keys and lengths and were declared diagnostic
only. The pattern may reflect category-specific tail behavior, but it cannot justify
category-specific retuning or a confirmatory category claim. A future protocol must
predeclare whether it targets only the frozen overall task mixture or also requires
category-level guardrails.

## Fresh-study planning scenarios

The table below preserves the same 1% target, 60-cell Bonferroni rule, and exact
one-sided interval. The last column is conservative: it is the largest true
per-cell rate compatible with at least 95% probability that all 60 cells pass under
a union-bound power calculation.

| Fresh observations per cell | Maximum passing count | Maximum passing observed rate | True rate for 95% single-cell pass | True rate for conservative 95% all-cell pass |
|---:|---:|---:|---:|---:|
| 5,000 | 28 | 0.560% | 0.415% | 0.300% |
| 10,000 | 69 | 0.690% | 0.569% | 0.467% |
| 20,000 | 156 | 0.780% | 0.685% | 0.603% |
| 50,000 | 431 | 0.862% | 0.797% | 0.740% |

Increasing sample size narrows the confidence penalty, but it does not remove the
need for a true operating rate below 1%. If the true rate is at the target boundary,
high-probability confirmation is impossible regardless of sample size.

## Proposed decision sequence before a new protocol

1. **Confirm the scientific claim.** Decide whether simultaneous at-most-1% control
   across all 60 cells is necessary, or whether a different claim is scientifically
   defensible. Do not change the claim merely to obtain a pass.
2. **Choose a design margin.** If the existing claim remains, select a target true
   null rate below 1% and a desired probability of passing the whole family.
3. **Assess sensitivity trade-offs using development evidence only.** Determine how
   more conservative thresholds affect watermarked-positive detection. The present
   confirmation split must remain report-only and cannot supply threshold choices.
4. **Choose sample size and compute budget.** A 20,000-per-split design supports a
   conservative whole-family margin near 0.60%; 50,000 supports about 0.74%. These
   are planning scenarios, not recommendations to launch either run now.
5. **Preregister a new protocol.** Freeze the threshold policy, power criterion,
   category treatment, variants, keys, prompts, and one-shot decision rule before
   generation.
6. **Use genuinely fresh data.** Exclude all current smoke, pilot, calibration, and
   confirmation prompts from the new calibration and confirmation splits.

## Current authorization boundary

- Preserve the failed protocol and all results unchanged.
- Do not retune on the confirmation split.
- Do not start the watermarked-positive pilot or attack corpus under the failed
  protocol.
- Do not start a replacement null run until a new protocol and compute budget are
  explicitly approved.

## Source-validation update — 31 August 2026

The preferred replacement path now keeps the pinned SmolLM2 model and changes only
the prompt source to pinned `HuggingFaceH4/ultrachat_200k` `train_sft` data. An
exact source audit found 203,109 eligible prompts after deduplication, exclusion of
all prior-study and development prompt overlaps, and the 1,024-token limit. This is sufficient for
fresh 20,000-prompt calibration and confirmation splits.

The proposed design retains the 1%/60-cell/95%-familywise claim and uses a 0.5%
calibration design rate. At 20,000 observations, at most 69 calibration exceedances
satisfy the 0.5% design bound and at most 156 confirmation exceedances satisfy the
1% final bound. The full planning record is
`confirmatory-null-v2-planning.md`; the config remains explicitly marked
`draft_not_authorized_for_generation`.

## Positive-sensitivity update — 31 August 2026

The predeclared 0.5% design-margin sensitivity screen completed 1,000 fresh
watermarked outputs and failed five of 60 cells. Every failure was canonical KGW:
four at 128 tokens and one at 256 tokens. The minimum detection rate was 62%; all
SynthID cells and all 512-token KGW cells passed. All 60 compact/native audits
matched exactly, and no v1 confirmation score was used.

A post-screen 0.5%-0.8% margin grid found no tested design FPR that both cleared
the fixed 80% positive screen in all cells and retained at least 95% conservative
whole-family confirmation power. That result led to the targeted KGW development
now completed below. The replacement null run remained unauthorized. See
`reports/phase2-positive-sensitivity/report.html`.

## KGW bias-development update — 1 September 2026

Two completed fresh targeted development brackets found no KGW generation bias
that passed both the fixed detection and quality guardrails. Bias 2.5 cleared all
eight targeted detection cells in the first bracket but failed quality in two.
The final bounded 2.3/2.4/2.45 bracket also selected no candidate: 2.3 and 2.4
cleared detection but each failed quality in four cells, while 2.45 failed one
detection and three quality cells. Final-bracket failures were driven by repeated
4-grams and reduced bigram diversity, not the NLL guardrail.

Bias-only tuning is closed. Do not run the all-key positive validation or the
replacement null study. The next priority is a formal KGW feasibility/design
decision requiring genuinely new scientific justification before more generation.
See `kgw-bias-development-report.md`.

Subsequent status: that formal decision is complete. It approves exactly one
bounded, preregistered canonical-SelfHash gamma-by-delta feasibility study, with
generation still prohibited until the executable protocol is frozen. See
`kgw-feasibility-design-decision.md`.

## Reproducible evidence

- Analysis: `results/phase2-confirmatory-null/failure-diagnosis.json`
- Analysis code: `validation/analyse_phase2_confirmation_failure.py`
- Frozen gate: `results/phase2-confirmatory-null/confirmation-gate.json`
- Failed-gate record: `docs/research-transformation/phase-2/confirmatory-null-gate-report.md`

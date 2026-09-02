# Phase 2 Confirmatory Null Protocol

Status: frozen before confirmatory generation  
Protocol ID: `phase2-confirmatory-null-v1`  
Frozen: 30 August 2026

## Primary question

Can the declared detector-threshold policy control false-positive probability at
or below 1% simultaneously across canonical KGW SelfHash and SynthID-Text, ten
frozen detector keys and 128/256/512-token length bins on the declared balanced
Dolly task mixture?

## Data separation

Two disjoint 5,000-prompt sets are selected from the pinned Dolly source after
excluding every prompt used by the smoke, 500-prompt pilot and Qwen replication.
The calibration and confirmation sets use identical proportional category quotas,
are deduplicated globally, and are fingerprinted separately.

The confirmation run does not begin until the calibration thresholds are written
to a new immutable artifact and its SHA-256 is recorded. Confirmation is evaluated
once. Any later threshold change requires a new, previously unseen confirmation
set and a new protocol version.

## Threshold fitting

All 5,000 calibration scores in each scheme × key × length cell are ordered from
smallest to largest. The cell candidate is the 4,972nd order statistic (one-based),
so no more than 28 calibration scores are strictly greater when values are unique;
ties make the rule more conservative.

- KGW retains its candidate separately for every key × model × length cell.
- SynthID uses one shared threshold per model × length: the maximum of the ten
  key-specific candidates. Confirmation still tests every SynthID key separately.

The decision rule is always `score > threshold`; equality is non-positive.

## Confirmatory acceptance rule

There are 60 primary cells: two schemes × ten detector keys × three lengths. The
familywise error rate is 5%. Bonferroni allocation gives a one-sided per-cell alpha
of 0.05/60. Each cell receives an exact Clopper-Pearson upper confidence bound for
its realised false-positive probability.

The global gate passes only when all 60 upper bounds are at most 1%. For n=5,000,
that is equivalent to no more than 28 false positives in every cell. A cell with
29 or more fails the global gate. This simultaneous rule is valid without assuming
independence among the ten key scores on the same text.

## Scope and assumptions

- One independent generated continuation per prompt; no repeated outputs are
  treated as independent observations.
- The claim is scoped to the pinned primary model, decoder, prompt population,
  variants, key schedule and length bins.
- Randomised, stratified prompt selection is used to reduce ordering dependence.
- Category results are diagnostics only and do not define or modify thresholds.
- Positive-detection performance is deliberately absent from this gate. The
  conservative-threshold cost is measured only after the null gate passes.

The order-statistic design follows the distribution-free finite-sample detector
threshold approach in Umsonst, Ruths and Sandberg,
[“Finite sample guarantees for quantile estimation: An application to detector
threshold tuning”](https://arxiv.org/abs/2105.12239). The separate confirmation
split independently tests the realised false-positive claim and prevents
in-sample threshold validation.

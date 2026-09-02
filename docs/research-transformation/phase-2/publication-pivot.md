# Phase 2 publication pivot and claim boundary

Decision date: 2 September 2026  
Status: publication preparation authorized; further generation closed

## Decision

Publish the completed validation program as a calibration, implementation-parity,
and experimental-design study. Do not continue the partial joint gamma-by-delta
Stage A run, do not inspect its score distributions, and do not begin Stage B,
replacement confirmation, or attacks.

The 128-token canonical KGW feasibility claim is prospectively re-scoped. The
partial Stage A run ended with 387 contiguous atomic batches and 1,935 of 5,200
planned outputs. It was stopped before outcome analysis. Those records support no
detection, quality, candidate-selection, or grid-failure claim.

The immutable machine-readable decision is
`results/phase2-v2-kgw-joint-feasibility/study-closure.json`.

## Proposed paper

Working title:

> **When Nominal False-Positive Rates Fail: Key- and Length-Conditional
> Validation of Canonical LLM Text Watermarks**

Central research question:

> Do nominal detector null assumptions and calibration-derived operating points
> provide reproducible false-positive control across watermark keys and text
> lengths when implementations are first matched exactly to their maintained
> references?

Primary contribution:

> An exact-reference, multi-key validation workflow showing why implementation
> parity, empirical null calibration, independent confirmation, and explicit
> familywise margins must precede robustness claims.

This is not a paper claiming that all text watermarks fail, that every tested cell
has a true false-positive rate above 1%, or that paraphrase robustness was tested.

## Evidence map

| Evidence block | Design | Supported statement | Boundary |
|---|---|---|---|
| Canonical parity | Maintained-reference detection and generation cross-checks | `kgw_author_selfhash_v1` and `synthid_deepmind_hash_v1` reproduce the pinned keyed primitives exactly on the tested cases | Does not establish statistical calibration or robustness |
| Multi-key null pilot | 500 SmolLM2 null outputs, ten keys, three lengths | Canonical KGW null scores were materially key- and length-conditional; nominal 1% cell FPR reached 47.0% at 512 tokens | Development evidence on one model/source |
| Independent replication | 104 balanced Qwen2.5 null outputs | The KGW key-conditional pattern reproduced, with nominal 1% cell FPR up to 41.3% at 512 tokens | Smaller replication; not a confirmatory operating-point test |
| Frozen calibration/confirmation | 5,000 calibration and 5,000 disjoint confirmation outputs; 60 cells | The preregistered simultaneous at-most-1% guarantee was not established: 18/60 cells failed the exact familywise rule | Failed-cell point estimates were 0.58%–0.96%; failure does not prove each true rate exceeds 1% |
| Failure diagnosis | Frozen-threshold descriptive analysis | The principal design failure was inadequate validation margin: 28/30 KGW calibration cells sat exactly at the 28-exceedance boundary | Diagnostic only; no replacement thresholds were produced |
| Positive sensitivity | 1,000 fresh watermarked outputs | A 0.5% design margin failed five canonical KGW detection cells, concentrated at shorter lengths; SynthID and 512-token KGW passed this development screen | Development screen, not independent validation |
| Bias development | Two fresh bounded targeted brackets | No tested KGW bias passed every fixed detection and quality guardrail | Does not exclude all possible parameterizations |
| Joint gamma-by-delta study | 5,000-output null complete; Stage A stopped at 1,935/5,200 | Only the prospective closure, compute record, and absence of outcome analysis are reportable | No partial Stage A result and no claim that the 12-candidate grid failed |

## Claims safe for the abstract and conclusion

1. Exact implementation identity is a prerequisite for interpreting watermark
   detector evaluations.
2. Under the tested canonical KGW configuration, model families, keys, sources,
   and lengths, the theoretical shared null reference did not provide stable
   key-specific operating behavior.
3. Empirical calibration alone did not establish the preregistered simultaneous
   60-cell guarantee on a disjoint confirmation split.
4. The failure was driven primarily by insufficient confirmation margin under the
   chosen fitting rule, not a general upward shift in held-out KGW exceedances.
5. More conservative null targets created an observed detection/quality trade-off
   in the bounded development studies.
6. Robustness or attack claims remain unavailable because the null-control gate
   failed before attacks were authorized.

## Claims prohibited

- “KGW has a 47% false-positive rate” without naming the key, model, length,
  nominal threshold, and pilot status.
- “The true false-positive rate exceeded 1% in 18 cells.”
- “SynthID was validated” or “KGW was invalidated” as universal scheme claims.
- “The joint gamma-by-delta grid failed.”
- Any watermark-removal, attack-resistance, authorship, misconduct, or deployment
  claim based on this program.
- Pooling canonical and Transformers variant scores.

## One-day publication priorities

1. **Freeze the pivot and recovery state — complete.** Preserve the closure
   artifact, partial batches, frozen protocols, and no-resume status.
2. **Lock the paper claim and evidence map — complete.** Use this document as the
   claim-audit source for every abstract, table, caption, and conclusion.
3. **Draft the manuscript core — in progress.** Complete abstract, introduction,
   methods, results, discussion, limitations, and reproducibility sections from
   existing evidence only.
4. **Assemble publication tables and figures.** Reuse the validated Phase 2 and
   confirmation-gate report datasets; do not manually transcribe result values.
5. **Run final audit.** Reproduce headline counts, test the recovery/closure path,
   check variant names and caveats, and ensure no partial Stage A statistic appears.

## Recommended submission position

Target a Findings-style or specialist trustworthy-AI/provenance venue. Present the
work as a rigorous measurement and validation result. The strongest contribution
is the sequence from exact implementation parity through independent null
confirmation and documented feasibility limits, including negative outcomes and
hard stops.


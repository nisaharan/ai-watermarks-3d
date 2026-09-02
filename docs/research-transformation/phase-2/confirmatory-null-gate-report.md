# Phase 2 confirmatory-null gate report

Run date: 31 August 2026  
Status: one-shot confirmation gate failed; attacks and post-confirmation retuning are prohibited

## Decision

The frozen confirmatory procedure did **not** establish simultaneous false-positive
control at or below 1% across all 60 primary cells. Eighteen cells failed the
predeclared exact-confidence rule, so the full attack corpus and the planned
watermarked-positive pilot remain closed.

This result does not invalidate implementation parity, and it does not show that
every failed cell has a true false-positive rate above 1%. It shows that the
project cannot make the stronger predeclared claim that all 60 cell rates are at
most 1% with 95% familywise confidence.

## Frozen design and acceptance rule

- 5,000 calibration nulls and 5,000 disjoint confirmation nulls;
- canonical `kgw_author_selfhash_v1` and `synthid_deepmind_hash_v1` scores;
- ten detector keys and paired 128-, 256-, and 512-token prefixes;
- 60 primary cells, each containing 5,000 confirmation observations;
- frozen KGW key x model x length thresholds;
- frozen SynthID model x length thresholds set to the maximum of the ten
  key-specific calibration candidates;
- strict exceedance rule: `score > threshold`;
- exact one-sided Clopper-Pearson upper bounds with Bonferroni-adjusted per-cell
  alpha `0.0008333333333333334`;
- pass only if every cell has an upper bound at or below 1%;
- at most 28 exceedances pass; 29 or more fail.

## Gate result

| Result | Cells |
|---|---:|
| Passed | 42 |
| Failed | 18 |
| Total | 60 |

Fourteen of 30 KGW cells and four of 30 SynthID cells failed. By length, five
failures occurred at 128 tokens, seven at 256 tokens, and six at 512 tokens.

The observed exceedance rates in the failed cells ranged from 29/5,000 (0.58%) to
48/5,000 (0.96%). Although those point estimates are below 1%, their simultaneous
exact upper confidence bounds exceed 1%. The most extreme cell was KGW key 03 at
512 tokens: 48/5,000 strict exceedances, empirical rate 0.96%, exact upper bound
1.4761%.

## Failed cells

| Scheme | Key | Length | Strict exceedances | Empirical rate | Exact upper bound |
|---|---|---:|---:|---:|---:|
| KGW | kgw-03 | 128 | 32 | 0.64% | 1.0787% |
| KGW | kgw-03 | 256 | 34 | 0.68% | 1.1293% |
| KGW | kgw-03 | 512 | 48 | 0.96% | 1.4761% |
| KGW | kgw-04 | 256 | 35 | 0.70% | 1.1545% |
| KGW | kgw-05 | 128 | 34 | 0.68% | 1.1293% |
| KGW | kgw-05 | 256 | 34 | 0.68% | 1.1293% |
| KGW | kgw-05 | 512 | 34 | 0.68% | 1.1293% |
| KGW | kgw-06 | 128 | 32 | 0.64% | 1.0787% |
| KGW | kgw-06 | 256 | 37 | 0.74% | 1.2046% |
| KGW | kgw-06 | 512 | 39 | 0.78% | 1.2545% |
| KGW | kgw-08 | 256 | 30 | 0.60% | 1.0278% |
| KGW | kgw-09 | 128 | 29 | 0.58% | 1.0022% |
| KGW | kgw-09 | 256 | 31 | 0.62% | 1.0533% |
| KGW | kgw-09 | 512 | 30 | 0.60% | 1.0278% |
| SynthID | synthid-03 | 128 | 30 | 0.60% | 1.0278% |
| SynthID | synthid-03 | 256 | 32 | 0.64% | 1.0787% |
| SynthID | synthid-03 | 512 | 31 | 0.62% | 1.0533% |
| SynthID | synthid-08 | 512 | 33 | 0.66% | 1.1040% |

## Interpretation boundary

The confirmatory evidence supports these conclusions:

1. The frozen calibration procedure failed its predeclared simultaneous 60-cell
   validation gate on held-out text.
2. A validated claim of at-most-1% false-positive behavior across every tested
   scheme x key x length cell is not available.
3. The attack experiment cannot start because its detector operating points have
   not passed the required null-control gate.
4. Canonical parity remains passed; this is a statistical operating-point failure,
   not evidence of a new implementation mismatch.

The result does not support ranking or selecting favourable keys, fitting new
thresholds to confirmation, category-specific retuning, or claiming that the
watermark-removal thesis itself passed or failed. No attacked watermarked corpus
was run.

## Validation checks

- Calibration: 1,000 contiguous atomic batches, 5,000/5,000 records, metadata
  matched files.
- Confirmation: 1,000 contiguous atomic batches, 5,000/5,000 records, metadata
  matched files.
- Calibration and confirmation prompt hashes were disjoint.
- The evaluator verified the frozen protocol and threshold hashes before scoring.
- All 60 saved cells contained exactly 5,000 observations.
- Independent recount from the saved artifact reproduced 42 passes and 18 failures.
- Automated acceptance-boundary tests passed: 28 exceedances pass and 29 fail.
- The one-shot artifact records `post_confirmation_retuning_authorized: false`.

## Authorized next work

1. Preserve the frozen protocol, thresholds, completed split artifacts, and failed
   one-shot gate as the permanent confirmatory record.
2. Do not run the positive pilot or attack corpus under this protocol.
3. Reassess the claim as a measurement-design problem: the current evidence is
   insufficient for the simultaneous at-most-1% guarantee.
4. If a new study is proposed, preregister it and use genuinely fresh calibration
   and confirmation data. The present confirmation split may be reported as prior
   evidence but must never become tuning data for a renewed confirmatory claim.
5. Before any new generation, decide whether the scientific target should remain
   the same strict 60-cell familywise guarantee, use a larger fresh null sample,
   or adopt a different predeclared operating claim. That decision requires a new
   protocol, not a post-hoc edit to this one.

## Evidence

- Frozen protocol: `configs/phase2-confirmatory-null.json`
- Frozen thresholds: `results/phase2-confirmatory-null/thresholds.json`
- Completed confirmation: `results/phase2-confirmatory-null/confirmation/run.json`
- One-shot gate: `results/phase2-confirmatory-null/confirmation-gate.json`
- Evaluator: `src/ai_watermarks_phase2/calibration_gate.py`


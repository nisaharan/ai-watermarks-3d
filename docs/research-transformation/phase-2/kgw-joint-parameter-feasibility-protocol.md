# Canonical KGW joint-parameter feasibility protocol

Protocol ID: `phase2-v2-kgw-joint-feasibility-v1`  
Date: 1 September 2026  
Status: executable preregistration ready for fingerprint freeze and compute-budget authorization; no generation authorized

## Decision question

Does any member of the fixed canonical-SelfHash parameter family

```text
gamma ∈ {0.25, 0.50, 0.70}
delta ∈ {2.0, 2.5, 3.0, 4.0}
```

meet the existing short-text detection requirement without violating fixed output-
quality and implementation-safety guardrails on the pinned SmolLM2/UltraChat
setting? This is a development feasibility question. It cannot repair the failed
v1 gate, establish false-positive control, or authorize attacks.

The machine-readable source of truth is
`configs/phase2-v2-kgw-joint-feasibility.json`.

## Frozen invariants

- Watermark variant: `kgw_author_selfhash_v1`, anchored Min-SelfHash, context
  width four. LeftHash and the Transformers SelfHash variant are excluded.
- Model: `HuggingFaceTB/SmolLM2-135M-Instruct` at revision
  `12fd25f77366fa6b3b4b768ec3050bf629380bac`.
- Decoder: CPU, temperature 0.8, top-k 40, tie-inclusive top-k policy.
- Keys: the existing deterministic ten-key schedule. Scores remain explicitly
  indexed by gamma and key and are never pooled across variants.
- Prompt population: the pinned eligible UltraChat `train_sft` population after
  all existing study/development exclusions and the 1,024-token prompt cap.
- Every output contains the exact fixed number of generated tokens. This preserves
  the existing 128/256/512 prefix estimands; decoded-length behavior is guarded
  separately.

## Data separation and order

Three mutually disjoint fresh manifests are frozen together:

1. 5,000 development-null prompts;
2. 100 Stage-A prompts;
3. 100 Stage-B prompts.

They exclude every smoke, pilot, v1 calibration/confirmation, positive-sensitivity
and bias-development prompt and are permanently excluded from later v2 calibration
or confirmation.

The order is mandatory:

1. Generate and finish the development null.
2. Fit and freeze gamma-specific provisional thresholds.
3. Run Stage A and its automated analysis.
4. Complete blinded review for every automatically eligible candidate.
5. Freeze at most one Stage-A selection.
6. Run Stage B only for that one selection.

No later stage may start early, and no partial distribution may change a threshold,
candidate, guardrail or sample size.

## Fresh development-null thresholds

The same 5,000 unwatermarked continuations are compact-scored under all three gamma
values, ten keys and three prefix lengths, producing 90 separately named cells.
At a 0.5% design FPR and 95% Bonferroni familywise confidence, the per-cell alpha
is `0.05 / 90 = 0.0005555555555555556`. Exact one-sided Clopper-Pearson inversion
allows at most 9 strict exceedances in 5,000 observations; 10 fail the design
bound. The threshold is the order statistic with at most 9 values strictly above
it. Comparison is always `score > threshold`.

Every operational threshold is indexed by gamma × detector key × model × length.
No gamma-0.25 threshold is reused or transformed for another gamma. The v1
confirmation split is never loaded.

## Stage A: fixed factorial screen

Stage A generates every one of the 12 candidates for keys 03, 05, 07 and 08 on
the same 100 prompts, plus one unwatermarked control per key/prompt. Paired batch
seeds are shared across the control and candidates within a key and prompt block.
Each output is 256 tokens and contributes 128- and 256-token prefix measurements.

### Detection outcome

A candidate must record at least 80 strict detections out of 100 in every one of
the eight key × length cells. The 80% rate is the fixed decision target inherited
from the earlier sensitivity screens. A one-sided 95% exact lower bound is reported
for interpretation but does not replace the predeclared count gate. Keys and
lengths are never averaged.

### Automated output-quality and safety guardrails

For every key × length cell, compare candidate and paired unwatermarked means.
All conditions must hold:

- conditional base-model NLL increase ≤ 0.15 nats/token;
- repeated-4-gram fraction increase ≤ 0.02 absolute;
- distinct-2-gram fraction decrease ≤ 0.02 absolute;
- mean decoded-character-count ratio between 0.85 and 1.15;
- zero empty decoded outputs and exact raw generated-token lengths;
- empty SelfHash rejection no-op rate ≤ 0.001 of generated token positions.

The no-op counter is diagnostic instrumentation around the already validated
empty-long-index safeguard; it does not alter non-empty candidate selection.

### Blinded task-quality veto

Every candidate that clears all automated gates receives a blinded paired review
on 50 frozen key × prompt pairs selected by SHA-256 rank. Two raters see the prompt
and randomly labelled candidate/control responses but not the parameter identity.
The fixed response categories and adjudication rule are stored in the config.

A candidate fails if any adjudicated pair marks its response unusable or if both
raters prefer the control in more than 10 of 50 pairs. Rater identifiers and the
label-randomization seed must be frozen before review. Review results are immutable
inputs to selection.

### Selection

Eligible candidates pass every detection, automated-quality and blinded-quality
gate. Select the eligible candidate with the smallest worst-cell NLL increase.
Values within 0.005 nats/token are tied; ties resolve by lower delta, then gamma
closest to 0.50, then lower gamma. At most one candidate advances.

If none advances, close or prospectively re-scope the 128-token canonical KGW
claim. No interpolation, guardrail relaxation, replacement candidate or further
tuning is permitted.

## Stage B: one-candidate independent validation

Stage B uses its untouched 100 prompts, all ten keys and 128/256/512-token
prefixes. It generates the single frozen candidate and a paired unwatermarked
control for every key/prompt. The same per-cell 80/100 detection gate, automated
quality/safety rules and 50-pair blinded-review veto apply across all 30 cells.

Failure closes or prospectively re-scopes the 128-token claim with no candidate
substitution. Success permits drafting a new full null calibration/confirmation
protocol. It does not authorize that protocol, the proposed 20,000-prompt splits,
or attacks.

## Compute and storage budget

The budget is based on completed local CPU timings:

| Component | Planning estimate |
|---|---:|
| 5,000-output development null and 90-cell scoring | 6.5 hours |
| Stage A, 5,200 outputs and quality analysis | 9.7 hours |
| Stage B, 2,000 outputs and quality analysis, if reached | 5.1 hours |
| Total planned CPU wall time | 21.3 hours |
| Hard CPU wall-time authorization cap | 24.0 hours |
| Storage authorization cap | 0.5 GB |

Manual review is additional. In the worst case, all 12 Stage-A candidates reach
review, requiring 1,200 individual pair ratings; the selected candidate's Stage-B
review adds 100, for a hard maximum of 1,300 ratings. The execution plan should
schedule review before committing to Stage B.

## Authorization and recovery

The protocol and manifests may be prepared, validated and fingerprinted before
generation. A separate authorization artifact must record the protocol freeze
digest and the user's approval of the 24-hour/0.5-GB cap. Runners must reject a
missing, mismatched or unapproved artifact.

The authorization artifact must have status
`kgw_joint_feasibility_generation_approved`, match both the protocol-config and
protocol-freeze SHA-256 digests, name a non-empty approver and UTC approval time,
repeat the exact compute/storage caps, and use approved scope
`development_null_stage_a_and_conditional_stage_b_only`. Approval does not cover
a v2 confirmation run or attacks.

Generation remains unauthorized at this protocol revision. When authorized,
every run writes atomic five-output batches and validates contiguous names, input
fingerprints, prompt order, paired seeds and completed record counts before resume.
The recovery command must remain the source of truth for the next legal transition.

## Executable implementation

The implementation consists of a locked development-null runner, exact threshold
fitter, Stage-A/Stage-B paired-generation runner, automated analysis and frozen
selection rules, plus deterministic blinded-packet and two-rater collation tools.
All real generation entry points require the separate authorization artifact.
Their `--dry-run` modes validate the setup while continuing to report generation
as unauthorized.

The final pre-authorization sequence is:

```bash
.venv/bin/python validation/validate_phase2_v2_kgw_joint_protocol.py --require-manifests
.venv/bin/python -m ai_watermarks_phase2.kgw_joint_null --dry-run
.venv/bin/python -m ai_watermarks_phase2.kgw_joint_stage --stage stage_a --dry-run
.venv/bin/python validation/freeze_phase2_v2_kgw_joint_protocol.py
.venv/bin/python -m ai_watermarks_phase2.resume_status
```

After the freeze, any change to a fingerprinted protocol input requires a new
prospective protocol revision and freeze; the existing freeze must not be silently
replaced.

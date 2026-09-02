# Phase 1 Decision Memo

## Decision

**Conditional go to Phase 2.** Reposition before implementation.

## Why go

- The project has a testable mechanism tied directly to open watermark internals.
- Two official, structurally different implementations are available.
- The proposed nested, out-of-cell predictive test is narrower than existing broad
  robustness benchmarks and can produce a useful negative result.
- Phase 0 has already removed the unsupported detector claims and corrected the
  estimator framing.

## Why conditional

- The motivating n-gram survival phenomenon is established prior art.
- Current benchmarks are mature; a simple scheme × attack leaderboard will not be
  a sufficient contribution.
- “Context survival” may collapse to attacked length or ordinary n-gram overlap.
- Exact computation may be scheme-specific, particularly under alignment,
  repeated-context masking, and semantic/context-free watermarks.

## Phase 2 success criteria

Phase 2 is complete only when:

1. KGW and SynthID-Text keyed generation and native detection run from pinned,
   reproducible configurations.
2. Null calibration, repeated-context, padding, truncation, and deterministic-edit
   tests pass.
3. Per-position native contexts and scores are exported.
4. Synthetic edits confirm that the alignment-based survival implementation is
   at least 99.5% position-accurate.
5. A small blinded pilot shows the proposed variable is not merely a renamed token
   overlap due to an implementation error.

## Stop or reposition triggers

- **Stop the predictor thesis** if native context state cannot be reconstructed
  exactly for both primary schemes.
- **Reposition to a KGW-only measurement paper** if the definition is valid for
  KGW but incoherent for SynthID-Text.
- **Reposition to a negative benchmark result** if context survival adds no
  predictive value beyond simpler metrics; preserve the preregistered finding.
- **Stop expansion** if empirical false-positive calibration is unstable or
  results depend on unreleasable, undocumented components.

## Immediate next action

Build a tiny Phase 2 validation harness using one small open causal model, ten
prompts, both primary watermark configurations, and deterministic attacks. Do not
generate the full corpus until all validation gates pass.


# Phase 2 KGW feasibility and joint-parameter decision

Date: 1 September 2026  
Status: decision approved; study protocol and generation remain unfrozen and unauthorized

## Final decision

Retain canonical KGW SelfHash for exactly one final, bounded feasibility study of
the joint green-list-ratio and logit-bias family. Treat this as a genuinely new
development protocol, not as a repair, continuation, or reinterpretation of the
failed v1 confirmatory study.

The fixed candidate family is:

- green-list ratio `gamma` in `{0.25, 0.50, 0.70}`;
- logit bias `delta` in `{2.0, 2.5, 3.0, 4.0}`;
- all 12 Cartesian-product combinations, without interpolation or an added
  candidate after results are seen.

This decision does not authorize generation. The next authorized work is to write,
review, fingerprint and approve an executable preregistration for the study below,
including its compute budget and fresh prompt manifests.

If no candidate passes the targeted feasibility stage, or if the one selected
candidate fails independent all-ten-key validation, close the 128-token canonical
KGW claim. The project must then omit KGW from the current simultaneous claim or
scope KGW prospectively to longer texts. There will be no third tuning round,
threshold weakening, post-result gamma interpolation, or further bias-only study.

## Why this is a scientifically new question

The completed local studies varied `delta` only while holding `gamma = 0.25`.
Biases above 2.0 repaired most short-text detections but caused repeated-4-gram and
distinct-2-gram failures. In canonical SelfHash, `gamma` also changes how many of
the top-k candidates can survive the self-salt rejection rule. A broader green
list may therefore reduce candidate scarcity and repetition while a jointly chosen
`delta` preserves detection. That interaction was not tested locally.

Changing `gamma` also changes the detector statistic and its empirical null
distribution. Thresholds fitted at `gamma = 0.25` are invalid for `gamma = 0.50`
or `0.70`; each gamma requires fresh, separately named development thresholds.

## What prior work actually did

| Source | Joint-parameter evidence | Transfer boundary |
|---|---|---|
| [Kirchenbauer et al., *A Watermark for Large Language Models*](https://proceedings.mlr.press/v202/kirchenbauer23a.html) | Swept gamma and delta and reported factorial results including gamma in `{0.25, 0.50}` and delta in `{1, 2, 5}`. It established a nonlinear quality-detection frontier rather than a universal setting. | The experiments used the earlier previous-token scheme, later called LeftHash, on OPT/C4 at about 200 tokens; they are not canonical SelfHash results. |
| [Official author implementation and guidance](https://github.com/jwkirchenbauer/lm-watermarking) | Uses `gamma = 0.25`, `delta = 2.0` as the baseline, describes gamma from 0.25 to 0.75 as reasonable, and notes that overconfident instruction models may require a larger delta. | Guidance, not a factorial SelfHash experiment; it cannot select a pair for SmolLM2. |
| [Kirchenbauer et al., *On the Reliability of Watermarks for Large Language Models*](https://proceedings.iclr.cc/paper_files/paper/2024/file/d78e9e4316e1714fbb0f20be66f8044c-Paper-Conference.pdf) | Establishes anchored Min-SelfHash, context width four, top-40 rejection sampling, repeated-context correction, and its robustness/quality behavior. | Its SelfHash ablations hold gamma fixed at 0.25 and do not perform a joint gamma-delta sweep. |
| [Molenda et al., *WaterJudge*](https://arxiv.org/abs/2403.19548) | Evaluated broad combinations of green-list size and bias, directly visualized the quality-detectability frontier, and found model/task-specific operating points. It also found length/EOS effects and that perplexity alone can miss quality loss. | Uses a previous-token green-list scheme on summarization and translation models, not canonical SelfHash or this false-positive gate. |
| [Cai et al., *Towards Better Statistical Understanding of Watermarking LLMs*](https://arxiv.org/abs/2403.13027) | A factorial gamma-delta study shows that misaligned pairs can be suboptimal and that a broader green list can reduce distortion at strong bias while preserving detection. | Uses a one-token/LeftHash-style scheme and larger models; the direction is a hypothesis for SelfHash, not a transferable result. |
| [Piet et al., *Mark My Words*](https://arxiv.org/abs/2312.00273) | Explored gamma, then fixed 0.5 and selected delta by model temperature and constrained quality; it also evaluated quality beyond perplexity. | Uses sliding-window/min-hash randomness rather than self-salting canonical SelfHash, and its preferred gamma conflicts with other studies. |
| [WaterBench](https://arxiv.org/abs/2311.07138) | Grid-searches gamma, delta and detection settings and evaluates task quality. | Its appendix's `v2` label is LeftHash plus WinMax, not `kgw_author_selfhash_v1`; its numerical settings must not be cited as SelfHash evidence. |

The literature therefore supports a joint study but not an off-the-shelf setting.
Published gamma preferences conflict, and no inspected study resolves canonical
anchored Min-SelfHash on SmolLM2 with top-k 40, temperature 0.8 and 128-token
outputs. That specific gap is the justification for the final local study.

`gamma = 0.10` is excluded. Its attractive published results come from LeftHash,
while canonical SelfHash would retain only about four of the top 40 candidates in
expectation. The local implementation has already encountered empty rejection
sets at `gamma = 0.25`, so a smaller green list is a poor safety direction here.

## Required preregistered design

### Invariants

- Variant: `kgw_author_selfhash_v1` only, anchored Min-SelfHash with context width
  four. Never pool or substitute `kgw_transformers_selfhash_v5_16` or LeftHash.
- Keep the pinned SmolLM2 model, UltraChat source revision, ten base keys,
  temperature 0.8, top-k 40 and the documented tie-inclusive decoder policy.
- Exclude every prompt used in smoke, pilots, v1, positive sensitivity and all
  three bias-development attempts.
- Use atomic resumable batches, fixed paired randomness and compact/native parity
  audits.

### Fresh development null

Before examining new watermarked-positive results, generate a fresh UltraChat
development-null set. The same clean outputs may be scored across the three gamma
values, but every threshold must be separately indexed by gamma, key, model and
length. Fit and freeze provisional thresholds at the existing 0.5% design FPR.
Do not reuse or transform the gamma-0.25 thresholds for another gamma, and do not
use any v1 confirmation score.

The executable protocol must justify the null sample size for estimating a 0.5%
tail. Five thousand clean outputs is the current minimum planning value; lowering
it requires a new exact-binomial precision analysis before approval.

### Stage A: targeted factorial feasibility

- Keys: the established weak keys `kgw-03`, `kgw-05`, `kgw-07` and `kgw-08`.
- Candidates: all 12 fixed gamma-delta pairs.
- Samples: 100 fresh UltraChat prompts per candidate and key.
- Generation: 256 tokens, with paired 128- and 256-token scoring.
- Controls: paired unwatermarked output and the exact `(0.25, 2.0)` historical
  operating point on the same prompts.
- Detection gate: at least 80% strict detections in every key by length cell at
  the frozen gamma-specific provisional threshold. Do not average across cells.
- Existing quality guardrails versus the paired unwatermarked control:
  conditional base-model NLL increase at most 0.15 nats/token, repeated-4-gram
  fraction increase at most 0.02 absolute, and distinct-2-gram fraction decrease
  at most 0.02 absolute in every cell.
- Add preregistered EOS/output-length shift and empty-candidate/no-op frequency
  guardrails. Include a blinded task-quality comparison for otherwise eligible
  finalists because prior work shows NLL and lexical metrics can miss degradation.

If several candidates pass every constraint, select the candidate with the
smallest worst-cell NLL increase. A tie within a predeclared numerical tolerance
goes first to lower delta and then to gamma closest to 0.50. Freeze the tolerance,
the task-quality rule and treatment of missing/EOS outputs before generation.

### Stage B: independent all-key validation

Validate only the one Stage-A selection on fresh prompts across all ten keys and
128-, 256- and 512-token prefixes. Use the same per-cell detection and quality
rules, with a preregistered sample size and no candidate substitution. Passing
Stage B permits drafting a new full null calibration/confirmation protocol; it
does not itself authorize that run or attacks.

## Interpretation and authorization boundary

This study can answer whether any member of the fixed family is feasible for a
future protocol. It cannot rescue v1, establish false-positive control, validate
attacks, or support a robustness claim. The completed v1 calibration,
confirmation, thresholds and failed gate remain frozen and reportable exactly as
they are.

Current authorization is limited to protocol/configuration design, power and
compute calculations, implementation, tests, and review. Generation begins only
after the new protocol, source exclusions, manifests, fingerprints, stop rules
and compute budget are explicitly approved.

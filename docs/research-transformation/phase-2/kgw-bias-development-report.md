# Phase 2 v2 KGW generation-bias development report

Date: 1 September 2026  
Status: no generation-bias candidate passed both detection and quality; bias-only tuning closed

## Decision

Do not select a new KGW generation bias. Do not run the independent all-key
positive validation, freeze the v2 null protocol, launch the approximately
40-hour null study, or begin attacks.

The original bias 2.0 remained too weak at 128 tokens. Stronger biases repaired
the targeted detection screen, but no tested candidate also passed every
predeclared quality guardrail. The result is development evidence, not a
confirmatory detection claim.

## Experiments

Both completed experiments used the pinned SmolLM2 model, canonical
`kgw_author_selfhash_v1`, four previously weak keys (03, 05, 07 and 08), 50 fresh
UltraChat prompts per condition, paired 128/256-token prefixes, and provisional
0.5%-design thresholds fitted only from v1 calibration data.

| Experiment | Bias | Failed detection cells | Failed quality cells | Selected |
|---|---:|---:|---:|:---:|
| First bracket | 2.0 | 4/8 | 0/8 | No |
| First bracket | 2.5 | 0/8 | 2/8 | No |
| First bracket | 3.0 | 0/8 | 8/8 | No |
| Final bracket | 2.0 | 4/8 | 0/8 | No |
| Final bracket | 2.3 | 0/8 | 4/8 | No |
| Final bracket | 2.4 | 0/8 | 4/8 | No |
| Final bracket | 2.45 | 1/8 | 3/8 | No |

Every candidate had to reach at least 40/50 strict detections in all eight
targeted cells. Relative to the paired bias-2.0 control, every cell also had to
remain within all of these fixed quality tolerances:

- conditional base-model NLL increase at most 0.15 nats/token;
- repeated 4-gram fraction increase at most 0.02 absolute;
- distinct 2-gram fraction decrease at most 0.02 absolute.

In the final bracket all candidate NLL checks passed. Failures were driven by
repetition and/or diversity. Bias 2.3 is therefore not eligible despite clearing
all detection cells: it failed quality for key 03 at 128 and 256 tokens, key 05
at 128, and key 07 at 128.

## Integrity and implementation record

An initial attempt stopped after 95 durable outputs when the canonical author
rejection loop returned an empty float tensor as a logits index. Those outputs
were not analyzed or reused. The two completed experiments used fresh prompts and
an explicit safeguard that represents an empty candidate set as `torch.long`,
making the intended action a no-op while leaving non-empty behavior unchanged.

- completed bracket run digest:
  `04a260f2b61b28f1092261959849e7e783f39bc3a3f7666c79dd5edc55e48d49`
- final bracket run digest:
  `2badca24f2be38bf8cfc40fe7a8392eff8e0cd563c329139e115b664098d4568`
- completed outputs: 600 plus 800; all condition counts exact;
- compact/native audits: 24 plus 32; every audit exact;
- v1 confirmation scores used: no;
- attacks authorized: no.

The bounded-memory NLL calculation was independently compared with direct model
logits on a short sequence and agreed within `4e-7` nats/token.

## Next priority

Stop bias-only tuning and make a formal KGW feasibility decision before generating
more data. The decision must choose between a genuinely new preregistered KGW
parameter-family study (for example, jointly studying green-list ratio and bias)
or a separately scoped future protocol that does not make the current 60-cell KGW
claim. Either choice requires new scientific justification and fresh data; neither
can reinterpret these failed development screens as a pass.

Subsequent status: the formal decision is complete and approves exactly one final,
bounded joint gamma-by-delta feasibility study, still requiring a frozen executable
protocol before generation. See `kgw-feasibility-design-decision.md`.

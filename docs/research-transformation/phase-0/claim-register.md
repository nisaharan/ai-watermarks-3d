# Phase 0 Claim Register

## Status vocabulary

- **Retain:** support and scope are adequate.
- **Narrow:** retain only with more precise wording or scope.
- **Relabel:** evidence provenance is misstated or insufficiently visible.
- **Withdraw:** current evidence cannot support the claim.
- **Retest:** preserve as a hypothesis for the new experiment.
- **Verify literature:** external support must be checked in Phase 1.

## Register

| ID | Material claim | Principal locations | Current evidence | Assessment | Required disposition |
|---|---|---|---|---|---|
| C-001 | Statistical text watermarks can be encoded through token-selection bias. | Main document Parts 1-2; GIFs 03-04 | Literature/mechanism | Plausible but not vendor-general | Narrow; verify literature |
| C-002 | C2PA file provenance and in-text statistical watermarks are different channels. | Main document Part 1 | Standards/literature | Useful taxonomy | Retain; verify scheme/vendor scope |
| C-003 | A watermark result means “processed by,” not “written by.” | README conclusion; articles | Interpretation | Directionally sound but scheme-specific | Narrow; verify literature and policy language |
| C-004 | Short text hides while long text cannot. | GIF 04; README figure table | Simulated mechanism | Absolute wording exceeds theory | Narrow to probabilistic detection power |
| C-005 | The textbook picture oversells word-level signal. | README finding 1; GIF 07 | Measured pair vs author-selected simulation | Circular comparison | Withdraw until published baseline exists |
| C-006 | Word choice alone will not tell who wrote a text. | README; GIF 07; main document | One pair plus general concern | Conclusion too broad for experiment | Narrow and verify literature |
| C-007 | Rhythm separates human from AI better than vocabulary. | README finding 2 and conclusion | One matched pair | No population variance | Withdraw as finding; retain sample observation |
| C-008 | The AI's paragraph pattern did not occur by accident. | README; articles | One generated text | Probability not estimated | Withdraw |
| C-009 | Five four-sentence paragraphs are a dependable AI tell. | Articles; GIF 10 | One AI sample | Unsupported individual inference | Withdraw; retain visual description only |
| C-010 | Vocabulary freshness points backwards. | README; GIF 08 | One pair, tokenizer-dependent TTR | True for this pair only | Narrow and standardize tokenizer |
| C-011 | Layer A changed no characters in the supplied AI text. | README; Part 10; GIF 11 | Byte identity | Verified for stored sample | Retain narrowly |
| C-012 | Unicode stripping cannot touch a watermark living in token choice. | README; main document; articles | Mechanistic reasoning | Valid for this carrier distinction | Retain with scheme scope |
| C-013 | A watermark remover mostly cannot remove the watermark. | README finding 3 | No applied watermark | Object absent | Withdraw |
| C-014 | Two of four rewrites are still caught. | README; Part 10; articles; GIF 11 | Invalid modelled proxy | Not a detector result | Withdraw |
| C-015 | Backtranslation is the weakest attack. | README; Part 10; articles | One hand-produced output | No variance; unequal attack cost | Withdraw; retest |
| C-016 | Paraphrase remains detectable at z=4.50. | Part 10; GIF 11 | Invalid modelled proxy | Not measured | Withdraw |
| C-017 | Structural and humanize evade detection. | Part 10 | Invalid modelled proxy | Not measured | Withdraw |
| C-018 | Structural is the best attack-quality trade-off. | Part 10 | Crude fact proxy and one output | Inadequate quality measurement | Withdraw; retest on common cost axis |
| C-019 | Bigram survival represents surviving watermark evidence. | Analysis code; Part 10 | Set overlap proxy | Topic/chance contaminated | Relabel as exploratory proxy; retest |
| C-020 | Context survival is a mechanistic predictor of post-attack detection. | Emerging roadmap | Theory plus exploratory intuition | Falsifiable, not yet established | Retest as primary hypothesis |
| C-021 | The heaviest rewrite scored more human than the human. | README; articles; GIF 12 | Selected heuristic values on one pair | No human scale or real detector | Withdraw as detector claim; narrow to metric overshoot |
| C-022 | Public detectors use the exact measured features. | Articles; main document | No detector suite or implementation trace | Overgeneralized | Withdraw; verify literature |
| C-023 | These metrics have no upper bound at human. | Part 10; articles | Conceptual observation | “Human” is a distribution, not a point | Reframe as one-sided-threshold limitation |
| C-024 | Tier 3 tell counts decline under rewriting. | Part 10 | Regex counts | Numerically reproducible | Retain as string-pattern counts only |
| C-025 | Tier 3 tells are the one honest or most dependable signal. | Part 10; articles | Fragile regex instrument | Unsupported comparison | Withdraw |
| C-026 | Facts retained are 97-100%. | Part 10 | Proper-noun/number presence heuristic | Not factuality evaluation | Relabel as entity/number retention proxy |
| C-027 | Detectors are biased against non-native-English writers. | README caveat; articles | External literature assertion | Important but not tested here | Verify literature; do not imply local measurement |
| C-028 | GPT-2 surprisal is measured correctly for the stored outputs. | Profiles; GIFs 05, 07, 08, 12 | Stored model results | Reproducible in principle; model revision unpinned | Retain as GPT-2 Large measurement with provenance caveat |
| C-029 | The two source texts have the same length. | README; LinkedIn copy | 346 vs 334 whitespace words | Approximately, not exactly | Narrow to approximately length-matched |
| C-030 | The two texts differ only by authorship. | README setup | Generation and provenance incomplete | Multiple uncontrolled differences | Withdraw “one variable” wording |
| C-031 | The human sample represents human writing. | Across narrative | One Wikipedia lead | Register and source confound | Narrow to this Wikipedia sample |
| C-032 | The AI sample represents machine writing. | Across narrative | One unnamed model/output | Model and decoding unknown | Narrow to this supplied AI sample |
| C-033 | Surface-tell hits are visible without a model. | Part 9; GIFs 09-10 | Regex matches | Reproducible string matching | Retain; do not equate with authorship |
| C-034 | Epistemic badging makes evidence provenance visible. | All figures | Presentation design | Substantively useful | Retain and strengthen |

## Priority summary

### Immediate blockers

- C-013 through C-018: real-watermark removal verdicts.
- C-019: bigram overlap described as watermark evidence.
- C-021 and C-022: generic detector and “more human” claims.
- C-030: “one variable” matched-pair framing.

### Safe descriptive core

- C-011: Layer A byte identity for the supplied sample.
- C-024: regex count changes, when described strictly as exact-pattern counts.
- C-028: stored GPT-2 measurements, with pinned-method caveats.
- C-033 and C-034: transparent demonstrations and provenance labelling.

### Research hypotheses to carry forward

- C-020: context survival as a predictor.
- C-015 and C-018: attack-family efficiency, retested at equal semantic cost.
- C-021: divergence between watermark evasion and generic detector appearance,
  reformulated with proper distributions and detector baselines.

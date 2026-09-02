# Nominal-threshold false-positive analysis (v1 plan steps A1-A6)

Date: 2 September 2026. Script: `validation/analyse_phase2_nominal_fpr.py` on
`results/phase2-nominal-fpr/null-scores.csv.gz` (10,000 unwatermarked
SmolLM2-135M-Instruct outputs, calibration + confirmation splits pooled; nothing
fitted). Figures in `paper/figures/`, tables in `paper/phase2-nominal-fpr-tables.md`.

## A1. Nominal 1% KGW threshold (z > 2.326), n = 10,000 per cell

- Point estimates above 1% in 20 of 30 key-by-length cells; the exact
  95% CI lies entirely above 1% in 19 cells and entirely below 1% in only
  8 cells.
- Worst key (07): 19.1% at 128, 33.0% at 256,
  48.4% [47.4, 49.3] at 512 tokens.
- Median across keys: 3.5% / 5.0% / 6.9% at 128 / 256 / 512.
- Best key (03): about 0.27% at 512, i.e. the nominal threshold is also
  *conservative* for some keys.
- The 500-output pilot figure (47.0%) is reproduced: 48.4% at n = 10,000.

## A2. SynthID-Text naive-independence reference

There is no nominal z for SynthID's mean-g detector. Using the naive-independence
normal approximation z = (mean_g - 0.5) sqrt(4 * depth * T) with the same 2.326
cutoff, per-cell FPR ranges 0.74% to 1.58% (11 of 30 cells above 1%
by point estimate). Mild over-dispersion, no key-specific bias. Report as a
reference, not as a SynthID failure.

## A3. Shape of the null (Fig 2)

Per-key null z at 512 tokens is approximately normal but shifted and widened:
mean z from -1.96 (key 03) to +2.24 (key 07); SD from
1.26 to 1.58 instead of 1.

## A4. Mechanism (Fig 3): key-specific null green rate

Each detector key induces its own null green-token rate p_k on this model's text,
stable across lengths, ranging 0.205 to 0.302 at 512 tokens against
the assumed gamma = 0.25. The z statistic assumes gamma, so
E[z] = (p_k - gamma) sqrt(T) / sqrt(gamma(1 - gamma)) grows as sqrt(T). Observed
mean z across the 30 cells matches this prediction with r = 0.9999.
A second, smaller effect is over-dispersion: SD(z) rises from about
1.07-1.27 at 128 tokens to 1.26-1.58 at 512, which is why key 06
(p_k = 0.249) still shows 3.7% FPR. A normal with the observed mean and SD
reproduces every cell's FPR within 1.5 percentage points.

Interpretation: the failure is not an implementation defect and not "tiny model
degeneracy" (see A5). It is the standard z-test's i.i.d.-Bernoulli(gamma) null
being wrong for real model text, with the sign and size of the error set by which
frequent (context, token) pairs each key colours green. This is the same
phenomenon Fernandez et al. (2023, "Three Bricks") documented for KGW-style
detectors; here it is quantified per key and per length on one pinned
implementation.

## A5. Repetition is not the driver (Fig 5)

Outputs are repetitive (median repeated-4-gram fraction 0.23), but for the
worst key the correlation between z and repetition is *negative*
(Spearman rho = -0.29): key 07 FPR is 63% in the least repetitive
quartile and 32% in the most repetitive. SelfHash already skips repeated
contexts (`ignore_repeated_ngrams`), which is why eligible positions average
363 of 512. Reviewers' "the model just repeats itself" objection is answered
from data.

## A6. Human-written text shows the same key ranking (Fig 6, Table 2)

Script: `validation/score_phase2_human_null.py` (detector only, no generation)
then `validation/analyse_phase2_human_null.py`. 5,000 de-duplicated human-written
Dolly passages (2,314 `response`, 2,686 `context`; at least 128 tokens; selected
by hashed seed `phase2-human-null-v1`) scored with the same ten frozen KGW keys
at every prefix length each text supports: n = 5,000 / 1,951 / 554 at
128 / 256 / 512 tokens. Table in `paper/phase2-human-null-tables.md`.

- The per-key null green rate p_k on human text ranges 0.216 to 0.280 at 512
  tokens and tracks the model's p_k key for key: Spearman rho = +0.94
  (p = 5e-5), Pearson r = +0.96 over ten keys. Key 07 is the worst key in
  both populations; keys 03 and 04 are the best in both.
- Human-text FPR at the nominal threshold is inflated in the same direction but
  by less: key 07 gives 9.4% / 16.4% / 25.5% at 128 / 256 / 512 tokens on
  human text against 19.1% / 33.0% / 48.4% on SmolLM2 output. 19 of 30
  human cells sit above 1% by point estimate. Key 08 is the one key where human
  text is slightly worse than the model (14.6% vs 12.7% at 512).
- Human text is far less repetitive (median repeated-4-gram fraction 0.016 vs
  0.23 for the model), and the inflation persists, which is a second, independent
  answer to the "the model just repeats itself" objection in A5.

Interpretation: C3 resolves in the "key x token frequency" direction. The
key-specific bias is a property of each key's green list against ordinary
English token statistics, not of SmolLM2's output distribution; the model
amplifies it (wider p_k spread, larger FPR) because its low-entropy output
concentrates mass on the same frequent (context, token) pairs. A practical
corollary: a KGW deployment cannot fix this by calibrating on model text alone,
because human text under the same key inflates too, just less.

Caveats for the manuscript: the 512-token human cell has only 554 texts (371 of
them `context` passages, which are largely Wikipedia-derived), so its intervals
are wide; the comparison length in Fig 6 is 512 because every human cell there
still has at least 200 texts. Dolly categories are not used for any claim.

## Consequences for the manuscript

1. Headline claim moves from the 500-output pilot to n = 10,000 with exact CIs.
2. Fig 1 (dot plot, three lengths) replaces the line chart; Fig 1b shows the three
   runs and makes the point that *which* key inflates is model-specific.
3. New Section: mechanism (p_k, sqrt(T) growth, over-dispersion).
4. The calibration/confirmation gate becomes a short design-margin section.
5. Human-text null (A6) becomes Table 2 + Fig 6 in the mechanism section: the
   key ranking is a property of the key, not the model. D3 is closed.
6. Still open from the plan: only the optional Qwen2.5-3B/7B run (section 6),
   which stays behind D6.

# Phase 2 Official-Reference Cross-check

Status: detection and generation parity gates passed on the canonical variants  
First check date: 27 August 2026  
Remediated: 27 August 2026  
Scope: implementation parity diagnostic; not a benchmark result

> The blocking issue is resolved. Canonical adapters now reproduce both pinned
> reference implementations exactly, and the retained Transformers variants are
> declared and gated separately.

## Decision

The stock Transformers-native KGW SelfHash and SynthID-Text implementations must
not be described as exact reproductions of the watermark authors' reference
implementations. Both diverge at the keyed token-assignment layer.

This does not mean the Transformers implementations are unusable. It means each
must be named and versioned as a separate implementation variant. The project now
carries both: canonical variants that match the authors' code exactly, and the
Transformers variants retained as explicitly labelled secondary conditions.

## Pinned references

| Family | Author-maintained repository | Pinned commit |
|---|---|---|
| KGW | [`jwkirchenbauer/lm-watermarking`](https://github.com/jwkirchenbauer/lm-watermarking) | `82922516930c02f8aa322765defdb5863d07a00e` |
| SynthID-Text | [`google-deepmind/synthid-text`](https://github.com/google-deepmind/synthid-text) | `addb4a158143c7c6851a1308f78b89fceed59683` |

The exact raw-file URLs and SHA-256 digests are frozen in
`configs/phase2-reference-sources.json`. The cross-check downloads those files,
verifies their hashes, and executes the upstream token logic without modifying
it. Narrow stubs replace only optional KGW normalization and SciPy imports that
are not used by the token-scoring path.

## Results

The tables below record the original diagnostic against the *stock* Transformers
implementations, which is what the retained secondary variants still produce. The
canonical variants introduced in remediation reach exact parity on every measure;
see [Remediation](#remediation) below.

### KGW SelfHash

| Check | Result |
|---|---:|
| Records | 30 |
| Eligible-token comparisons | 1,330 |
| Exact records | 0 / 30 |
| Green-hit agreement | 60.23% |
| Mean absolute z-score difference | 1.963 |
| Maximum absolute z-score difference | 4.820 |

Both variants use context width four, green fraction 0.25, and the public key
15485863, and both evaluate the same `anchored_minhash_prf` expression
`min(hash_key * hashint(ngram) * hashint(ngram[-1]))`. The single difference is
the seed of the global permutation table behind `hashint`: the authors fix it at
2971215073, while Transformers derives it from `hashing_key`. Matching public
parameter labels therefore do not produce matching token partitions.

The 60.23% figure is close to the 62.5% expected of two independent green lists
at gamma 0.25, which is the signature of unrelated keying rather than a partial
mismatch.

### SynthID-Text

| Check | Result |
|---|---:|
| Records | 30 |
| G-value bit comparisons | 11,880 |
| Exact g-value records | 0 / 30 |
| G-value agreement | 50.15% |
| Repetition-mask agreement | 100% |
| EOS-mask agreement | 100% |
| Mean absolute mean-score difference | 0.052 |
| Maximum absolute mean-score difference | 0.127 |

The matching masks show that n-gram eligibility semantics are aligned on this
fixture. The keyed g-values are not, for two reasons. The DeepMind reference
seeds every hash with an initialisation vector derived from SHA-256 of the keys,
where Transformers seeds with a literal one; and the reference derives g-values
by iterating the hash twelve times and reading bit 30, where Transformers indexes
a pre-computed random 0/1 sampling table. Neither difference alone accounts for
the divergence, and applying both together reproduces the reference exactly.

The 50.15% bit agreement is chance for binary values, again indicating
independent derivations rather than a near miss.

## Interpretation

The observed 60.2% KGW binary agreement and approximately 50% SynthID bit
agreement are diagnostic descriptions of these 30 stored smoke sequences. They
are not population estimates. Exact parity was the gate criterion, so both gates
fail regardless of sampling uncertainty.

Because primitive assignments differ, generation-output parity was not pursued:
different green lists or g-values necessarily drive different sampling
distributions. Detector thresholds, robustness comparisons, and empirical nulls
must be calibrated separately for each declared variant.

## Remediation

Author-maintained behaviour is now the canonical research condition, with the
Transformers variants retained as explicitly labelled secondary conditions. All
four are selectable through `variants` in the run configuration and are recorded
in the `auxiliary.variant` field of every exported score:

1. `kgw_author_selfhash_v1` — the authors' fixed `hashint` table;
2. `kgw_transformers_selfhash_v5_16` — stock Transformers variant;
3. `synthid_deepmind_hash_v1` — reference SHA-derived IV and iterative g-values;
4. `synthid_transformers_table_v5_16` — stock Transformers variant.

The adapters live in `src/ai_watermarks_phase2/canonical.py`, which enumerates
every difference from the stock implementations. Because the configuration object
builds the processor on both the generation and the detection path, selecting a
variant keeps the two on one primitive.

### Parity after remediation

| Family | Variant | Result |
|---|---|---:|
| KGW SelfHash | `kgw_author_selfhash_v1` | 100% green-hit agreement; 30/30 exact; max abs z-difference 0.000 |
| SynthID-Text | `synthid_deepmind_hash_v1` | 100% g-value agreement; 30/30 exact; max abs score difference 0.000 |

The cross-check now gates each family against the parity its declared variant is
expected to show, so a canonical variant fails on any divergence and a secondary
variant fails if it silently starts matching. Both branches were exercised: the
secondary variants still reproduce 60.23% and 50.15% exactly.

`tests/test_reference_parity.py` provides the same gate on a small deterministic
fixture that needs no model and no smoke run, skipping when the pinned sources
are not cached.

## Generation-path parity

The detection cross-check gates the keyed primitives. It says nothing about
whether generating through these adapters reproduces the reference decoders, so
`validation/phase2_generation_parity.py` gates that separately. Both arms are
driven along one shared token path and handed the same model scores at each step,
because letting each sample its own continuation would compare different contexts
and would also diverge on `torch.multinomial` alone.

Building this check found a second KGW difference that the table swap did not
address. The authors' self-salt rejection sampling uses `tail_rule="fixed_compute"`
and breaks *after* index 40, considering 41 candidates; Transformers loops
`range(40)` and considers 40. This is observable whenever a tie at the top-k
boundary lets a 41st candidate through with a finite score, since
`TopKLogitsWarper` masks `scores < threshold` rather than taking exactly k. The
canonical variant now reproduces the authors' loop.

| Family | Comparison | Result |
|---|---|---:|
| KGW | biased score vector, full vocabulary | 120/120 steps exact; max abs difference 0.000 |
| SynthID | sampling distribution over the reference top-k set | 50/50 matched-candidate steps within 2.4e-07 |

### Known deviation: top-k tie policy

SynthID has a residual difference that is *not* in the watermark. The reference
processor runs its own `torch.topk(k)` internally and takes exactly k candidates,
while the Transformers stack filters upstream with `TopKLogitsWarper` and keeps
ties at the boundary. Over five prompts and 24 steps, 70 of 120 steps saw between
41 and 46 candidates instead of 40.

The two effects separate cleanly:

| Step class | Steps | Max abs probability difference |
|---|---:|---:|
| Same candidate set | 50 | 2.4e-07 (float32 rounding) |
| Boundary tie | 70 | 5.2e-03 |

The tournament is therefore exact, and the deviation is a decoder configuration
difference. The gate is taken on the matched-candidate steps and the tie steps are
reported with their magnitude. Closing it would mean overriding the sampler's
top-k for this variant, which is a decoding decision rather than a watermarking
one and has not been taken.

### Effect on the smoke set

Applying the KGW rejection-sampling fix changed no sampled token in the ten-prompt
smoke run: the bias lands on a rank-40 candidate whose probability stays small, so
the distribution changes at tie steps while the draws did not. The fix matters for
correctness of the declared variant, not for these particular outputs.

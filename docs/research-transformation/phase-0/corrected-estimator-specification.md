# Corrected Estimator Specification

Status: mathematical correction for review, not a replacement detector

## 1. Current implementation

The repository measures set-based word-bigram survival `s` and computes:

```text
p = p_marked * s + gamma * (1 - s)
z_current = (p - gamma) * sqrt(n) / sqrt(gamma * (1 - gamma))
```

Equivalently:

```text
z_current = (p_marked - gamma) * s * sqrt(n)
            / sqrt(gamma * (1 - gamma))
```

where `n` is candidate length. This assumes that fraction `s` of every candidate
token remains watermark-bearing. That is false when tokens are inserted: insertion
can increase `n` without increasing the surviving evidence.

## 2. Length-corrected projection

Let:

- `n` be the number of scored candidate positions;
- `k` be the number of original watermark-bearing token positions whose required
  seeding context and token survived the attack;
- `gamma` be the null green-list probability;
- `p_marked` be the expected green-list probability at a preserved marked position.

The expected number of excess green hits is:

```text
(p_marked - gamma) * k
```

The null standard deviation over the candidate is:

```text
sqrt(n * gamma * (1 - gamma))
```

Therefore the projected expected score is:

```text
z_projection = (p_marked - gamma) * k
               / sqrt(n * gamma * (1 - gamma))
```

For the repository's illustrative values `gamma = 0.5` and
`p_marked = 0.72`:

```text
z_projection = 0.44 * k / sqrt(n)
```

When `k` stays fixed and unrelated text is appended, this decreases as
`1 / sqrt(n)`.

## 3. Approximation using the current proxy

If the existing survival rate `s` is retained temporarily, one can approximate:

```text
k_proxy = s * n_original_context_positions
```

and substitute `k_proxy` into the corrected formula. This repairs the length
dependence, but it does not repair the construct validity of `s`.

The current `bigram_survival` function:

- lowercases and tokenizes with `[A-Za-z0-9]+`;
- converts bigrams to sets, discarding position and repetition;
- counts matching topical or chance bigrams as preserved evidence;
- does not use the watermark scheme's tokenizer or actual context width;
- does not check whether a preserved token was green under a held key.

Accordingly, the corrected value must be called a **projection**, never a measured
detector `z` or a caught/evaded verdict.

## 4. Requirements for a real measurement

A valid experiment must:

1. Generate the original text with a known watermark scheme and held key.
2. Record the scheme tokenizer, context width, `gamma`, watermark strength, and
   decoding configuration.
3. Run the scheme-native keyed detector on the original and attacked text.
4. Count context survival positionally using the scheme's tokens and seeding rule.
5. Distinguish preserved keyed evidence from coincidental lexical overlap.
6. Validate the detector over a large unwatermarked null sample.
7. Report operating characteristics such as TPR at a fixed FPR.

## 5. Phase 0 disposition

- Preserve `modelled_z` only as part of the archived exploratory implementation.
- Do not patch it silently and continue using its existing verdicts.
- Add a new, separately named implementation during Phase 2 after keyed watermark
  ground truth is available.
- Use the corrected projection in Phase 1 only to state the hypothesis and design
  validation tests.

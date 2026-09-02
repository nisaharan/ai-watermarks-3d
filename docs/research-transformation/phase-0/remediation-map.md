# Phase 0 Remediation Map

Status: approved; immediate actions applied on 26 August 2026. See
[remediation-implementation.md](remediation-implementation.md) for the implementation
record and deferred items.

## 1. Recommended version strategy

Preserve the present work as an exploratory baseline rather than silently rewriting
its history:

1. Tag the last pre-transformation commit as the exploratory `v0` baseline.
2. Add a prominent status notice to active public entry points.
3. Move unsupported findings from present-tense results into a clearly labelled
   retrospective or archive.
4. Build the validated experiment through new modules and result artifacts.
5. Replace public findings only after the relevant phase gate passes.

## 2. File-by-file actions

| Artifact | Current risk | Proposed action | Timing |
|---|---|---|---|
| `README.md` | Headline findings exceed evidence | Add exploratory-status banner; replace “found” with “demonstrated on one pair”; remove detector verdicts | After Phase 0 approval |
| `AI-Watermarks-3D.md` Parts 1-7 | Vendor-general and illustrative claims need source verification | Preserve structure; audit citations and scope in Phase 1 | Phase 1 |
| `AI-Watermarks-3D.md` Parts 8-9 | One-pair observations generalized to classes | Rewrite as a worked example; define tokenizers; remove individual-authorship implications | After Phase 0 approval |
| `AI-Watermarks-3D.md` Part 10 | No applied watermark; invalid projected verdicts | Archive as exploratory analysis; replace active section only after real keyed experiments | Phase 2 onward |
| `analyse_removal.py` | Incorrect length dependence and invalid construct | Freeze as legacy; do not silently patch; implement a new keyed evaluation module | Phase 2 |
| `measure_texts.py` | Unpinned model revision and tokenizer mismatch | Pin revision; centralize tokenization and metric definitions | Phase 2-3 |
| `surface_tells.py` | Exact-phrase counts presented as habit detection | Rename outputs as pattern matches; validate against annotation or treat as demonstration | Phase 1-5 |
| `make_removal_gifs.py` | Red/green detector verdicts from modelled proxy | Retire GIF 11 from active evidence; rebuild from keyed measurements | Phase 2-6 |
| `make_real_text_gifs.py` | One-pair generalization and self-selected simulated comparator | Narrow captions; replace with distributional figures later | Phase 3-6 |
| `make_surface_tell_gifs.py` | Counts can be mistaken for authorship evidence | Add instrument limitations on-frame | After Phase 0 approval |
| `article/laundered-text.md` | Strongest unsupported public claims | Mark as exploratory draft or withhold until rewritten from validated findings | Immediate after approval |
| `article/laundered-text-linkedin.md` | Same, with fewer methodological caveats | Withhold or replace with a project-reframing post | Immediate after approval |
| `article/linkedin-post.md` | Publishes modelled z as an evasion verdict | Withhold current versions | Immediate after approval |
| Existing GIFs 01-04 | Illustrative ranges may lack source mapping | Retain only as explicitly author-selected teaching illustrations until verified | Phase 1 |
| Existing GIFs 05-10, 12 | Descriptive but overgeneralized | Retain as one-pair visuals with revised captions or archive | After approval |
| `example/` | Missing full machine-generation provenance | Preserve; add legacy manifest stating what is known and unknown | After approval |

## 3. Immediate documentation patch proposed

If Phase 0 is approved, the first patch should add this notice to the README and
long-form entry point:

> **Research status:** This version is an exploratory demonstration built from one
> human and one AI sample. It does not measure a real keyed watermark. The published
> bigram-survival z-scores are hypothetical projections and must not be interpreted
> as detector outcomes. A validated research redesign is in progress.

This notice reduces misinterpretation while preserving the current materials for
traceability.

## 4. Metric standardization decisions

Before new results are produced:

- define `word`, `token`, `sentence`, and `paragraph` in one metric specification;
- use scheme-native tokens for watermark context and detection;
- use a separate documented word tokenizer for prose statistics;
- attach metric version identifiers to output tables;
- rename `facts_retained` to `entity_number_retention_proxy` unless a real factuality
  system replaces it;
- rename Tier 3 counts to `exact_pattern_hits`;
- prohibit `caught`, `evaded`, or `detected` for modelled projections.

## 5. Phase 1 handoff requirements

Phase 1 should not begin as a general reading exercise. It must answer:

1. Which prior papers already model context or token survival under attacks?
2. For which watermark families is context survival theoretically meaningful?
3. Which open implementations support keyed, reproducible evaluation?
4. Which attacks and detector baselines are expected by current reviewers?
5. What evaluation metrics and false-positive operating points are standard?
6. What fairness findings require direct replication or only citation?

The output should be a source-verified novelty matrix and an updated research
protocol, followed by an explicit stop/go decision.

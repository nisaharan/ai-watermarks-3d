# Metric Specification

Status: Phase 0 definitions for legacy interpretation and future implementation

## Purpose

This document prevents the same metric name from referring to different calculations
and separates prose measurements from watermark-scheme measurements.

## Evidence namespaces

Future machine-readable results should prefix or group metrics by purpose:

- `watermark.*`: scheme-native keyed measurements.
- `context.*`: positional context-survival measurements.
- `style.*`: descriptive prose statistics.
- `quality.*`: semantic, factual, grammatical, and human-review measurements.
- `detector.*`: named generic AI-text detector outputs.
- `legacy.*`: retained exploratory fields that are not active evidence.

## Legacy metric definitions

| Current field | Actual definition | Valid interpretation | Required future name |
|---|---|---|---|
| `n_words` in `profiles.json` | GPT-2-offset word assembly, excluding the first unscored token | Model-pipeline word count | `style.gpt2_assembled_word_count` |
| `n_words` in removal analysis | Python whitespace split | Whitespace-delimited count | `style.whitespace_word_count` |
| `ttr` in `profiles.json` | Unique normalized GPT-2-assembled words divided by count | Sample lexical ratio under this tokenizer | `style.ttr_gpt2_assembled` |
| `ttr` in removal analysis | Unique `[A-Za-z0-9]+` tokens divided by count | ASCII-regex lexical ratio | `legacy.ttr_ascii_regex` |
| `sent_cv` | Population standard deviation of whitespace word counts per regex-split sentence, divided by mean | Descriptive sentence-length variation | `style.sentence_length_cv` |
| `punct_variety` | Count of distinct characters matching the configured punctuation regex | Character-set variety | `style.punctuation_character_variety` |
| `bigram_survival` | Recall of unique lowercased ASCII-regex word-bigram types from the original in the candidate | Set-overlap proxy only | `legacy.unique_word_bigram_recall` |
| `modelled_z` | Legacy formula applying assumed marked rate to the candidate using bigram recall | Invalid as detector score | `legacy.invalid_modelled_z` |
| `modelled_z_detected` | Threshold at 4 over legacy `modelled_z` | Withdrawn | Remove from active schema |
| `facts_retained` | Presence rate for automatically selected numbers and non-initial capitalized words | Entity/number presence proxy | `quality.entity_number_retention_proxy` |
| `tells_total` | Exact regex matches after within-category overlap removal | Pattern-match count | `style.exact_pattern_hits` |

## Canonical prose units for new work

- **Character:** Unicode code point after a declared normalization policy.
- **Whitespace word:** maximal non-whitespace span, used only for transparent length
  reporting.
- **Prose word token:** produced by one documented Unicode-aware tokenizer selected
  before the corpus is frozen.
- **Model token:** token from the explicitly versioned model tokenizer.
- **Watermark token:** token from the scheme-native tokenizer used for seeding and
  detection.
- **Sentence:** output of a versioned sentence segmenter, with language declared.
- **Paragraph:** non-empty block separated by one or more blank lines.

These units are not interchangeable. Every table must state the relevant unit.

## Watermark measurements

A field may use the `watermark.*` namespace only when it is computed by a keyed,
validated scheme implementation. Minimum fields:

- `watermark.scheme_id`;
- `watermark.config_id`;
- `watermark.key_id` without exposing secret material;
- `watermark.tokenizer_revision`;
- `watermark.context_width`;
- `watermark.scored_positions`;
- `watermark.native_score`;
- `watermark.p_value` where defined;
- `watermark.threshold` and associated false-positive operating point.

## Context-survival measurements

Context survival must be positional and scheme-aware:

- use the watermark tokenizer;
- use the scheme's actual context width and seeding rule;
- count repeated contexts at their positions rather than collapsing to a set;
- distinguish preserved marked positions from coincidental surface matches;
- report surviving count and candidate scored length separately.

The Phase 0 length-corrected projection is a design aid, not an active metric.

## Quality measurements

No single proxy may be labelled “facts retained” or “quality.” Report components:

- semantic preservation;
- entailment and contradiction;
- entity and number retention;
- factual verification where references permit;
- grammatical/readability score;
- blinded human-review results;
- output length and computational cost.

## Reporting precision

- Show counts as integers.
- Show rates with denominators and no more than three meaningful decimals.
- Show effect estimates with confidence intervals.
- Show detector results at a declared FPR.
- Do not use `caught`, `evaded`, or `detected` for modelled or simulated values.

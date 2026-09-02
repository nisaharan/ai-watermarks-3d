# Remediation Implementation Record

Implementation date: 26 August 2026  
Status: immediate Phase 0 remediation complete

## Applied

### Repository status and discoverability

- Added `RESEARCH_STATUS.md` as the canonical status statement.
- Added prominent exploratory-status notices to the README and long-form document.
- Linked the status, validation report, and transformation plan from active entry
  points.

### Claim correction

- Reframed the README findings as sample-level observations.
- Removed caught/evaded verdicts and the invalid z-score table from the active README.
- Identified GIF 11 as a withdrawn legacy visual rather than active evidence.
- Reframed metric overshoot relative to one Wikipedia reference instead of “more
  human than the human.”
- Narrowed sentence, vocabulary, and surprisal statements to the supplied pair.
- Removed “one variable,” “nobody does that by accident,” and comparable causal or
  class-level wording from active explanatory sections.

### Long-form boundary

- Relabelled Part 8 as an exploratory worked example.
- Reframed Tier 3 as exact-pattern matching rather than habit or authorship detection.
- Collapsed Part 10 as withdrawn historical analysis with a prominent invalidity
  notice and a link to the corrected estimator specification.

### Public-content controls

- Marked all existing article and LinkedIn drafts as archived and not for publication.
- Added an explicit `--allow-archived` gate to the HTML builder so an archived draft
  cannot be rendered accidentally.

### Code and output labels

- Marked `analyse_removal.py` as a legacy exploratory implementation.
- Added a runtime warning and neutralized its printed threshold summary.
- Updated the stored removal-analysis JSON with a withdrawn-evidence status.
- Reworded GIF generators so future renders use sample-level, non-detector language.
- Reworded the surface scanner as exact-pattern matching.
- Reworded simulated GIFs as author-selected illustrations rather than published
  typical distributions.

### Provenance and metrics

- Added `example/PROVENANCE.md` documenting known and missing lineage.
- Added the project metric specification with explicit namespaces and canonical units.
- Recorded the two conflicting legacy tokenization/TTR definitions.
- Reserved keyed `watermark.*` metrics for validated scheme-native measurements.

## Preserved for traceability

- Source texts and rewrite outputs.
- Stored GPT-2 measurements.
- Legacy `modelled_z` fields and the historical GIF 11 file.
- Withdrawn prose inside the collapsed historical Part 10.
- Archived public article drafts.

Preservation does not make these items active evidence.

## Deliberately deferred

- Tagging or committing an exploratory `v0` release: requires an explicit git-release
  decision.
- Replacing GIF 11 with a measured figure: blocked until keyed ground truth exists.
- Pinning new model and tokenizer revisions: belongs to the Phase 2 environment.
- Replacing exact-pattern counts with annotated or model-assisted evaluation: belongs
  to Phase 5.
- Rewriting public articles from validated findings: blocked until the relevant
  experiment gate passes.
- Literature and vendor-claim verification: Phase 1.

## Acceptance condition

The immediate remediation is successful if a new reader can distinguish:

1. sample-level descriptive evidence;
2. withdrawn legacy projections;
3. illustrations and mechanisms;
4. hypotheses awaiting keyed experiments.

# Paper package

The manuscript and everything generated for it. All of it is built from stored
detector scores by fixed scripts; no step regenerates text.

The manuscript is set two-column in the IEEEtran conference class, with STIX
Two for both body text and figures.

## Contents

1. `arxiv/main.tex` and `arxiv/references.bib`: the manuscript.
2. `arxiv/tables/`: generated LaTeX fragments (Table 1 nominal false-positive
   rates, Table 2 the human-text null, Table A1 the sixty calibrated cells).
   Generated, so do not edit by hand.
3. `figures/`: generated vector PDFs, numbered as they appear in the paper.
   `figure-captions.md` records which script owns each one, and
   `../validation/figstyle.py` holds the shared style.
4. `phase2-nominal-fpr-tables.md`, `phase2-human-null-tables.md`,
   `phase2-appendix-table-a1.md`: Markdown twins of the manuscript tables, for
   reading outside LaTeX.
5. `release-and-license-audit.md`: the release boundary and licence checks.
6. `when-nominal-false-positive-rates-fail.pdf`: the current build.

The analysis record behind Sections 4 and 5, with every number quoted in the
paper, is `../docs/research-transformation/phase-2/nominal-fpr-report.md`.

## Rebuild

From the repository root:

```bash
python validation/analyse_phase2_nominal_fpr.py         # Figures 1-5, Table 1
python validation/analyse_phase2_human_null.py          # Figure 6, Table 2
python validation/build_phase2_publication_figures.py   # Figure 7
python validation/build_phase2_v1_latex_tables.py       # LaTeX tables
cd paper/arxiv && tectonic main.tex                     # or latexmk -pdf
```

The human-text null reads `results/phase2-human-null/human-scores.csv.gz`,
which is in the repository. Regenerating that file from scratch instead needs
`validation/score_phase2_human_null.py` and about 25 minutes of detector-only
scoring; it loads no model weights.

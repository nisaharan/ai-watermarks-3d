# Figure inventory (generated figures, v1 manuscript)

Captions live with the figures in `arxiv/main.tex`; this file records where each
one comes from so a stale figure can be traced to the script that owns it. All
figures are vector PDF authored at the document text width (6.27 in) and included
at `width=\textwidth`, so they are placed at scale 1.0 and their type is the size
it claims to be. Shared style: `../validation/figstyle.py`.

| Figure | File | Built by |
|---|---|---|
| 1 | `figures/fig1-nominal-fpr-by-key.pdf` | `validation/analyse_phase2_nominal_fpr.py` |
| 2 | `figures/fig2-nominal-fpr-three-runs.pdf` | `validation/analyse_phase2_nominal_fpr.py` |
| 3 | `figures/fig3-z-distributions.pdf` | `validation/analyse_phase2_nominal_fpr.py` |
| 4 | `figures/fig4-key-green-rate-mechanism.pdf` | `validation/analyse_phase2_nominal_fpr.py` |
| 5 | `figures/fig5-z-vs-repetition.pdf` | `validation/analyse_phase2_nominal_fpr.py` |
| 6 | `figures/fig6-human-vs-model-null.pdf` | `validation/analyse_phase2_human_null.py` |
| 7 | `figures/fig7-design-margin.pdf` | `validation/build_phase2_publication_figures.py` |

Figures 1 to 6 are computed from stored detector scores. Figure 7 is the only one
whose numbers come from a report artifact,
`reports/phase2-confirmation-gate/artifact.json`.

## Style rules the figures follow

* Colour encodes something. Prefix length is an ordinal one-hue ramp, light to
  dark. Run and population identity take the categorical slots in fixed order.
  Which side of the assumed green-list fraction a key falls on takes the
  diverging pair. The palettes were checked with a validator, not by eye.
* Every series also carries a marker or line style, so the figures survive
  greyscale printing and colour-vision deficiency. This was checked by rendering
  each figure to greyscale.
* Text is Computer Modern, the same family as the manuscript body, with Greek
  and maths written as mathtext so they match the surrounding text.
* Fonts embed as Type 42, not Type 3.
* Dense layers are rasterised individually; axes and all text stay vector.

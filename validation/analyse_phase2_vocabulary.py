"""Does a larger vocabulary dampen the key effect? Same text, two tokenizers.

The paper shows that each detector key induces its own null green rate on real
text, and that a Qwen2.5 run fails different keys than the SmolLM2 run. That
comparison changes the model and the tokenizer at once, so it cannot say which
one decides. A natural objection is also that a bigger vocabulary might average
the effect away.

This script separates the two. It scores the identical human-written passages
under two vocabularies, SmolLM2-135M at about 49k tokens and Qwen2.5-0.5B at
about 152k, holding the ten KGW hashing keys, the watermark parameters and the
text fixed. Whatever differs is the vocabulary alone. No text is generated and
no model weights are loaded.

Inputs:
    results/phase2-human-null/human-scores.csv[.gz], human-texts.csv
    results/phase2-human-null-qwen/human-scores.csv[.gz], human-texts.csv
Outputs:
    results/phase2-human-null-qwen/vocabulary-cells.csv
    results/phase2-human-null-qwen/vocabulary-summary.json
    paper/figures/fig9-vocabulary.pdf
    paper/phase2-vocabulary-tables.md

Usage (repo root): python validation/analyse_phase2_vocabulary.py
"""

from __future__ import annotations

import json
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figstyle as fs

ROOT = os.environ.get("AIWM_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SMOL = os.path.join(ROOT, "results", "phase2-human-null")
QWEN = os.path.join(ROOT, "results", "phase2-human-null-qwen")
FIG = os.path.join(ROOT, "paper", "figures")
Z = stats.norm.ppf(0.99)
GAMMA = 0.25
LENGTHS = (128, 256, 512)
VOCAB = {"SmolLM2": "SmolLM2-135M, 49k tokens", "Qwen2.5": "Qwen2.5-0.5B, 152k tokens"}


def cp(x, n, conf=0.95):
    a = 1 - conf
    lo = 0.0 if x == 0 else stats.beta.ppf(a / 2, x, n - x + 1)
    hi = 1.0 if x == n else stats.beta.ppf(1 - a / 2, x + 1, n - x)
    return float(lo), float(hi)


def load(folder: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    p = os.path.join(folder, "human-scores.csv.gz")
    if not os.path.exists(p):
        p = os.path.join(folder, "human-scores.csv")
    if not os.path.exists(p):
        raise SystemExit(f"missing scores under {folder}")
    scores = pd.read_csv(p)
    texts = pd.read_csv(os.path.join(folder, "human-texts.csv"))
    return scores[scores.scheme == "kgw"], texts


def cells(scores: pd.DataFrame, label: str) -> pd.DataFrame:
    rows = []
    for (key, L), g in scores.groupby(["key_id", "length"]):
        n, x = len(g), int((g.value > Z).sum())
        lo, hi = cp(x, n)
        green, elig = int(g.green_tokens.sum()), int(g.eligible_positions.sum())
        plo, phi = cp(green, elig)
        rows.append(dict(vocabulary=label, key_id=key, length=int(L), n=n, exceed=x,
                         fpr=x / n, fpr_lo=lo, fpr_hi=hi,
                         p_k=green / elig, p_lo=plo, p_hi=phi,
                         mean_z=g.value.mean(), sd_z=g.value.std(ddof=1)))
    return pd.DataFrame(rows)


def figure(c: pd.DataFrame, L: int, rho: float, out: str) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(fs.TEXTWIDTH, 2.95))
    keys = sorted(c.key_id.unique())
    x = np.arange(len(keys))

    # (a) the spread of p_k under each vocabulary, on identical text
    ax = axes[0]
    for i, vocab in enumerate(VOCAB):
        g = c[(c.vocabulary == vocab) & (c.length == L)].set_index("key_id").loc[keys]
        ax.vlines(x + (i - 0.5) * 0.34, g.p_lo, g.p_hi, color=fs.CAT[i], linewidth=1.1)
        ax.scatter(x + (i - 0.5) * 0.34, g.p_k, s=20, color=fs.CAT[i], marker=fs.CAT_MARKER[i],
                   zorder=3, edgecolor="white", linewidth=0.5, label=VOCAB[vocab])
    ax.axhline(GAMMA, color=fs.INK, linewidth=0.9, zorder=2)
    ax.text(len(keys) - 0.45, GAMMA + 0.0015, "assumed $\\gamma = 0.25$", ha="right",
            va="bottom", fontsize=7.2, color=fs.INK)
    ax.set_xticks(x)
    ax.set_xticklabels([k.replace("kgw-", "") for k in keys])
    ax.set_xlim(-0.6, len(keys) - 0.4)
    ax.set_xlabel("Frozen detector key")
    ax.set_ylabel(f"Null green rate $p_k$ ({L} tokens)")
    ax.legend(loc="upper left", fontsize=7)
    fs.title(ax, "(a)  Same passages, two vocabularies")
    fs.style(ax)

    # (b) does the ranking transfer?
    ax = axes[1]
    a = c[(c.vocabulary == "SmolLM2") & (c.length == L)].set_index("key_id").loc[keys]
    b = c[(c.vocabulary == "Qwen2.5") & (c.length == L)].set_index("key_id").loc[keys]
    lim = [min(a.p_lo.min(), b.p_lo.min()) - 0.006, max(a.p_hi.max(), b.p_hi.max()) + 0.006]
    ax.plot(lim, lim, color=fs.MUTED, linewidth=0.8, zorder=2)
    ax.axhline(GAMMA, color=fs.INK, linewidth=0.7, zorder=1)
    ax.axvline(GAMMA, color=fs.INK, linewidth=0.7, zorder=1)
    for key in keys:
        ra, rb = a.loc[key], b.loc[key]
        col = fs.POS if ra.p_k > GAMMA else fs.NEG
        ax.plot([ra.p_lo, ra.p_hi], [rb.p_k, rb.p_k], color=col, linewidth=0.9, zorder=3)
        ax.plot([ra.p_k, ra.p_k], [rb.p_lo, rb.p_hi], color=col, linewidth=0.9, zorder=3)
        ax.scatter([ra.p_k], [rb.p_k], s=20, color=col, zorder=4, edgecolor="white",
                   linewidth=0.5, marker="o" if col == fs.POS else "s")
        ax.annotate(key.replace("kgw-", ""), (ra.p_k, rb.p_k), xytext=(4, 3.5),
                    textcoords="offset points", fontsize=6.8, color=fs.MUTED)
    ax.set_xlim(*lim)
    ax.set_ylim(*lim)
    ax.set_xlabel("$p_k$ under the SmolLM2 vocabulary")
    ax.set_ylabel("$p_k$ under the Qwen2.5 vocabulary")
    fs.title(ax, f"(b)  The ranking does not transfer, $\\rho = {rho:+.2f}$")
    fs.style(ax, grid="both")
    fig.tight_layout()
    fs.save(fig, out)


def main() -> int:
    s_scores, s_texts = load(SMOL)
    q_scores, q_texts = load(QWEN)

    # the two runs select passages by the same hashed rank, but eligibility
    # depends on the tokenizer, so restrict to the passages both scored
    key_cols = ["source_row", "field"]
    shared = s_texts.merge(q_texts, on=key_cols, suffixes=("_s", "_q"))[
        key_cols + ["prompt_id_s", "prompt_id_q"]]
    s_scores = s_scores[s_scores.prompt_id.isin(set(shared.prompt_id_s))]
    q_scores = q_scores[q_scores.prompt_id.isin(set(shared.prompt_id_q))]

    c = pd.concat([cells(s_scores, "SmolLM2"), cells(q_scores, "Qwen2.5")], ignore_index=True)
    c.to_csv(os.path.join(QWEN, "vocabulary-cells.csv"), index=False)

    L = max(l for l in LENGTHS if c[c.length == l].n.min() >= 200)
    a = c[(c.vocabulary == "SmolLM2") & (c.length == L)].set_index("key_id")
    b = c[(c.vocabulary == "Qwen2.5") & (c.length == L)].set_index("key_id")
    keys = sorted(set(a.index) & set(b.index))
    rho, pval = stats.spearmanr(a.loc[keys].p_k, b.loc[keys].p_k)
    figure(c, L, float(rho), os.path.join(FIG, "fig9-vocabulary.pdf"))

    def spread(vocab, length):
        g = c[(c.vocabulary == vocab) & (c.length == length)]
        return [float(g.p_k.min()), float(g.p_k.max())]

    summary = {
        "scope": ("identical human passages scored under two vocabularies with the same ten "
                  "KGW keys and watermark parameters; detector-only, nothing generated"),
        "shared_passages": int(len(shared)),
        "comparison_length": int(L),
        "n_by_length": {int(l): int(c[c.length == l].n.min()) for l in LENGTHS
                        if (c.length == l).any()},
        "p_k_range": {v: {int(l): spread(v, l) for l in LENGTHS if (c.length == l).any()}
                      for v in VOCAB},
        "p_k_spread_width": {v: {int(l): round(spread(v, l)[1] - spread(v, l)[0], 4)
                                 for l in LENGTHS if (c.length == l).any()} for v in VOCAB},
        "spearman_p_k_across_vocabularies": float(rho),
        "spearman_p": float(pval),
        "worst_key": {v: str(c[(c.vocabulary == v) & (c.length == L)].set_index("key_id").p_k.idxmax())
                      for v in VOCAB},
        "fpr_range_at_nominal": {v: [float(c[(c.vocabulary == v) & (c.length == L)].fpr.min()),
                                     float(c[(c.vocabulary == v) & (c.length == L)].fpr.max())]
                                 for v in VOCAB},
        "cells_above_1pct": {v: int((c[c.vocabulary == v].fpr > 0.01).sum()) for v in VOCAB},
    }
    json.dump(summary, open(os.path.join(QWEN, "vocabulary-summary.json"), "w"), indent=2)

    lines = ["# Vocabulary comparison on identical human text (generated)\n",
             "Source: `validation/analyse_phase2_vocabulary.py`. The same human-written Dolly",
             "passages scored under two tokenizers with the same ten KGW hashing keys and the",
             "same watermark parameters. Detector-only; no text generated and no weights loaded.",
             f"Restricted to the {len(shared):,} passages both runs scored.\n",
             "| Vocabulary | Length | n | $p_k$ range | FPR range at nominal $z>2.326$ |",
             "|---|---:|---:|---:|---:|"]
    for v in VOCAB:
        for L2 in LENGTHS:
            g = c[(c.vocabulary == v) & (c.length == L2)]
            if g.empty:
                continue
            lines.append(f"| {v} | {L2} | {int(g.n.min()):,} | {g.p_k.min():.3f}-{g.p_k.max():.3f} | "
                         f"{g.fpr.min()*100:.2f}%-{g.fpr.max()*100:.2f}% |")
    lines.append(f"\nSpearman correlation of $p_k$ across the two vocabularies at {L} tokens: "
                 f"{rho:+.2f} (p = {pval:.2g}) over ten keys.")
    open(os.path.join(ROOT, "paper", "phase2-vocabulary-tables.md"), "w").write("\n".join(lines) + "\n")

    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

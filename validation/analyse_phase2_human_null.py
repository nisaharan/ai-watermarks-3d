"""A6 analysis: human-written text vs model-generated null under the same keys.

Inputs:
    results/phase2-human-null/human-scores.csv[.gz] (from score_phase2_human_null.py)
    results/phase2-nominal-fpr/null-scores.csv[.gz] (model null, 10,000 outputs)
Outputs:
    results/phase2-human-null/human-vs-model-cells.csv
    results/phase2-human-null/human-vs-model-summary.json
    paper/phase2-human-null-tables.md                (Table 2)
    paper/figures/fig6-human-vs-model-null.pdf

Question answered: is the key-specific null green rate p_k a property of the key
x vocabulary (then human text shows the same key ranking) or of the generating
model's output distribution (then it does not)?
"""

from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figstyle as fs

ROOT = os.environ.get("AIWM_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HUM = os.path.join(ROOT, "results", "phase2-human-null")
MOD = os.path.join(ROOT, "results", "phase2-nominal-fpr")
FIG = os.path.join(ROOT, "paper", "figures")
Z = stats.norm.ppf(0.99)
LENGTHS = (128, 256, 512)
GAMMA = 0.25


def cp(x, n, conf=0.95):
    a = 1 - conf
    lo = 0.0 if x == 0 else stats.beta.ppf(a / 2, x, n - x + 1)
    hi = 1.0 if x == n else stats.beta.ppf(1 - a / 2, x + 1, n - x)
    return lo, hi


def cells(df, label):
    k = df[df.scheme == "kgw"]
    rows = []
    for (key, L), g in k.groupby(["key_id", "length"]):
        n, x = len(g), int((g.value > Z).sum())
        lo, hi = cp(x, n)
        green, elig = int(g.green_tokens.sum()), int(g.eligible_positions.sum())
        plo, phi = cp(green, elig)
        rows.append(dict(population=label, key_id=key, length=L, n=n, exceed=x, fpr=x / n,
                         ci_lo=lo, ci_hi=hi, p_k=green / elig, p_lo=plo, p_hi=phi,
                         mean_z=g.value.mean(), sd_z=g.value.std(ddof=1),
                         mean_eligible=g.eligible_positions.mean()))
    return pd.DataFrame(rows)


def md_table(c, summary, path):
    lines = ["# Human-text null tables (generated; v1 plan Table 2)\n",
             "Source: `validation/analyse_phase2_human_null.py`. Human rows: de-duplicated",
             "Databricks Dolly `response` and `context` fields (human-written), scored with the",
             "same ten frozen canonical KGW SelfHash keys as the model null; each text is scored",
             "at every prefix length it supports, so n falls with length. Model rows: 10,000",
             "unwatermarked SmolLM2-135M-Instruct outputs. FPR is the empirical rate at the",
             "nominal one-sided 1% threshold (z > 2.326) with exact two-sided 95% Clopper-Pearson",
             "intervals; p_k is the pooled null green-token rate for the key (gamma = 0.25).\n"]
    for L in LENGTHS:
        h = c[(c.population == "human") & (c.length == L)].set_index("key_id")
        m = c[(c.population == "model") & (c.length == L)].set_index("key_id")
        if h.empty:
            continue
        lines.append(f"\n## {L} tokens (human n = {int(h.n.iloc[0]):,}; model n = {int(m.n.iloc[0]):,})\n")
        lines.append("| Key | Human FPR | Model FPR | Human p_k | Model p_k |")
        lines.append("|---|---:|---:|---:|---:|")
        for key in sorted(set(h.index) & set(m.index)):
            a, b = h.loc[key], m.loc[key]
            lines.append(f"| {key} | {a.fpr*100:.2f}% [{a.ci_lo*100:.2f}, {a.ci_hi*100:.2f}]"
                         f" | {b.fpr*100:.2f}% [{b.ci_lo*100:.2f}, {b.ci_hi*100:.2f}]"
                         f" | {a.p_k:.3f} | {b.p_k:.3f} |")
    L = summary["comparison_length"]
    lines.append(f"\nKey-level agreement at {L} tokens: Spearman rho = "
                 f"{summary['spearman_p_k_human_vs_model']:+.2f} (p = {summary['spearman_p']:.1e}), "
                 f"Pearson r = {summary['pearson_p_k_human_vs_model']:+.2f} over ten keys. "
                 f"Worst key on human text: {summary['worst_key_human']}; on model text: "
                 f"{summary['worst_key_model']}.")
    open(path, "w").write("\n".join(lines) + "\n")


def main():
    hp = os.path.join(HUM, "human-scores.csv.gz")
    if not os.path.exists(hp):
        hp = os.path.join(HUM, "human-scores.csv")
    if not os.path.exists(hp):
        print("human-scores.csv[.gz] not found; run validation/score_phase2_human_null.py first",
              file=sys.stderr)
        return 1
    human = pd.read_csv(hp)
    mp = os.path.join(MOD, "null-scores.csv.gz")
    model = pd.read_csv(mp if os.path.exists(mp) else mp[:-3])
    c = pd.concat([cells(model, "model"), cells(human, "human")], ignore_index=True)
    c.to_csv(os.path.join(HUM, "human-vs-model-cells.csv"), index=False)

    # key-level comparison at the longest length both populations support
    L = max(l for l in LENGTHS if (c[(c.population == "human") & (c.length == l)].n.min() or 0) >= 200) \
        if (c.population == "human").any() else 512
    h = c[(c.population == "human") & (c.length == L)].set_index("key_id")
    m = c[(c.population == "model") & (c.length == L)].set_index("key_id")
    keys = sorted(set(h.index) & set(m.index))
    rho, p = stats.spearmanr(h.loc[keys].p_k, m.loc[keys].p_k)
    r = float(np.corrcoef(h.loc[keys].p_k, m.loc[keys].p_k)[0, 1])
    summary = {
        "comparison_length": int(L),
        "human_n_by_length": {int(l): int(c[(c.population == "human") & (c.length == l)].n.min())
                              for l in LENGTHS if ((c.population == "human") & (c.length == l)).any()},
        "spearman_p_k_human_vs_model": float(rho), "spearman_p": float(p),
        "pearson_p_k_human_vs_model": r,
        "human_p_k_range": [float(h.loc[keys].p_k.min()), float(h.loc[keys].p_k.max())],
        "model_p_k_range": [float(m.loc[keys].p_k.min()), float(m.loc[keys].p_k.max())],
        "human_fpr_range": [float(h.loc[keys].fpr.min()), float(h.loc[keys].fpr.max())],
        "model_fpr_range": [float(m.loc[keys].fpr.min()), float(m.loc[keys].fpr.max())],
        "human_cells_above_1pct": int((c[c.population == "human"].fpr > 0.01).sum()),
        "human_cells_total": int((c.population == "human").sum()),
        "worst_key_human": str(h.loc[keys].fpr.idxmax()), "worst_key_model": str(m.loc[keys].fpr.idxmax()),
    }
    json.dump(summary, open(os.path.join(HUM, "human-vs-model-summary.json"), "w"), indent=2)
    md_table(c, summary, os.path.join(ROOT, "paper", "phase2-human-null-tables.md"))

    fig, axes = plt.subplots(1, 2, figsize=(fs.TEXTWIDTH, 2.95))

    # (a) the same keys, two populations. Identity is the job, so two
    # categorical slots with their own markers; log y for a 50-fold spread.
    ax = axes[0]
    x = np.arange(len(keys))
    for i, (pop, off, lab) in enumerate((
            ("model", -0.17, f"SmolLM2 output, $n = {int(m.loc[keys].n.iloc[0]):,}$"),
            ("human", 0.17, f"human Dolly text, $n = {int(h.loc[keys].n.iloc[0]):,}$"))):
        g = (m if pop == "model" else h).loc[keys]
        ax.vlines(x + off, g.ci_lo * 100, g.ci_hi * 100, color=fs.CAT[i], linewidth=1.1)
        ax.scatter(x + off, g.fpr * 100, s=20, color=fs.CAT[i], marker=fs.CAT_MARKER[i],
                   zorder=3, edgecolor="white", linewidth=0.5, label=lab)
    ax.axhline(1.0, color=fs.INK, linestyle=(0, (2.5, 2.5)), linewidth=0.9)
    ax.text(len(keys) - 0.45, 1.1, "nominal 1%", ha="right", va="bottom",
            fontsize=7.2, color=fs.INK)
    ax.set_xticks(x)
    ax.set_xticklabels([k.replace("kgw-", "") for k in keys])
    ax.set_xlim(-0.6, len(keys) - 0.4)
    ax.set_xlabel("Frozen detector key")
    ax.set_ylabel(f"False-positive rate at {L} tokens (%)")
    fs.percent_log(ax, [0.2, 0.5, 1, 2, 5, 10, 20, 50])
    ax.set_ylim(0.08, 130)
    ax.legend(loc="upper right", ncol=1, fontsize=7.2, borderpad=0.2)
    fs.title(ax, "(a)  The same keys on human-written text")
    fs.style(ax)

    # (b) the ranking itself. One series, so colour is free to carry which side
    # of gamma the key falls on, the same encoding as the mechanism figure.
    ax = axes[1]
    hk, mk = h.loc[keys], m.loc[keys]
    cols = [fs.POS if p > GAMMA else fs.NEG for p in mk.p_k]
    lim = [min(mk.p_lo.min(), hk.p_lo.min()) - 0.006,
           max(mk.p_hi.max(), hk.p_hi.max()) + 0.006]
    ax.plot(lim, lim, color=fs.MUTED, linewidth=0.8, zorder=2)
    ax.axhline(GAMMA, color=fs.INK, linewidth=0.7, zorder=1)
    ax.axvline(GAMMA, color=fs.INK, linewidth=0.7, zorder=1)
    for key, c in zip(keys, cols):
        a_, b_ = mk.loc[key], hk.loc[key]
        ax.plot([a_.p_lo, a_.p_hi], [b_.p_k, b_.p_k], color=c, linewidth=0.9, zorder=3)
        ax.plot([a_.p_k, a_.p_k], [b_.p_lo, b_.p_hi], color=c, linewidth=0.9, zorder=3)
        ax.scatter([a_.p_k], [b_.p_k], s=20, color=c, zorder=4, edgecolor="white",
                   linewidth=0.5, marker="o" if c == fs.POS else "s")
        ax.annotate(key.replace("kgw-", ""), (a_.p_k, b_.p_k), xytext=(4, 3.5),
                    textcoords="offset points", fontsize=6.8, color=fs.MUTED)
    ax.set_xlim(*lim)
    ax.set_ylim(*lim)
    ax.set_xlabel("Null green rate $p_k$ on SmolLM2 output")
    ax.set_ylabel("Null green rate $p_k$ on human text")
    fs.title(ax, f"(b)  Key ranking agrees, $\\rho = {rho:+.2f}$")
    fs.style(ax, grid="both")

    fig.tight_layout()
    fs.save(fig, os.path.join(FIG, "fig6-human-vs-model-null.pdf"))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Nominal-threshold false-positive analysis on the full 10,000-output null.

Inputs (produced by ``validation/extract_phase2_null_scores.py``):
    results/phase2-nominal-fpr/null-scores.csv[.gz]
    results/phase2-nominal-fpr/null-texts.csv
    results/phase2-variance-pilot/scores.csv          (SmolLM2, n=500, development pilot)
    results/phase2-variance-replication/scores.csv    (Qwen2.5-0.5B, n=104)

Outputs:
    results/phase2-nominal-fpr/nominal-fpr-cells.csv     one row per scheme x key x length
    results/phase2-nominal-fpr/nominal-fpr-summary.json  headline numbers used in the paper
    results/phase2-nominal-fpr/repetition-length.json    A5 numbers
    paper/figures/fig1-nominal-fpr-by-key.pdf            dot plot, 3 lengths, exact CIs
    paper/figures/fig2-nominal-fpr-three-runs.pdf        n=10,000 vs pilot vs Qwen at 512
    paper/figures/fig3-z-distributions.pdf               per-key z density vs N(0,1)
    paper/figures/fig4-key-green-rate-mechanism.pdf      A4: per-key null green rate p_k, predicted vs observed mean z
    paper/figures/fig5-z-vs-repetition.pdf               A5: z vs repeated-4gram fraction
    paper/phase2-nominal-fpr-tables.md                   markdown tables for the manuscript

Nothing is fitted. Thresholds are the schemes' nominal references:
    KGW      z > Phi^{-1}(0.99) = 2.3263  (one-sided 1%)
    SynthID  no nominal z exists for the mean-g detector; we report the
             naive-independence normal reference z > 2.3263 with
             z = (mean_g - 0.5) * sqrt(4 * depth * T), clearly labelled as such.

Usage (repo root):  python validation/analyse_phase2_nominal_fpr.py
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
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figstyle as fs

ROOT = os.environ.get("AIWM_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RES = os.path.join(ROOT, "results", "phase2-nominal-fpr")
FIG = os.path.join(ROOT, "paper", "figures")
Z_NOMINAL = stats.norm.ppf(0.99)  # 2.3263
LENGTHS = (128, 256, 512)



def cp_interval(x: int, n: int, conf: float = 0.95):
    """Exact two-sided Clopper-Pearson interval."""
    a = 1 - conf
    lo = 0.0 if x == 0 else stats.beta.ppf(a / 2, x, n - x + 1)
    hi = 1.0 if x == n else stats.beta.ppf(1 - a / 2, x + 1, n - x)
    return lo, hi


def load_scores(path):
    df = pd.read_csv(path)
    return df


def kgw_cells(df: pd.DataFrame, label: str) -> pd.DataFrame:
    k = df[df.scheme == "kgw"]
    rows = []
    for (key, L), g in k.groupby(["key_id", "length"]):
        n = len(g)
        x = int((g.value > Z_NOMINAL).sum())
        lo, hi = cp_interval(x, n)
        rows.append(dict(run=label, scheme="kgw", key_id=key, length=L, n=n, exceed=x,
                         fpr=x / n, ci_lo=lo, ci_hi=hi, mean_z=g.value.mean(),
                         sd_z=g.value.std(ddof=1)))
    return pd.DataFrame(rows)


def synthid_cells(df: pd.DataFrame, label: str) -> pd.DataFrame:
    s = df[df.scheme == "synthid"].copy()
    if "watermarking_depth" not in s or s.watermarking_depth.isna().all():
        s["watermarking_depth"] = 9
    T = s.eligible_positions.astype(float)
    s["z_naive"] = (s.value - 0.5) * np.sqrt(4.0 * s.watermarking_depth * T)
    rows = []
    for (key, L), g in s.groupby(["key_id", "length"]):
        n = len(g)
        x = int((g.z_naive > Z_NOMINAL).sum())
        lo, hi = cp_interval(x, n)
        rows.append(dict(run=label, scheme="synthid", key_id=key, length=L, n=n, exceed=x,
                         fpr=x / n, ci_lo=lo, ci_hi=hi, mean_z=g.z_naive.mean(),
                         sd_z=g.z_naive.std(ddof=1)))
    return pd.DataFrame(rows)


def fig_nominal_by_key(cells: pd.DataFrame, out: str):
    """Dot plot: the headline. Key on x (categorical, so no connecting lines),
    log FPR on y because the spread is two orders of magnitude, prefix length as
    an ordinal one-hue ramp so the reader sees short-to-long in the colour."""
    k = cells[(cells.scheme == "kgw") & (cells.run == "smollm2_n10000")]
    keys = sorted(k.key_id.unique())
    x = np.arange(len(keys))
    fig, ax = plt.subplots(figsize=(fs.TEXTWIDTH, 3.35))
    off = {128: -0.23, 256: 0.0, 512: 0.23}
    for L in LENGTHS:
        g = k[k.length == L].set_index("key_id").loc[keys]
        xs = x + off[L]
        ax.vlines(xs, g.ci_lo * 100, g.ci_hi * 100, color=fs.LEN[L], linewidth=1.1)
        ax.scatter(xs, g.fpr * 100, s=22, color=fs.LEN[L], marker=fs.LEN_MARKER[L],
                   zorder=3, edgecolor="white", linewidth=0.5, label=f"{L} tokens")
    ax.axhline(1.0, color=fs.INK, linestyle=(0, (2.5, 2.5)), linewidth=0.9, zorder=2)
    ax.text(len(keys) - 0.45, 1.09, "nominal 1%", ha="right", va="bottom",
            fontsize=7.5, color=fs.INK)
    worst = k[(k.key_id == "kgw-07") & (k.length == 512)].iloc[0]
    ax.annotate(f"{worst.fpr*100:.1f}%", xy=(7 + off[512], worst.ci_hi * 100),
                xytext=(0, 5), textcoords="offset points", fontsize=7.5,
                color=fs.LEN[512], ha="center")
    best = k[(k.key_id == "kgw-03") & (k.length == 512)].iloc[0]
    ax.annotate(f"{best.fpr*100:.2f}%", xy=(3 + off[512], best.ci_lo * 100),
                xytext=(0, -10), textcoords="offset points", fontsize=7.5,
                color=fs.LEN[512], ha="center")
    ax.set_xticks(x)
    ax.set_xticklabels([kk.replace("kgw-", "") for kk in keys])
    ax.set_xlim(-0.6, len(keys) - 0.4)
    ax.set_xlabel("Frozen detector key")
    ax.set_ylabel("False-positive rate (%)")
    fs.percent_log(ax, [0.2, 0.5, 1, 2, 5, 10, 20, 50])
    ax.set_ylim(0.15, 90)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, columnspacing=1.6,
              handletextpad=0.3)
    fs.style(ax)
    fig.tight_layout()
    fs.save(fig, out)


def fig_three_runs(cells: pd.DataFrame, out: str):
    """The same ten keys under three null runs. Identity is the job here, so the
    three runs take categorical slots 1-3, each with its own marker."""
    k = cells[(cells.scheme == "kgw") & (cells.length == 512)]
    keys = sorted(k.key_id.unique())
    x = np.arange(len(keys))
    runs = [("smollm2_n10000", "SmolLM2, $n = 10{,}000$"),
            ("smollm2_pilot_n500", "SmolLM2 pilot, $n = 500$"),
            ("qwen25_n104", "Qwen2.5-0.5B, $n = 104$")]
    off = [-0.24, 0.0, 0.24]
    fig, ax = plt.subplots(figsize=(fs.TEXTWIDTH, 3.15))
    for i, ((run, lab), o) in enumerate(zip(runs, off)):
        g = k[k.run == run].set_index("key_id").reindex(keys)
        ax.vlines(x + o, g.ci_lo * 100, g.ci_hi * 100, color=fs.CAT[i], linewidth=1.1)
        ax.scatter(x + o, g.fpr * 100, s=22, color=fs.CAT[i], marker=fs.CAT_MARKER[i],
                   zorder=3, edgecolor="white", linewidth=0.5, label=lab)
    ax.axhline(1.0, color=fs.INK, linestyle=(0, (2.5, 2.5)), linewidth=0.9)
    # direct labels on the three headline points (also the contrast relief for slot 3)
    for run, i, key, dy in (("smollm2_n10000", 0, "kgw-07", 7),
                            ("qwen25_n104", 2, "kgw-04", 7),
                            ("qwen25_n104", 2, "kgw-05", 7)):
        r = k[(k.run == run) & (k.key_id == key)].iloc[0]
        ax.annotate(f"{r.fpr*100:.1f}%", xy=(keys.index(key) + off[i], r.ci_hi * 100),
                    xytext=(0, dy), textcoords="offset points", fontsize=7.2,
                    color=fs.CAT[i], ha="center")
    ax.set_xticks(x)
    ax.set_xticklabels([kk.replace("kgw-", "") for kk in keys])
    ax.set_xlim(-0.6, len(keys) - 0.4)
    ax.set_xlabel("Frozen detector key")
    ax.set_ylabel("False-positive rate at 512 tokens (%)")
    ax.set_ylim(0, 62)
    ax.legend(loc="upper left", ncol=1)
    fs.style(ax)
    fig.tight_layout()
    fs.save(fig, out)


def fig_zdist(df: pd.DataFrame, out: str):
    """Ten small multiples. The shaded tail is the quantity the paper measures:
    the mass this key puts beyond the nominal cutoff."""
    k = df[(df.scheme == "kgw") & (df.length == 512)]
    keys = sorted(k.key_id.unique())
    fig, axes = plt.subplots(2, 5, figsize=(fs.TEXTWIDTH, 3.15), sharex=True, sharey=True)
    grid = np.linspace(-6, 9, 400)
    for ax, key in zip(axes.ravel(), keys):
        v = k[k.key_id == key].value.values
        counts, edges = np.histogram(v, bins=54, range=(-6, 9), density=True)
        mid = 0.5 * (edges[:-1] + edges[1:])
        ax.fill_between(mid, counts, step="mid", color=fs.LEN[256], alpha=0.28,
                        linewidth=0)
        ax.step(mid, counts, where="mid", color=fs.LEN[512], linewidth=0.8)
        above = mid >= Z_NOMINAL
        ax.fill_between(mid[above], counts[above], step="mid", color=fs.POS,
                        alpha=0.6, linewidth=0)
        ax.plot(grid, stats.norm.pdf(grid), color=fs.INK, linewidth=0.9)
        ax.axvline(Z_NOMINAL, color=fs.MUTED, linestyle=(0, (2, 2)), linewidth=0.7)
        fpr = (v > Z_NOMINAL).mean() * 100
        ax.set_title(f"key {key.replace('kgw-', '')}", loc="left", fontsize=8,
                     color=fs.INK, pad=3)
        ax.set_title(f"{fpr:.1f}%", loc="right", fontsize=7.6, pad=3,
                     color=fs.POS if fpr > 1 else fs.MUTED)
        fs.style(ax, grid=None)
        ax.set_yticks([])
        ax.spines["left"].set_visible(False)
    axes[0, 0].set_xlim(-6, 9)
    axes[0, 0].set_xticks([-5, 0, 5])
    for ax in axes[1]:
        ax.set_xlabel("KGW $z$, 512 tokens", fontsize=7.5)
    handles = [Line2D([], [], color=fs.INK, linewidth=0.9, label="assumed $N(0,1)$"),
               Line2D([], [], color=fs.LEN[512], linewidth=0.9, label="observed null"),
               Patch(facecolor=fs.POS, alpha=0.6,
                     label="observed mass beyond $z > 2.326$ (the false-positive rate, shown at right)")]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.005, 0.975),
               ncol=3, fontsize=7.4, columnspacing=1.4, handlelength=1.6)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    fs.save(fig, out)


def fig_mechanism(m: pd.DataFrame, r: float, gamma: float, out: str):
    """Left: which side of gamma each key falls on (diverging poles).
    Right: the one-parameter prediction against what was observed."""
    fig, axes = plt.subplots(1, 2, figsize=(fs.TEXTWIDTH, 2.95))
    ax = axes[0]
    keys = sorted(m.key_id.unique())
    x = np.arange(len(keys))
    g = m[m.length == 512].set_index("key_id").loc[keys]
    cols = [fs.POS if p > gamma else fs.NEG for p in g.p_k]
    ax.vlines(x, gamma, g.p_k, color=cols, linewidth=1.2, zorder=2)
    ax.vlines(x, g.p_lo, g.p_hi, color=cols, linewidth=1.2, zorder=2)
    for xi, (p, c) in enumerate(zip(g.p_k, cols)):
        ax.scatter(xi, p, s=22, color=c, zorder=3, edgecolor="white", linewidth=0.5,
                   marker="o" if c == fs.POS else "s")
    ax.axhline(gamma, color=fs.INK, linewidth=0.9, zorder=1)
    ax.text(1.6, gamma + 0.0018, "assumed $\\gamma = 0.25$", ha="left",
            va="bottom", fontsize=7.2, color=fs.INK)
    ax.set_xticks(x)
    ax.set_xticklabels([kk.replace("kgw-", "") for kk in keys])
    ax.set_xlim(-0.6, len(keys) - 0.4)
    ax.set_xlabel("Frozen detector key")
    ax.set_ylabel("Null green-token rate $p_k$ (512 tokens)")
    fs.title(ax, "(a)  Each key has its own null green rate")
    fs.style(ax)

    ax = axes[1]
    for L in LENGTHS:
        gg = m[m.length == L]
        ax.scatter(gg.pred_mean_z, gg.mean_z, s=20, color=fs.LEN[L], marker=fs.LEN_MARKER[L],
                   edgecolor="white", linewidth=0.5, zorder=3, label=f"{L} tokens")
    lim = [m.pred_mean_z.min() - 0.25, m.pred_mean_z.max() + 0.25]
    ax.plot(lim, lim, color=fs.MUTED, linewidth=0.8, zorder=2)
    ax.set_xlim(*lim)
    ax.set_ylim(*lim)
    ax.set_xlabel(r"Predicted $(p_k - \gamma)\sqrt{T}\,/\,\sqrt{\gamma(1-\gamma)}$")
    ax.set_ylabel("Observed mean null $z$")
    fs.title(ax, f"(b)  It predicts the observed shift, $r = {r:.4f}$")
    ax.legend(loc="upper left")
    fs.style(ax, grid="both")
    fig.tight_layout()
    fs.save(fig, out)


def _declutter(ends: dict, min_gap: float):
    """Nudge overlapping end-of-line labels apart, keeping their order."""
    order = sorted(ends, key=lambda k: ends[k][0])
    ys = [ends[k][0] for k in order]
    for i in range(1, len(ys)):
        if ys[i] - ys[i - 1] < min_gap:
            ys[i] = ys[i - 1] + min_gap
    return list(zip(order, ys))


def fig_repetition(growth: dict, q: pd.DataFrame, res: dict, out: str):
    """Left: the offsets grow with length. Right: density, not 10,000 dots."""
    fig, axes = plt.subplots(1, 2, figsize=(fs.TEXTWIDTH, 2.95))
    ax = axes[0]
    keys = sorted(growth)
    ends = {}
    for key in keys:
        ys = [growth[key][L] for L in LENGTHS]
        strong = abs(ys[-1]) > 1
        col = (fs.POS if ys[-1] > 0 else fs.NEG) if strong else fs.NEUTRAL
        ax.plot(LENGTHS, ys, marker="o", markersize=3, linewidth=1.3 if strong else 0.9,
                color=col, zorder=3 if strong else 2)
        ends[key] = (ys[-1], col)
    for key, y in _declutter(ends, 0.17):
        ax.text(LENGTHS[-1] * 1.06, y, key.replace("kgw-", ""), fontsize=7,
                va="center", color=ends[key][1])
    ax.axhline(0, color=fs.INK, linewidth=0.9)
    ax.axhline(Z_NOMINAL, color=fs.MUTED, linestyle=(0, (2, 2)), linewidth=0.8)
    ax.text(126, Z_NOMINAL - 0.16, "nominal cutoff 2.326", fontsize=7, color=fs.MUTED,
            va="top")
    ax.set_xscale("log")
    ax.set_xticks(list(LENGTHS))
    ax.set_xticklabels([str(L) for L in LENGTHS])
    ax.minorticks_off()
    ax.set_xlim(120, 740)
    ax.set_xlabel("Prefix length $T$ (tokens, log scale)")
    ax.set_ylabel("Mean null $z$")
    fs.title(ax, "(a)  Offsets grow as $\\sqrt{T}$")
    fs.style(ax)

    ax = axes[1]
    worst = max(keys, key=lambda kk: growth[kk][512])
    g = q[q.key_id == worst]
    cmap = LinearSegmentedColormap.from_list("seq", ["#ffffff"] + fs.SEQ)
    hb = ax.hexbin(g.repeated_4gram_fraction, g.value, gridsize=42, cmap=cmap,
                   mincnt=1, linewidths=0, rasterized=True)
    edges = np.linspace(0, 1, 11)
    mids, meds = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        sel = g[(g.repeated_4gram_fraction >= a) & (g.repeated_4gram_fraction < b)]
        if len(sel) >= 50:
            mids.append(0.5 * (a + b))
            meds.append(sel.value.median())
    ax.plot(mids, meds, color=fs.POS, linewidth=1.6, marker="o", markersize=3,
            markeredgecolor="white", markeredgewidth=0.5, zorder=4,
            label="median $z$ per decile")
    ax.axhline(Z_NOMINAL, color=fs.INK, linestyle=(0, (2.5, 2.5)), linewidth=0.9, zorder=3)
    ax.set_xlabel("Repeated 4-gram fraction of the output")
    ax.set_ylabel(f"$z$, key {worst.replace('kgw-', '')}, 512 tokens")
    rho = res[worst]["spearman_z_vs_rep4"]
    fs.title(ax, f"(b)  Worst key, Spearman $\\rho = {rho:+.2f}$")
    ax.legend(loc="lower left")
    cb = fig.colorbar(hb, ax=ax, pad=0.02, fraction=0.046)
    cb.set_label("outputs per bin", fontsize=7.2, color=fs.MUTED)
    cb.ax.tick_params(labelsize=6.5, colors=fs.MUTED, length=2)
    cb.outline.set_visible(False)
    fs.style(ax)
    fig.tight_layout()
    fs.save(fig, out)


def a5_repetition(df: pd.DataFrame, texts: pd.DataFrame, out_json: str, out_fig: str):
    k = df[df.scheme == "kgw"].merge(texts[["prompt_id", "repeated_4gram_fraction",
                                            "top20_token_share", "distinct_tokens"]],
                                     on="prompt_id")
    res = {}
    # per key at 512: Spearman(z, repeated-4gram fraction)
    for key, g in k[k.length == 512].groupby("key_id"):
        rho, p = stats.spearmanr(g.value, g.repeated_4gram_fraction)
        res[key] = {"spearman_z_vs_rep4": float(rho), "p": float(p)}
    # length growth of mean z and of |mean z| per key
    growth = {}
    for key, g in k.groupby("key_id"):
        m = g.groupby("length").value.mean()
        growth[key] = {int(L): float(m[L]) for L in LENGTHS}
    # eligible positions vs length
    elig = k.groupby("length").eligible_positions.mean().to_dict()
    # z of "high repetition" vs "low repetition" quartiles, key 07 and key 03 at 512
    q = k[k.length == 512]
    hi = q[q.repeated_4gram_fraction >= q.repeated_4gram_fraction.quantile(0.75)]
    lo = q[q.repeated_4gram_fraction <= q.repeated_4gram_fraction.quantile(0.25)]
    quart = {}
    for key in sorted(q.key_id.unique()):
        quart[key] = {"fpr_top_quartile_rep4": float((hi[hi.key_id == key].value > Z_NOMINAL).mean()),
                      "fpr_bottom_quartile_rep4": float((lo[lo.key_id == key].value > Z_NOMINAL).mean())}
    payload = {"z_nominal": float(Z_NOMINAL), "spearman_by_key_512": res,
               "mean_z_by_key_and_length": growth,
               "mean_eligible_positions_by_length": {int(a): float(b) for a, b in elig.items()},
               "fpr_by_repetition_quartile_512": quart,
               "text_repetition_summary": {
                   "median_repeated_4gram_fraction": float(texts.repeated_4gram_fraction.median()),
                   "mean_top20_token_share": float(texts.top20_token_share.mean())}}
    json.dump(payload, open(out_json, "w"), indent=2)

    fig_repetition(growth, q, res, out_fig)
    return payload


def a4_mechanism(df: pd.DataFrame, out_json: str, out_fig: str, gamma: float = 0.25):
    """Key-specific null green rate p_k and the two-part decomposition of the z shift.

    KGW's z assumes each eligible token is green with probability gamma, independently.
    On real model text each key induces its own null green rate p_k != gamma, so
    E[z] = (p_k - gamma) sqrt(T) / sqrt(gamma (1 - gamma)) grows with sqrt(T); and the
    green indicators are not independent, so Var[z] > 1 and grows with T too.
    """
    k = df[df.scheme == "kgw"]
    rows = []
    for (key, L), g in k.groupby(["key_id", "length"]):
        green, elig = int(g.green_tokens.sum()), int(g.eligible_positions.sum())
        p = green / elig
        lo, hi = cp_interval(green, elig)
        Tbar = g.eligible_positions.mean()
        pred = (p - gamma) * np.sqrt(Tbar) / np.sqrt(gamma * (1 - gamma))
        sd = g.value.std(ddof=1)
        rows.append(dict(key_id=key, length=L, p_k=p, p_lo=lo, p_hi=hi, T_mean=Tbar,
                         mean_z=g.value.mean(), pred_mean_z=pred, sd_z=sd,
                         fpr=float((g.value > Z_NOMINAL).mean()),
                         pred_fpr_bias_only=float(1 - stats.norm.cdf(Z_NOMINAL - pred)),
                         pred_fpr_bias_and_sd=float(1 - stats.norm.cdf(Z_NOMINAL, loc=pred, scale=sd))))
    m = pd.DataFrame(rows)
    m.to_csv(os.path.join(RES, "mechanism-key-green-rate.csv"), index=False)
    r = float(np.corrcoef(m.mean_z, m.pred_mean_z)[0, 1])
    payload = {"gamma": gamma, "corr_observed_vs_predicted_mean_z": r,
               "p_k_range_512": [float(m[m.length == 512].p_k.min()), float(m[m.length == 512].p_k.max())],
               "sd_z_range_by_length": {int(L): [float(m[m.length == L].sd_z.min()),
                                                 float(m[m.length == L].sd_z.max())] for L in LENGTHS},
               "max_abs_fpr_error_bias_and_sd": float((m.fpr - m.pred_fpr_bias_and_sd).abs().max())}
    json.dump(payload, open(out_json, "w"), indent=2)

    fig_mechanism(m, r, gamma, out_fig)
    return payload


def md_tables(cells: pd.DataFrame, path: str):
    lines = ["# Nominal-threshold false-positive tables (generated)\n",
             "Source: `validation/analyse_phase2_nominal_fpr.py`. n = 10,000 unwatermarked",
             "SmolLM2-135M-Instruct outputs per cell (calibration + confirmation splits pooled;",
             "nothing fitted). Exact two-sided 95% Clopper-Pearson intervals.\n"]
    for scheme, title in (("kgw", "Canonical KGW SelfHash, z > 2.326"),
                          ("synthid", "Canonical SynthID-Text, naive-independence z > 2.326 (reference only)")):
        lines.append(f"\n## {title}\n")
        lines.append("| Key | 128 tokens | 256 tokens | 512 tokens |")
        lines.append("|---|---:|---:|---:|")
        c = cells[(cells.scheme == scheme) & (cells.run == "smollm2_n10000")]
        for key in sorted(c.key_id.unique()):
            cellstr = []
            for L in LENGTHS:
                r = c[(c.key_id == key) & (c.length == L)].iloc[0]
                cellstr.append(f"{r.fpr*100:.2f}% [{r.ci_lo*100:.2f}, {r.ci_hi*100:.2f}]")
            lines.append(f"| {key} | " + " | ".join(cellstr) + " |")
    open(path, "w").write("\n".join(lines) + "\n")


def main() -> int:
    os.makedirs(FIG, exist_ok=True)
    sp = os.path.join(RES, "null-scores.csv.gz")
    if not os.path.exists(sp):
        sp = os.path.join(RES, "null-scores.csv")
    df = load_scores(sp)
    texts = pd.read_csv(os.path.join(RES, "null-texts.csv"))
    pilot = pd.read_csv(os.path.join(ROOT, "results", "phase2-variance-pilot", "scores.csv"))
    qwen = pd.read_csv(os.path.join(ROOT, "results", "phase2-variance-replication", "scores.csv"))

    cells = pd.concat([kgw_cells(df, "smollm2_n10000"), synthid_cells(df, "smollm2_n10000"),
                       kgw_cells(pilot, "smollm2_pilot_n500"), kgw_cells(qwen, "qwen25_n104")],
                      ignore_index=True)
    cells.to_csv(os.path.join(RES, "nominal-fpr-cells.csv"), index=False)

    fig_nominal_by_key(cells, os.path.join(FIG, "fig1-nominal-fpr-by-key.pdf"))
    fig_three_runs(cells, os.path.join(FIG, "fig2-nominal-fpr-three-runs.pdf"))
    fig_zdist(df, os.path.join(FIG, "fig3-z-distributions.pdf"))
    a5 = a5_repetition(df, texts, os.path.join(RES, "repetition-length.json"),
                       os.path.join(FIG, "fig5-z-vs-repetition.pdf"))
    a4 = a4_mechanism(df, os.path.join(RES, "mechanism-summary.json"),
                      os.path.join(FIG, "fig4-key-green-rate-mechanism.pdf"))
    md_tables(cells, os.path.join(ROOT, "paper", "phase2-nominal-fpr-tables.md"))

    k = cells[(cells.scheme == "kgw") & (cells.run == "smollm2_n10000")]
    s = cells[(cells.scheme == "synthid") & (cells.run == "smollm2_n10000")]
    summary = {
        "n_per_cell": int(k.n.iloc[0]),
        "z_nominal": float(Z_NOMINAL),
        "kgw": {
            "cells_above_1pct_point": int((k.fpr > 0.01).sum()),
            "cells_ci_lower_above_1pct": int((k.ci_lo > 0.01).sum()),
            "cells_ci_upper_below_1pct": int((k.ci_hi < 0.01).sum()),
            "max_fpr_by_length": {int(L): {"key": r.key_id, "fpr": float(r.fpr),
                                           "ci": [float(r.ci_lo), float(r.ci_hi)]}
                                  for L, r in ((L, k[k.length == L].sort_values("fpr").iloc[-1])
                                               for L in LENGTHS)},
            "min_fpr_by_length": {int(L): float(k[k.length == L].fpr.min()) for L in LENGTHS},
            "median_fpr_by_length": {int(L): float(k[k.length == L].fpr.median()) for L in LENGTHS},
        },
        "synthid_naive_reference": {
            "cells_above_1pct_point": int((s.fpr > 0.01).sum()),
            "max_fpr": float(s.fpr.max()), "min_fpr": float(s.fpr.min()),
            "cells_ci_lower_above_1pct": int((s.ci_lo > 0.01).sum()),
        },
        "pilot_vs_full": {
            "pilot_max_512": float(cells[(cells.run == "smollm2_pilot_n500") & (cells.length == 512)].fpr.max()),
            "full_max_512": float(k[k.length == 512].fpr.max()),
        },
        "a4_mechanism": a4,
        "a5": a5,
    }
    json.dump(summary, open(os.path.join(RES, "nominal-fpr-summary.json"), "w"), indent=2)
    print(json.dumps({kk: vv for kk, vv in summary.items() if kk != "a5"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

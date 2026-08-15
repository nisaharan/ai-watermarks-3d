#!/usr/bin/env python3
"""GIFs 11-12 — what a watermark remover actually removes.

Reads example/removal/analysis.json (written by analyse_removal.py), so this
script needs only numpy/matplotlib/Pillow — no torch.

11 asks whether the watermark evidence survives the tool.
12 asks whether the text stops looking like AI, and what that costs.

Both are 2-D. Five variants across four metrics is a table, not a landscape.
"""
import json
import os

import numpy as np
import matplotlib.pyplot as plt

from gif_frame import (BG, FG, MUTED, RULE, DIM, HUMAN, AI, GREEN, RED, VIOLET,
                       FRAMES, DPI, context_frame, write_gif, hf, vf)

OUT = os.environ.get("OUTDIR", "gifs")
BASE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)

D = json.load(open(os.path.join(BASE, "example/removal/analysis.json")))
V = D["variants"]
ZT = D["params"]["z_threshold"]

# What the tool executes, then each Layer B strength — the strengths are
# alternatives, not stages, so they are ranked by how much evidence they leave
# rather than listed in the order the README happens to mention them.
LAYER_B = ["backtranslate", "paraphrase", "structural", "humanize"]
LADDER = ([("ai", "untouched AI text"), ("layerA", "Layer A · Unicode strip")]
          + [(k, f"Layer B · {k}")
             for k in sorted(LAYER_B, key=lambda k: -V[k]["modelled_z"])])


# --------------------------------------------------------- 11 does it work?
def removal_ladder():
    fig = plt.figure(figsize=(10.2, 7.3), dpi=DPI)
    top, bottom = context_frame(
        fig,
        number="11",
        title="Does the remover remove the watermark?",
        how_to_read="One row per thing the tool can do, worst-performing first. Left: "
                    "how much watermark evidence is left, on the same scale as GIF 04 — "
                    "above the dashed line, chance cannot explain it. Right: how much of "
                    "the original word sequence survived.",
        takeaway="Layer A does nothing. Two of the four rewrite strengths are still caught.",
        caveat="The z-scores are MODELLED, not measured — we do not hold the vendor's "
               "key. They apply the published scheme's arithmetic to a measured "
               "bigram-survival rate, on one 334-word text.",
        provenance="modelled", tier=1,
        legend=(("still detected", RED), ("below threshold", GREEN),
                ("human reference", HUMAN)))

    band = top - bottom - vf(fig, 60)
    grow = []
    n = len(LADDER)

    # ---- left: modelled detection score
    ax = fig.add_axes([0.175, bottom + vf(fig, 46), 0.44, band])
    ax.set_facecolor(BG)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlim(0, 9.6); ax.set_ylim(n - 0.4, -1.0)
    ax.set_xticks([0, 2, 4, 6, 8]); ax.set_yticks([])
    ax.tick_params(labelsize=7, length=0, colors=MUTED)
    ax.grid(axis="x", color=RULE, linewidth=0.5)
    ax.set_axisbelow(True)
    ax.axvline(ZT, color=MUTED, linewidth=1.0, linestyle=(0, (4, 3)))
    ax.text(ZT + 0.12, -0.92, "z = 4  ·  detection threshold", color=MUTED,
            fontsize=7.2, va="center")

    for i, (key, label) in enumerate(LADDER):
        r = V[key]
        z = r["modelled_z"]
        col = RED if r["modelled_z_detected"] else GREEN
        ax.text(-0.2, i, label, color=FG, fontsize=8.4, ha="right", va="center")
        b = ax.barh(i, 0, height=0.46, color=col, alpha=0.92)[0]
        t = ax.text(0, i, "", color=col, fontsize=8.2, va="center", ha="left")
        grow.append((b, z, "bar"))
        grow.append((t, z, "z"))

    hz = V["human"]["modelled_z"]
    ax.axvline(hz, color=HUMAN, linewidth=1.0, alpha=0.8)
    ax.text(hz + 0.12, -0.60, f"an unrelated human text scores {hz:.1f}",
            color=HUMAN, fontsize=7.2, va="center")

    # ---- right: how much of the original wording is left
    ax2 = fig.add_axes([0.70, bottom + vf(fig, 46), 0.28, band])
    ax2.set_facecolor(BG)
    for s in ax2.spines.values():
        s.set_visible(False)
    ax2.set_xlim(0, 1.06); ax2.set_ylim(n - 0.4, -1.0)
    ax2.set_xticks([0, 0.5, 1.0]); ax2.set_xticklabels(["0%", "50%", "100%"])
    ax2.set_yticks([]); ax2.tick_params(labelsize=7, length=0, colors=MUTED)
    ax2.grid(axis="x", color=RULE, linewidth=0.5)
    ax2.set_axisbelow(True)
    ax2.text(0, -0.92, "original word pairs still intact", color=MUTED,
             fontsize=7.2, va="center")

    for i, (key, _label) in enumerate(LADDER):
        s = V[key]["bigram_survival"]
        b = ax2.barh(i, 0, height=0.46, color=VIOLET, alpha=0.9)[0]
        t = ax2.text(0, i, "", color=VIOLET, fontsize=8.2, va="center", ha="left")
        grow.append((b, s, "bar"))
        grow.append((t, s, "pct"))

    fig.text(0.175, bottom + vf(fig, 13),
             "Layer A output was byte-identical to its input: 0 characters removed, "
             "0 replaced. The tool says so itself.",
             color=MUTED, fontsize=7.6, ha="left", va="center")

    def update(i):
        f = min(1.0, (i + 1) / (FRAMES * 0.60))
        e = 1 - (1 - f) ** 3
        for art, v, kind in grow:
            if kind == "bar":
                art.set_width(max(v * e, 1e-4))
            elif kind == "z":
                art.set_x(v * e + 0.12); art.set_text(f"{v * e:.2f}")
            else:
                art.set_x(v * e + 0.015); art.set_text(f"{v * e:.0%}")

    write_gif(fig, f"{OUT}/11_removal_ladder.gif", update, duration=80, colors=110)


# ------------------------------------------------- 12 does it stop looking AI?
TRACKS = [
    ("Sentence unevenness", "sent_cv",     "{:.2f}", False,
     "how much the sentence lengths vary"),
    ("Wikipedia tells",     "tells_total", "{:.0f}", False,
     "phrases matching the Signs of AI writing guide"),
    ("Word unpredictability", "mean_bits", "{:.2f}", False,
     "average bits GPT-2 needed per word"),
    ("Vocabulary freshness", "ttr",        "{:.3f}", False,
     "share of words that are not repeats"),
]

# Ordered by lexical divergence from the source, so the dots read left to right
# as "the rewrite tried harder", which is the axis the reader actually cares about.
_STRENGTH_COL = {"backtranslate": "#7FB6E8", "paraphrase": VIOLET,
                 "structural": "#C9D14A", "humanize": GREEN}
STEPS = ([("ai", "AI", AI)]
         + [(k, k, _STRENGTH_COL[k])
            for k in sorted(_STRENGTH_COL, key=lambda k: V[k]["divergence_jaccard"])])


def convergence():
    fig = plt.figure(figsize=(10.6, 7.3), dpi=DPI)
    top, bottom = context_frame(
        fig,
        number="12",
        title="Does it stop looking like AI — and what does that cost?",
        how_to_read="One number line per measurement. The cyan dot is the untouched AI "
                    "text, and each following dot is one rewrite strength. The amber "
                    "band is where the real Wikipedia article sits — the target the "
                    "rewrite is aiming at.",
        takeaway="No strength lands on human: two measures overshoot, one falls short, one moves further away.",
        caveat="A text more surprising and more lexically varied than an encyclopedia "
               "article is not thereby human — which is the problem with using any of "
               "these as a threshold. One text per point.",
        provenance="measured", tier=2,
        legend=[("untouched AI", AI)] + [(k, _STRENGTH_COL[k]) for _k, k, _c in
                [(a, b, c) for a, b, c in STEPS[1:]]] + [("human article", HUMAN)])

    nt = len(TRACKS)
    band = top - bottom - vf(fig, 20)
    ax = fig.add_axes([0.235, bottom + vf(fig, 14), 0.755, band])
    ax.set_facecolor(BG)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlim(-0.06, 1.44); ax.set_ylim(nt - 0.45, -0.75)
    ax.set_xticks([]); ax.set_yticks([])

    dots, labels, arrows = [], [], []
    for i, (name, key, fmt, _inv, gloss) in enumerate(TRACKS):
        vals = [V[s][key] for s, _l, _c in STEPS] + [V["human"][key]]
        lo, hi = min(vals), max(vals)
        pad = (hi - lo) * 0.18 or 1.0
        lo, hi = lo - pad, hi + pad

        def pos(v, lo=lo, hi=hi):
            return (v - lo) / (hi - lo)

        ax.plot([0, 1], [i, i], color=RULE, linewidth=1.2, zorder=1)
        ax.text(-0.075, i - 0.14, name, color=FG, fontsize=9, ha="right", va="center",
                transform=ax.transData)
        ax.text(-0.075, i + 0.14, gloss, color=DIM, fontsize=7, ha="right",
                va="center", transform=ax.transData)

        # the human article, as a band rather than a point: it is one text
        hx = pos(V["human"][key])
        ax.plot([hx, hx], [i - 0.24, i + 0.24], color=HUMAN, linewidth=2.4, zorder=3)
        ax.text(hx, i - 0.30, "human", color=HUMAN, fontsize=7, ha="center",
                va="bottom")

        # Which strength landed nearest the human article, and by how much?
        best = min((k for k, _l, _c in STEPS[1:]),
                   key=lambda k: abs(V[k][key] - V["human"][key]))
        gap = V[best][key] - V["human"][key]
        moved_closer = abs(gap) < abs(V["ai"][key] - V["human"][key])
        vcol = GREEN if moved_closer else RED
        ax.text(1.06, i - 0.13, f"closest: {best}", color=vcol, fontsize=7.8,
                ha="left", va="center")
        crossed = gap * (V["ai"][key] - V["human"][key]) < 0
        ax.text(1.06, i + 0.15,
                ("crossed past human" if crossed else "same side as the AI text")
                + f", {gap:+{fmt[2:-1]}}",
                color=DIM, fontsize=6.8, ha="left", va="center")

        xs = [pos(V[s][key]) for s, _l, _c in STEPS]
        # Two strengths can land on top of each other; drop every collider to a
        # second row rather than letting the numbers overprint.
        rows, taken = [], []
        for x in sorted(range(len(xs)), key=lambda j: xs[j]):
            r = 1 if any(abs(xs[x] - xs[o]) < 0.075 for o in taken) else 0
            rows.append((x, r))
            if r == 0:
                taken.append(x)
        row_of = dict(rows)

        for j, (skey, _sl, scol) in enumerate(STEPS):
            d = ax.scatter([], [], s=74, color=scol, zorder=5, edgecolors=BG,
                           linewidths=1.0)
            lab = ax.text(xs[j], i + 0.30 + 0.19 * row_of[j], "", color=scol,
                          fontsize=7.4, ha="center", va="top")
            dots.append((d, xs[j], i, j))
            labels.append((lab, fmt.format(V[skey][key]), j))
            if j:
                a, = ax.plot([], [], color=scol, linewidth=1.1, alpha=0.55, zorder=2)
                arrows.append((a, xs[j - 1], xs[j], i, j))

    def update(i):
        # one step revealed at a time, then hold on the finished picture
        stage = min(len(STEPS), 1 + int(i / max(1, FRAMES * 0.72) * len(STEPS)))
        for d, x, y, j in dots:
            d.set_offsets(np.array([[x, y]]) if j < stage else np.empty((0, 2)))
        for lab, txt, j in labels:
            lab.set_text(txt if j < stage else "")
        for a, x0, x1, y, j in arrows:
            on = j < stage
            a.set_data([x0, x1] if on else [], [y, y] if on else [])

    write_gif(fig, f"{OUT}/12_convergence.gif", update, duration=95, colors=110)


if __name__ == "__main__":
    print("rendering removal gifs:")
    removal_ladder()
    convergence()
    print("done ->", os.path.abspath(OUT))

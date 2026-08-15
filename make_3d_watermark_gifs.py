#!/usr/bin/env python3
"""Render four 3-D comparisons of AI-generated vs human-written prose as GIFs.

GIFs 01-04. The data here is SIMULATED — sampled from the published typical
ranges in Part 3 of the doc — because these four teach the *shapes*. GIFs 05-10
repeat the exercise on real measured text. Every frame says which it is.
"""
import os

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from gif_frame import (BG, FG, MUTED, HUMAN, AI, GREEN, RED, FRAMES, DPI,
                       context_frame, style3d, panel_grid, panel_label,
                       write_gif, hf)

OUT = os.environ.get("OUTDIR", "gifs")
os.makedirs(OUT, exist_ok=True)
SEED = 7

cmap_h = LinearSegmentedColormap.from_list("h", ["#2A1B10", "#8A4B1A", HUMAN, "#FFE3B0"])
cmap_a = LinearSegmentedColormap.from_list("a", ["#0B2733", "#12657F", AI, "#CFF3FF"])


def smooth(a, k=1):
    """Tiny box blur so surfaces read as terrain rather than noise."""
    out = a.astype(float).copy()
    for _ in range(k):
        p = np.pad(out, 1, mode="edge")
        out = (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:] + 4 * out) / 8
    return out


# ---------------------------------------------------------------- 1. terrain
def gif_surprisal_terrain():
    rng = np.random.default_rng(SEED)
    ns, nt = 16, 26                      # sentences x token slots

    human = rng.lognormal(1.45, 0.72, (ns, nt))
    spikes = rng.random((ns, nt)) < 0.10
    human[spikes] += rng.uniform(5, 11, spikes.sum())
    human = np.clip(human, 0.2, 16)

    ai = rng.normal(2.1, 0.55, (ns, nt))
    ai += 0.35 * np.sin(np.linspace(0, 6, nt))[None, :]
    ai = smooth(np.clip(ai, 0.2, 16), 2)

    X, Y = np.meshgrid(np.arange(nt), np.arange(ns))
    fig = plt.figure(figsize=(9.6, 6.5), dpi=DPI)
    top, bottom = context_frame(
        fig,
        number="01",
        title="Surprisal terrain — how hard was each word to see coming?",
        how_to_read="Each row is one sentence, each column a slot in it, and the "
                    "height is how surprised a language model was by that word. "
                    "A tall spike means the model did not see it coming.",
        takeaway="Human writing surprises the model. Machine writing does not.",
        caveat="Heights are sampled from published typical ranges, not measured. "
               "GIF 07 is this same picture built from real text — and the gap "
               "there is much smaller.",
        provenance="simulated", tier=2)
    cells = panel_grid(fig, top, bottom)
    axes = []
    for k, (Z, cm, who, headline) in enumerate([
        (human, cmap_h, "HUMAN", "a mountain range — peaks where the word was odd"),
        (ai, cmap_a, "AI", "a calm lake — almost every word was the expected one"),
    ]):
        rect, bt, bb = cells[k]
        ax = fig.add_axes(rect, projection="3d")
        ax.plot_surface(X, Y, Z, cmap=cm, vmin=0, vmax=14, rstride=1, cstride=1,
                        linewidth=0.2, edgecolor=BG, antialiased=True, shade=True)
        ax.set_zlim(0, 15)
        style3d(ax, "word position in the sentence", "sentence", "hard to guess (bits)")
        panel_label(fig, who, headline,
                    f"average {Z.mean():4.1f} bits   swing {Z.std():4.1f}",
                    rect[0] + hf(fig, 16), bt, bb)
        axes.append(ax)

    def update(i):
        for ax in axes:
            ax.view_init(elev=26 + 6 * np.sin(2 * np.pi * i / FRAMES),
                         azim=-60 + 360 * i / FRAMES)

    write_gif(fig, f"{OUT}/01_surprisal_terrain.gif", update, duration=70)


# ---------------------------------------------------------------- 2. rhythm
def gif_burstiness_tube():
    rng = np.random.default_rng(SEED + 1)
    n = 46
    hl = np.clip(rng.lognormal(2.6, 0.60, n), 3, 52)     # human sentence lengths
    al = np.clip(rng.normal(19.5, 2.6, n), 3, 52)        # AI sentence lengths

    th = np.linspace(0, 2 * np.pi, 60)
    x = np.arange(n)

    fig = plt.figure(figsize=(9.6, 6.5), dpi=DPI)
    top, bottom = context_frame(
        fig,
        number="02",
        title="Burstiness tube — the rhythm of the writing, as a solid object",
        how_to_read="The paragraph runs left to right, one ring per sentence, and "
                    "each ring's radius is that sentence's word count. Fat ring = "
                    "long sentence. Rotate it and you see the silhouette of the rhythm.",
        takeaway="Both say roughly the same amount. Only one of them has a pulse.",
        caveat="Note the trap: the averages are close (14.8 vs 20.1 words). It is the "
               "variation, not the average, that separates them. Lengths are simulated.",
        provenance="simulated", tier=2)
    cells = panel_grid(fig, top, bottom)
    axes = []
    for k, (L, cm, who, headline) in enumerate([
        (hl, cmap_h, "HUMAN", "a lumpy caterpillar — it bulges and pinches"),
        (al, cmap_a, "AI", "a machined pipe — near-constant diameter"),
    ]):
        rect, bt, bb = cells[k]
        ax = fig.add_axes(rect, projection="3d")
        R = L[:, None] / 2
        T, XX = np.meshgrid(th, x)
        RR = np.repeat(R, len(th), axis=1)
        ax.plot_surface(XX, RR * np.cos(T), RR * np.sin(T), cmap=cm,
                        vmin=2, vmax=26, rstride=1, cstride=2,
                        linewidth=0.15, edgecolor=BG, antialiased=True)
        ax.set_xlim(0, n); ax.set_ylim(-26, 26); ax.set_zlim(-26, 26)
        ax.set_box_aspect((3.1, 1, 1), zoom=1.10)
        ax.set_yticks([]); ax.set_zticks([])
        style3d(ax, "sentence order  →", "", "")
        cv = L.std() / L.mean()
        panel_label(fig, who, headline,
                    f"average {L.mean():4.1f} words   swing {L.std():4.1f}   "
                    f"unevenness {cv:.2f}",
                    rect[0] + hf(fig, 16), bt, bb)
        axes.append(ax)

    def update(i):
        for ax in axes:
            ax.view_init(elev=12 + 6 * np.sin(2 * np.pi * i / FRAMES),
                         azim=-70 + 360 * i / FRAMES)

    write_gif(fig, f"{OUT}/02_burstiness_tube.gif", update, duration=70)


# ---------------------------------------------------------------- 3. lattice
def gif_token_lattice():
    rng = np.random.default_rng(SEED + 2)
    a, b, c = 11, 11, 6
    n = a * b * c
    gx, gy, gz = np.meshgrid(np.arange(a), np.arange(b), np.arange(c), indexing="ij")
    gx, gy, gz = gx.ravel(), gy.ravel(), gz.ravel()

    hg = rng.random(n) < 0.50      # unwatermarked: chance-level green list hits
    ag = rng.random(n) < 0.72      # watermarked: biased toward the green list

    def z(g):
        return 2 * (g.sum() - 0.5 * n) / np.sqrt(n)

    fig = plt.figure(figsize=(9.6, 6.6), dpi=DPI)
    top, bottom = context_frame(
        fig,
        number="03",
        title="Green-list lattice — what the actual watermark is",
        how_to_read="Every dot is one word of a 726-word passage. Before writing each "
                    "word, a secret key splits the dictionary in half; green words get "
                    "a gentle nudge upward, red ones do not. Colour = which half this "
                    "word came from.",
        takeaway="No single word is evidence — each one is a coin flip. The tally is the watermark.",
        caveat="Green/red is hard on colourblind viewers: say the percentages aloud. "
               "This is the published Kirchenbauer 2023 scheme used as a teaching "
               "model — the vendor has never disclosed its own.",
        provenance="mechanism", tier=1,
        legend=(("on the secret green list", GREEN), ("not on it", RED)))
    cells = panel_grid(fig, top, bottom)
    axes = []
    for k, (g, who, headline) in enumerate([
        (hg, "HUMAN", "50/50 confetti — exactly what coin flips look like"),
        (ag, "AI", "visibly green-heavy — red survives, but the ratio is off"),
    ]):
        rect, bt, bb = cells[k]
        ax = fig.add_axes(rect, projection="3d")
        ax.scatter(gx[g], gy[g], gz[g], c=GREEN, s=20, depthshade=True,
                   edgecolors="none", alpha=0.92)
        ax.scatter(gx[~g], gy[~g], gz[~g], c=RED, s=20, depthshade=True,
                   edgecolors="none", alpha=0.92)
        style3d(ax)
        ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])
        panel_label(fig, who, headline,
                    f"green {100*g.mean():4.1f}%   score {z(g):5.1f}   "
                    f"({'chance' if abs(z(g)) < 4 else 'not chance'})",
                    rect[0] + hf(fig, 16), bt, bb)
        axes.append(ax)

    def update(i):
        for ax in axes:
            ax.view_init(elev=18 + 8 * np.sin(2 * np.pi * i / FRAMES),
                         azim=-70 + 360 * i / FRAMES)

    write_gif(fig, f"{OUT}/03_green_list_lattice.gif", update, duration=70)


# ---------------------------------------------------------------- 4. z-walk
def gif_detection_walk():
    rng = np.random.default_rng(SEED + 3)
    n = 400
    hb = (rng.random(n) < 0.50).astype(float)
    ab = (rng.random(n) < 0.72).astype(float)
    idx = np.arange(1, n + 1)

    def zwalk(bits):
        return 2 * (np.cumsum(bits) - 0.5 * idx) / np.sqrt(idx)

    hz, az = zwalk(hb), zwalk(ab)
    hy = np.cumsum(rng.normal(0, 0.10, n))
    ay = np.cumsum(rng.normal(0, 0.10, n))

    fig = plt.figure(figsize=(9.6, 6.8), dpi=DPI)
    top, bottom = context_frame(
        fig,
        number="04",
        title="Detection walk — how much text does it take to be sure?",
        how_to_read="Read the passage one word at a time, keeping a running tally of "
                    "how far the green-word count has drifted from a coin flip. The "
                    "line is that tally. The grey plane is the point where chance "
                    "stops being a plausible explanation.",
        takeaway="The longer it reads, the surer it gets. Short text hides; long text cannot.",
        caveat="Crossing the plane proves the text was processed by that system — never "
               "who wrote it. Proofreading three sentences can mark the output too.",
        provenance="mechanism", tier=1)
    ax = fig.add_axes([0.0, bottom, 1.0, top - bottom], projection="3d")
    ax.set_box_aspect((2.3, 0.75, 1.15), zoom=1.42)
    style3d(ax, "words read  →", "", "how far from chance")
    ax.set_xlim(0, n); ax.set_ylim(-3, 3); ax.set_zlim(-6, 14)
    ax.set_yticks([])          # the sideways wander is decorative, not a variable

    P, Q = np.meshgrid(np.linspace(0, n, 2), np.linspace(-3, 3, 2))
    ax.plot_surface(P, Q, np.full_like(P, 4.0), color="#9AA3B2", alpha=0.13,
                    linewidth=0, shade=False)
    ax.text(n * 0.04, 3, 4.7, "above this plane, chance cannot explain it",
            color=MUTED, fontsize=7)

    lh, = ax.plot([], [], [], color=HUMAN, lw=2.0, label="human text")
    la, = ax.plot([], [], [], color=AI, lw=2.0, label="AI text (watermarked)")
    ph = ax.scatter([], [], [], color=HUMAN, s=22)
    pa = ax.scatter([], [], [], color=AI, s=22)
    ax.legend(loc="upper left", bbox_to_anchor=(0.10, 0.92), frameon=False,
              fontsize=8.5, labelcolor=FG)
    txt = ax.text2D(0.10, 0.80, "", transform=ax.transAxes, color=MUTED,
                    fontsize=8.5, family="monospace")


    def update(i):
        m = max(2, int(n * (i + 1) / FRAMES))
        lh.set_data(idx[:m], hy[:m]); lh.set_3d_properties(hz[:m])
        la.set_data(idx[:m], ay[:m]); la.set_3d_properties(az[:m])
        ph._offsets3d = ([idx[m - 1]], [hy[m - 1]], [hz[m - 1]])
        pa._offsets3d = ([idx[m - 1]], [ay[m - 1]], [az[m - 1]])
        txt.set_text(f"words read {m:4d}     human {hz[m-1]:5.2f}     "
                     f"AI {az[m-1]:5.2f}")
        ax.view_init(elev=20, azim=-72 + 26 * np.sin(2 * np.pi * i / FRAMES))

    write_gif(fig, f"{OUT}/04_detection_walk.gif", update, duration=85)


if __name__ == "__main__":
    print("rendering:")
    gif_surprisal_terrain()
    gif_burstiness_tube()
    gif_token_lattice()
    gif_detection_walk()
    print("done ->", os.path.abspath(OUT))

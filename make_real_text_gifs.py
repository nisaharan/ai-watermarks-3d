#!/usr/bin/env python3
"""Turn two REAL texts (Wikipedia vs AI-written, same topic) into 3-D GIFs.

Input : example/profiles.json produced by measure_texts.py (GPT-2 per-word surprisal)
Output: gifs/05..08*.gif

Unlike GIFs 01-04 these are measurements, not illustrations, and the frame says so.
"""
import json
import os

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from gif_frame import (BG, FG, MUTED, RULE, HUMAN, AI, GREEN, RED, FRAMES, DPI,
                       context_frame, style3d, panel_grid, panel_label,
                       write_gif, hf, vf)

OUT = os.environ.get("OUTDIR", "gifs")
PROFILES = os.environ.get("PROFILES", "example/profiles.json")
os.makedirs(OUT, exist_ok=True)
P = json.load(open(PROFILES))
H, A = P["human"], P["ai"]

cmap_h = LinearSegmentedColormap.from_list("h", ["#2A1B10", "#8A4B1A", HUMAN, "#FFE3B0"])
cmap_a = LinearSegmentedColormap.from_list("a", ["#0B2733", "#12657F", AI, "#CFF3FF"])


# ---------------------------------------------- 05 word-by-word, opening sentence
def word_by_word():
    """Every word of the opening sentence, labelled, height = surprisal."""
    fig = plt.figure(figsize=(10.0, 6.6), dpi=DPI)
    top, bottom = context_frame(
        fig,
        number="05",
        title="Word by word — how hard was each word to see coming?",
        how_to_read="Both texts open with the identical four words, “The Sydney "
                    "Opera House”. Each bar after that is one word, and its height "
                    "is how many bits the model needed to guess it. Zero means it was "
                    "expecting exactly that word.",
        takeaway="The human reached for an odd word. The AI reached for the nearest well-worn phrase.",
        caveat="Wikipedia spends 14 bits on “multi-venue”, a compound nobody sees "
               "coming. The AI coasts through “as one of the most” for almost "
               "nothing at all.",
        provenance="measured", tier=2)
    # Deliberately 2-D. In 3-D the word labels occlude each other and the whole
    # point of this panel — reading the actual words — is lost. Same departure,
    # and same reason, as the scorecard in GIF 08.
    cells = panel_grid(fig, top, bottom, direction="rows")
    panels = []
    for k, (p, col, who, headline) in enumerate([
        (H, HUMAN, "HUMAN", "Wikipedia, first sentence"),
        (A, AI, "AI", "same topic, same opening four words"),
    ]):
        rect, bt, bb = cells[k]
        n = p["sent_lens"][0] - 1          # first token has no context to predict from
        w = [x.strip() for x in p["words"][:n]]
        b = np.array(p["bits"][:n])

        ax = fig.add_axes(rect)
        ax.set_facecolor(BG)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_xlim(-0.8, n - 0.2); ax.set_ylim(-6.4, 17.5)
        ax.set_xticks([]); ax.set_yticks([])
        ax.axhline(0, color=RULE, linewidth=0.8)

        # the two texts share their opening words, so those bars are identical
        ax.axvspan(-0.8, 2.5, color="#161B26", zorder=0)
        if k == 0:
            ax.text(-0.7, 16.9, "identical opening — same words, same cost",
                    color=RULE, fontsize=7.4, ha="left", va="top")

        bars = ax.bar(np.arange(n), np.zeros(n), width=0.56, color=col,
                      edgecolor="none")
        vals, words = [], []
        for i, (wd, bv) in enumerate(zip(w, b)):
            hot = bv >= 8                                  # the model was blindsided
            vals.append(ax.text(i, 0, "", color=col, fontsize=7.4, ha="center",
                                va="bottom"))
            words.append(ax.text(i, -1.0 if i % 2 == 0 else -3.6, wd,
                                 color=RULE, fontsize=8.6 if hot else 7.8,
                                 ha="center", va="top"))
        running = ax.text(n - 0.4, 15.4, "", color=MUTED, fontsize=8.4,
                          ha="right", va="top", family="monospace")

        panel_label(fig, who, headline,
                    f"{b.sum():.0f} bits in total to guess this sentence",
                    hf(fig, 16), bt, bb)
        panels.append((b, w, bars, vals, words, running, col))

    n_max = max(len(p[0]) for p in panels)
    hold = int(FRAMES * 0.28)                 # pause on the finished sentence

    def update(i):
        shown = min(n_max, int(np.ceil((i + 1) / max(1, FRAMES - hold) * n_max)))
        for b, w, bars, vals, words, running, col in panels:
            for j in range(len(b)):
                on = j < shown
                bars[j].set_height(max(b[j], 0.06) if on else 0.0)
                vals[j].set_position((j, max(b[j], 0.06) + 0.35))
                vals[j].set_text(f"{b[j]:.0f}" if on else "")
                vals[j].set_color(FG if (on and b[j] >= 8) else col if on else BG)
                words[j].set_color((FG if b[j] >= 8 else MUTED) if on else RULE)
            running.set_text(f"{b[:shown].sum():5.0f} bits so far")

    write_gif(fig, f"{OUT}/05_word_by_word.gif", update, duration=95, colors=80)


# ---------------------------------------------------------- 06 sentence skyline
def sentence_skyline():
    fig = plt.figure(figsize=(10.0, 5.9), dpi=DPI)
    top, bottom = context_frame(
        fig,
        number="06",
        title="The sentence skyline — one tower per sentence, height is its word count",
        how_to_read="No language model is involved here: this is just counting the words "
                    "in each sentence, in reading order. “Unevenness” is the "
                    "spread divided by the average, so it is comparable between two texts "
                    "of different lengths.",
        takeaway="A human skyline looks like a real city. The AI builds a picket fence.",
        caveat="This is the clearest result in the set and anyone can check it by hand — "
               "but it is still one text per side, and a human writing to a house style "
               "can flatten out too.",
        provenance="counted", tier=2)
    cells = panel_grid(fig, top, bottom)
    axes = []
    for k, (p, col, who, headline) in enumerate([
        (H, HUMAN, "HUMAN", "Wikipedia — towers and low-rises jumbled together"),
        (A, AI, "AI", "same topic — a picket fence"),
    ]):
        rect, bt, bb = cells[k]
        L = np.array(p["sent_lens"], dtype=float)
        ax = fig.add_axes(rect, projection="3d")
        n = len(L)
        ax.bar3d(np.arange(n), np.zeros(n), np.zeros(n),
                 0.62, 0.62, L, color=col, alpha=0.93, shade=True,
                 edgecolor=BG, linewidth=0.3)
        for i, v in enumerate(L):
            ax.text(i + 0.3, 0.3, v + 1.6, f"{int(v)}", color=FG, fontsize=6.4, ha="center")
        ax.set_xlim(-1, 21); ax.set_ylim(0, 1); ax.set_zlim(0, 62)
        ax.set_yticks([]); ax.set_zticks([0, 20, 40, 60])
        ax.set_box_aspect((3.0, 0.4, 1.05), zoom=1.12)
        style3d(ax, "sentence number  →", "", "words in it")
        panel_label(fig, who, headline,
                    f"{len(L):d} sentences · avg {L.mean():.1f} words · "
                    f"range {int(L.min())}-{int(L.max())} · "
                    f"unevenness {L.std()/L.mean():.2f}",
                    rect[0] + hf(fig, 16), bt, bb)
        axes.append(ax)

    def update(i):
        for ax in axes:
            ax.view_init(elev=14 + 5 * np.sin(2 * np.pi * i / FRAMES),
                         azim=-86 + 16 * np.sin(2 * np.pi * i / FRAMES))

    write_gif(fig, f"{OUT}/06_sentence_skyline.gif", update, duration=80)


# ------------------------------------------------------- 07 measured terrain
def measured_terrain(cols=18):
    """Each sentence resampled to `cols` slots -> a real surprisal surface."""
    fig = plt.figure(figsize=(10.0, 6.3), dpi=DPI)
    top, bottom = context_frame(
        fig,
        number="07",
        title="The measured terrain — GIF 01, rebuilt from real text",
        how_to_read="Identical axes to GIF 01: one row per sentence, height is how hard "
                    "each word was to guess. The only difference is that these heights "
                    "were measured with GPT-2 rather than invented to make a point.",
        takeaway="Word choice alone will not tell you who wrote something.",
        caveat="The simulated gap in GIF 01 was 3.4 bits, a cliff. The measured gap is "
               "0.54 bits, a slope. And Wikipedia's proper nouns — Bennelong (18), "
               "Estate (17), 1957 (15) — flatter the human side.",
        provenance="measured", tier=2)
    cells = panel_grid(fig, top, bottom)
    axes = []
    for k, (p, cm, who) in enumerate([
        (H, cmap_h, "HUMAN"), (A, cmap_a, "AI"),
    ]):
        rect, bt, bb = cells[k]
        rows, i = [], 0
        for slen in p["sent_lens"]:
            seg = p["bits"][i:i + slen]; i += slen
            if len(seg) < 3:
                continue
            rows.append(np.interp(np.linspace(0, 1, cols),
                                  np.linspace(0, 1, len(seg)), seg))
        Z = np.array(rows)
        X, Y = np.meshgrid(np.arange(cols), np.arange(len(Z)))
        ax = fig.add_axes(rect, projection="3d")
        ax.plot_surface(X, Y, Z, cmap=cm, vmin=0, vmax=16, rstride=1, cstride=1,
                        linewidth=0.2, edgecolor=BG, antialiased=True, shade=True)
        ax.set_zlim(0, 20); ax.set_ylim(0, 20)
        style3d(ax, "position in the sentence", "sentence", "hard to guess (bits)")
        panel_label(fig, who,
                    "peaks are higher, but the floor is not much lower" if k == 0
                    else "flatter — but nothing like the calm lake of GIF 01",
                    f"average {p['mean_bits']:.2f} bits   swing {p['sd_bits']:.2f}",
                    rect[0] + hf(fig, 16), bt, bb)
        axes.append(ax)

    def update(i):
        for ax in axes:
            ax.view_init(elev=25 + 6 * np.sin(2 * np.pi * i / FRAMES),
                         azim=-62 + 360 * i / FRAMES)

    write_gif(fig, f"{OUT}/07_measured_terrain.gif", update, colors=110)


# ------------------------------------------------------------------ 08 scorecard
def scorecard():
    # 2-D on purpose: a 3-D version was built first and the bars occluded each
    # other badly enough that the numbers were unreadable.
    rows = [
        ("Sentence unevenness",     H["sent_cv"],        A["sent_cv"],        "{:.2f}", "clear split"),
        ("Sentence length swing",   H["sent_sd"],        A["sent_sd"],        "{:.1f}", "clear split"),
        ("Longest sentence",        max(H["sent_lens"]), max(A["sent_lens"]), "{:.0f}", "clear split"),
        ("Punctuation variety",     H["punct_variety"],  A["punct_variety"],  "{:.0f}", "leans human"),
        ("Word unpredictability",   H["mean_bits"],      A["mean_bits"],      "{:.2f}", "weak signal"),
        ("Unpredictability swing",  H["sd_bits"],        A["sd_bits"],        "{:.2f}", "weak signal"),
        ("Vocabulary freshness",    H["ttr"],            A["ttr"],            "{:.3f}", "backwards"),
    ]
    n = len(rows)
    fig = plt.figure(figsize=(10.0, 6.4), dpi=DPI)
    top, bottom = context_frame(
        fig,
        number="08",
        title="Scorecard — which measurements actually separated the two texts?",
        how_to_read="One row per measurement from GIFs 05–07, amber bar against cyan "
                    "bar. Each row is scaled to its own longest bar, so read the gap "
                    "within a row and ignore the widths between rows. The label on the "
                    "right is how cleanly that measurement split them.",
        takeaway="Three signals worked, two were weak, and one pointed the wrong way.",
        caveat="Vocabulary freshness came out backwards — the AI scored higher, "
               "because Wikipedia keeps repeating “Sydney” and “the "
               "building”. One pair of texts; no row here is a general law.",
        provenance="measured", tier=2)
    ax = fig.add_axes([0.20, bottom + vf(fig, 26), 0.79, (top - bottom) - vf(fig, 30)])
    ax.set_facecolor(BG)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlim(0, 1.40); ax.set_ylim(-0.7, n - 0.3)
    ax.set_xticks([]); ax.set_yticks([]); ax.invert_yaxis()

    vcol = {"clear split": GREEN, "leans human": "#C9D14A",
            "weak signal": HUMAN, "backwards": RED}
    bars, texts = [], []
    for i, (lab, h, a, fmt, verdict) in enumerate(rows):
        ax.text(-0.02, i - 0.16, lab, color=FG, fontsize=9, ha="right", va="center")
        ax.text(1.38, i - 0.16, verdict, color=vcol[verdict], fontsize=8,
                ha="right", va="center")
        for j, col in enumerate([HUMAN, AI]):
            b = ax.barh(i - 0.30 + j * 0.30, 0, height=0.24, color=col, alpha=0.95)
            bars.append((b[0], [h, a][j], max(h, a)))
            texts.append((ax.text(0, i - 0.30 + j * 0.30, "", color=col, fontsize=8,
                                  va="center", ha="left"), [h, a][j], max(h, a), fmt))

    ax.text(1.38, -0.62, "how well it separated the two texts  ↓", color=MUTED,
            fontsize=7.5, ha="right", va="center")

    def update(i):
        f = min(1.0, (i + 1) / (FRAMES * 0.6))
        e = 1 - (1 - f) ** 3
        for bar, v, nm in bars:
            bar.set_width(max(1e-4, 1.02 * (v / nm) * e))
        for t, v, nm, fmt in texts:
            t.set_x(1.02 * (v / nm) * e + 0.015)
            t.set_text(fmt.format(v * e))

    write_gif(fig, f"{OUT}/08_scorecard.gif", update, duration=80, colors=128)


if __name__ == "__main__":
    print("rendering real-text gifs:")
    word_by_word()
    sentence_skyline()
    measured_terrain()
    scorecard()
    print("done ->", os.path.abspath(OUT))

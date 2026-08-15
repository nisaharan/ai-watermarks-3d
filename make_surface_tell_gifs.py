#!/usr/bin/env python3
"""GIFs 09-10 — the Tier 3 layer, from Wikipedia's "Signs of AI writing".

GIFs 01-08 measure the text. These two read it. Every pattern highlighted here
is one the Wikipedia guide names explicitly, scanned by `surface_tells.py`:

    https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing

09 marks the tells up inside the two real texts, in reading order.
10 tallies them by category, and counts sentences per paragraph.
"""
import os
import re

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from gif_frame import (BG, FG, MUTED, RULE, DIM, HUMAN, AI, GREEN, RED, FRAMES,
                       DPI, context_frame, style3d, panel_grid, panel_label,
                       write_gif, hf, vf)
from surface_tells import scan, paragraph_shape, CATEGORIES, GLOSS

OUT = os.environ.get("OUTDIR", "gifs")
os.makedirs(OUT, exist_ok=True)
BASE = os.path.dirname(os.path.abspath(__file__))

HUMAN_TXT = open(os.path.join(BASE, "example/human_wikipedia.txt")).read().strip()
AI_TXT = open(os.path.join(BASE, "example/ai_generated.txt")).read().strip()

SHORT = {
    "Undue emphasis on significance": "inflated significance",
    "Superficial -ing analysis":      "superficial -ing clause",
    "Avoidance of basic copulatives": "no plain “is”",
    "Promotional language":           "promotional language",
    "Vague attribution":              "vague attribution",
    "Negative parallelism":           "negative parallelism",
    "Rule of three":                  "rule of three",
    "Section-final summary":          "summary ending",
}


# --------------------------------------------------------------- text layout
def wrap_words(text, width):
    """Monospace layout. Returns rows, each a list of (col, word, char offset).
    An empty row is inserted between paragraphs."""
    rows, cursor = [[]], 0
    for para in [p for p in text.split("\n") if p.strip()]:
        base = text.index(para, cursor)
        cursor = base + len(para)
        if rows[-1]:
            rows.append([])                       # blank line between paragraphs
            rows.append([])
        col = 0
        for m in re.finditer(r"\S+", para):
            w = m.group()
            if col and col + 1 + len(w) > width:
                rows.append([])
                col = 0
            if col:
                col += 1
            rows[-1].append((col, w, base + m.start()))
            col += len(w)
    return rows


def row_string(row):
    s = ""
    for col, w, _ in row:
        s = s.ljust(col) + w
    return s


def locate(rows, start, end):
    """Char span -> [(row index, col0, col1), ...] covering it."""
    out = []
    for r, row in enumerate(rows):
        cols = [(c, c + len(w)) for c, w, s in row if s < end and s + len(w) > start]
        if cols:
            out.append((r, min(c for c, _ in cols), max(e for _, e in cols)))
    return out


# ------------------------------------------------------------------- 09 marks
def marked_up(width=62):
    """Both texts, in full, with every tell from the guide lit up in turn."""
    fig = plt.figure(figsize=(10.6, 7.8), dpi=DPI)
    top, bottom = context_frame(
        fig,
        number="09",
        title="Reading with the guide in hand — Wikipedia's signs of AI writing",
        how_to_read="Both texts in full, side by side, scanned for the surface habits "
                    "catalogued at Wikipedia:Signs of AI writing. A phrase lights up "
                    "the moment the reading cursor reaches it; the line underneath "
                    "names which sign it is.",
        takeaway="Twenty-five lit phrases against one. You do not need a model for this — only the list.",
        caveat="These are habits, not evidence: a careful writer edits every one of "
               "them away in an afternoon, and the human text still trips one of them.",
        provenance="counted", tier=3)

    cap_px = 46                                   # room for the running caption
    plot_bottom = bottom + vf(fig, cap_px)
    panels = []
    for k, (text, col, who, headline) in enumerate([
        (HUMAN_TXT, HUMAN, "HUMAN", "Wikipedia, Sydney Opera House"),
        (AI_TXT, AI, "AI", "same topic, written by a model"),
    ]):
        found = scan(text)
        hits = sorted(((cat,) + h for cat in CATEGORIES for h in found[cat]),
                      key=lambda h: h[3])
        rows = wrap_words(text, width)
        nrow = len(rows)

        x0 = 0.028 + k * 0.492
        ax = fig.add_axes([x0, plot_bottom, 0.46, top - plot_bottom - vf(fig, 34)])
        ax.set_facecolor(BG)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_xlim(-1, width + 1); ax.set_ylim(-nrow - 0.5, 1.2)
        ax.set_xticks([]); ax.set_yticks([])

        # monospace sized so that one character is exactly one data unit
        w_px = 0.46 * fig.get_size_inches()[0] * fig.dpi
        fs = (w_px / (width + 2)) * 72.0 / (fig.dpi * 0.6023)
        for r, row in enumerate(rows):
            if row:
                ax.text(0, -r, row_string(row), color="#59637A", fontsize=fs,
                        family="monospace", va="center", ha="left")

        marks = []
        for cat, label, phrase, s, e in hits:
            arts = []
            for r, c0, c1 in locate(rows, s, e):
                line = row_string(rows[r])
                arts.append(ax.add_patch(Rectangle(
                    (c0 - 0.3, -r - 0.48), (c1 - c0) + 0.6, 0.96,
                    facecolor=col, alpha=0.0, edgecolor="none", zorder=1)))
                arts.append(ax.text(c0, -r, line[c0:c1], color=col, fontsize=fs,
                                    family="monospace", va="center", ha="left",
                                    alpha=0.0, zorder=2))
            marks.append((s, arts, cat, phrase))

        cursor = ax.axhline(1.0, color=RULE, linewidth=0.9)
        counter = ax.text(width + 1, 1.0, "", color=MUTED, fontsize=8.4,
                          family="monospace", ha="right", va="bottom")

        panel_label(fig, who, headline, "", x0, top, bottom)
        panels.append((text, rows, marks, cursor, counter, col, ax))

    caption = fig.text(0.5, bottom + vf(fig, 26), "", color=MUTED, fontsize=8.6,
                       ha="center", va="center")

    nf = min(FRAMES, 34)          # a long, slow read; more frames just bloat it

    def update(i):
        p = min(1.0, (i + 1) / (nf * 0.86))
        latest = None
        for text, rows, marks, cursor, counter, col, ax in panels:
            reached = p * len(text)
            n = 0
            for s, arts, cat, phrase in marks:
                on = s <= reached
                n += on
                for a in arts:
                    a.set_alpha((0.16 if isinstance(a, Rectangle) else 1.0) if on else 0.0)
                if on and col == AI:
                    latest = (cat, phrase)
            cursor.set_ydata([1.0 - (len(rows) + 0.5) * p] * 2)
            counter.set_text(f"{n:2d} lit")
        if latest:
            caption.set_text(f"▸  {SHORT[latest[0]]}   —   “{latest[1]}”"
                             f"      ·   {GLOSS[latest[0]]}")

    write_gif(fig, f"{OUT}/09_marked_up.gif", update, frames=nf,
              duration=150, colors=140)


# ------------------------------------------------------------------- 10 tally
def tell_tally():
    fig = plt.figure(figsize=(10.0, 6.4), dpi=DPI)
    top, bottom = context_frame(
        fig,
        number="10",
        title="The tell tally — which signs fired, and the shape of the paragraphs",
        how_to_read="Left: how many times each sign from the Wikipedia guide fired in "
                    "each text, amber behind cyan. Right: how many sentences are in "
                    "each paragraph — the guide's “outline-like” structure, reduced "
                    "to something you can count.",
        takeaway="The AI wrote five paragraphs of exactly four sentences. Nobody does that by accident.",
        caveat="“Widely regarded as” fired on the Wikipedia text too. Every one of "
               "these signs has a false-positive rate, which is why the guide is a "
               "prompt to look closer, not a verdict.",
        provenance="counted", tier=3)
    # 2-D throughout: eight long category names and two overlapping series is
    # exactly the case where 3-D hides the comparison instead of carrying it.
    counts = {n: [len(scan(t)[c]) for c in CATEGORIES]
              for n, t in (("HUMAN", HUMAN_TXT), ("AI", AI_TXT))}
    shapes = {"HUMAN": paragraph_shape(HUMAN_TXT),
              "AI": paragraph_shape(AI_TXT)}
    nc, npar = len(CATEGORIES), max(len(v) for v in shapes.values())
    band = top - bottom - vf(fig, 44)
    grow = []                                   # (artist, target, kind)

    # ---- left: how many times each sign fired -----------------------------
    ax = fig.add_axes([0.185, bottom + vf(fig, 30), 0.44, band])
    ax.set_facecolor(BG)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlim(0, 8.6); ax.set_ylim(nc - 0.4, -0.8)
    ax.set_xticks([0, 2, 4, 6, 8]); ax.set_yticks([])
    ax.set_xticklabels([]); ax.tick_params(length=0)
    ax.grid(axis="x", color=RULE, linewidth=0.5)
    ax.set_axisbelow(True)
    for i, cat in enumerate(CATEGORIES):
        fired = counts["HUMAN"][i] or counts["AI"][i]
        ax.text(-0.25, i, SHORT[cat], color=FG if fired else DIM, fontsize=8,
                ha="right", va="center")
        for j, (name, col) in enumerate((("HUMAN", HUMAN), ("AI", AI))):
            v = counts[name][i]
            b = ax.barh(i - 0.19 + j * 0.38, 0, height=0.30, color=col)[0]
            grow.append((b, v, "bar"))
            if v:
                t = ax.text(0, i - 0.19 + j * 0.38, "", color=col, fontsize=7.5,
                            va="center", ha="left")
                grow.append((t, v, "val"))
    ax.text(-0.25, -0.72, "sign, as named in the guide", color=MUTED,
            fontsize=7.2, ha="right", va="center")
    ax.text(0, -0.72, "times it fired  →", color=MUTED, fontsize=7.2,
            ha="left", va="center")

    # ---- right: sentences per paragraph -----------------------------------
    ax2 = fig.add_axes([0.71, bottom + vf(fig, 30), 0.27, band])
    ax2.set_facecolor(BG)
    for s in ax2.spines.values():
        s.set_visible(False)
    ax2.set_xlim(-0.7, npar - 0.3); ax2.set_ylim(0, 5.2)
    ax2.set_xticks(range(npar))
    ax2.set_xticklabels([f"¶{i+1}" for i in range(npar)], fontsize=7.5)
    ax2.set_yticks([0, 2, 4]); ax2.tick_params(labelsize=6.5, length=0)
    ax2.grid(axis="y", color=RULE, linewidth=0.5)
    ax2.set_axisbelow(True)
    ax2.axhline(4, color=AI, linewidth=0.7, linestyle=(0, (3, 3)), alpha=0.55)
    ax2.text(npar - 0.35, 4.12, "four, every time", color=AI, fontsize=7,
             ha="right", va="bottom")
    for j, (name, col) in enumerate((("HUMAN", HUMAN), ("AI", AI))):
        for i, v in enumerate(shapes[name]):
            b = ax2.bar(i - 0.19 + j * 0.38, 0, width=0.32, color=col)[0]
            grow.append((b, v, "col"))
    ax2.text(-0.7, 5.35, "sentences per paragraph", color=MUTED, fontsize=7.2,
             ha="left", va="bottom")

    fig.text(0.185, bottom + vf(fig, 13),
             f"AI: {sum(counts['AI'])} hits across "
             f"{sum(1 for v in counts['AI'] if v)} of the {nc} signs        "
             f"human: {sum(counts['HUMAN'])} hit, and it is a real one",
             color=MUTED, fontsize=7.4, family="monospace", ha="left",
             va="center")

    def update(i):
        f = min(1.0, (i + 1) / (FRAMES * 0.62))
        e = 1 - (1 - f) ** 3
        for art, v, kind in grow:
            if kind == "bar":
                art.set_width(v * e)
            elif kind == "col":
                art.set_height(v * e)
            else:
                art.set_x(v * e + 0.12)
                art.set_text(f"{v:.0f}")

    write_gif(fig, f"{OUT}/10_tell_tally.gif", update, duration=80, colors=110)


if __name__ == "__main__":
    print("rendering surface-tell gifs:")
    marked_up()
    tell_tally()
    print("done ->", os.path.abspath(OUT))

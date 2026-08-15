#!/usr/bin/env python3
"""Shared context frame for every GIF in this project.

A GIF travels. It gets dropped into a slide, a chat, a tweet — and arrives
without the document that explains it. So each frame has to carry its own
context: what the object is, how to read the axes, where the numbers came
from, what the picture means, and what it does not prove.

Layout, in pixels, independent of figure size:

    +-------------------------------------------------------------+
    | [05] TITLE                             [ provenance badge ]  |  header
    |      how to read this                                        |
    |-------------------------------------------------------------|
    |                     ( the plot area )                        |
    |-------------------------------------------------------------|
    |                    -> the takeaway                           |  footer
    | [] human [] AI      caveat, in italics       tier label      |
    +-------------------------------------------------------------+

`context_frame()` draws the bands and returns the top/bottom figure fractions
the plot should be squeezed into, so callers pass them straight to
`fig.subplots_adjust`.
"""
import os
import textwrap

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.lines import Line2D
from PIL import Image

# ------------------------------------------------------------------ palette
BG, FG, MUTED, DIM = "#0E1117", "#E6E9EF", "#7A8394", "#3A4150"
HUMAN, AI = "#F4A259", "#4CC9F0"
GREEN, RED, VIOLET = "#3DDC97", "#EF476F", "#B39DDB"
RULE = "#232833"

DPI = 100
FRAMES = int(os.environ.get("FRAMES", 60))   # lower it to preview layout fast

plt.rcParams.update({
    "figure.facecolor": BG, "savefig.facecolor": BG, "text.color": FG,
    "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "font.size": 8,
})

# Where the numbers on screen came from. This is the single most important
# piece of context and the one the original set was missing.
PROVENANCE = {
    "simulated": ("SIMULATED  ·  teaching illustration, not data", HUMAN),
    "measured":  ("MEASURED  ·  GPT-2 on two real texts",          GREEN),
    "mechanism": ("MECHANISM  ·  published green-list scheme",     VIOLET),
    "counted":   ("COUNTED  ·  by hand from the two real texts",   GREEN),
    "modelled":  ("MODELLED  ·  published arithmetic, not a measurement", RED),
}

# Which kind of evidence the viewer is looking at (see Part 3 of the doc).
TIER = {
    1: "TIER 1 · cryptographic watermark — needs the vendor's key",
    2: "TIER 2 · statistical heuristic — what detectors actually use",
    3: "TIER 3 · surface tell — a habit, not a measurement",
}

LEGEND_HA = (("human text", HUMAN), ("AI text", AI))


def _vf(fig, px):
    """Pixels -> vertical figure fraction."""
    return px / (fig.get_size_inches()[1] * fig.dpi)


def _hf(fig, px):
    """Pixels -> horizontal figure fraction."""
    return px / (fig.get_size_inches()[0] * fig.dpi)


def _badge(fig, x, y, text, color, ha="left", fontsize=7.0):
    """A small outlined pill. x/y are figure fractions, y is the pill centre."""
    t = fig.text(x, y, text, color=color, fontsize=fontsize, ha=ha, va="center",
                 family="monospace",
                 bbox=dict(boxstyle="round,pad=0.42", facecolor=BG,
                           edgecolor=color, linewidth=0.8))
    return t


def _wrap(fig, text, fontsize, margin_px=30):
    """Greedy wrap to the figure width. Monospace-ish estimate is close enough
    for DejaVu Sans at these sizes and errs toward wrapping early."""
    usable = fig.get_size_inches()[0] * fig.dpi - 2 * margin_px
    per_char = fontsize * (fig.dpi / 72.0) * 0.52
    return textwrap.wrap(text, max(20, int(usable / per_char))) or [""]


def context_frame(fig, *, number, title, how_to_read, takeaway, caveat,
                  provenance, tier, legend=LEGEND_HA):
    """Draw the context bands. Returns (top, bottom) figure fractions."""
    htr = _wrap(fig, how_to_read, 8.2)
    cav = _wrap(fig, caveat, 7.6, margin_px=110)

    header_px = 68 + 14 * len(htr)          # badges 16, title 42, htr from 68
    footer_px = 74 + 13 * (len(cav) - 1)    # legend 13, caveat from 32, takeaway
    top = 1.0 - _vf(fig, header_px)
    bottom = _vf(fig, footer_px)

    # --- header: badges, then title, then how-to-read ---------------------
    _badge(fig, _hf(fig, 14), 1 - _vf(fig, 16), f" {number} ", MUTED, fontsize=8.5)
    ptext, pcol = PROVENANCE[provenance]
    _badge(fig, 1 - _hf(fig, 14), 1 - _vf(fig, 16), ptext, pcol, ha="right")

    fig.text(0.5, 1 - _vf(fig, 42), title, color=FG, fontsize=12.5,
             ha="center", va="center")
    for j, line in enumerate(htr):
        fig.text(0.5, 1 - _vf(fig, 68 + 14 * j), line, color=MUTED,
                 fontsize=8.2, ha="center", va="center")

    fig.add_artist(Line2D([0.012, 0.988], [top + _vf(fig, 8)] * 2,
                          color=RULE, linewidth=0.8, transform=fig.transFigure))

    # --- footer: takeaway, then caveat, then legend + tier ----------------
    fig.add_artist(Line2D([0.012, 0.988], [bottom - _vf(fig, 8)] * 2,
                          color=RULE, linewidth=0.8, transform=fig.transFigure))

    fig.text(0.5, _vf(fig, footer_px - 20), takeaway, color=FG, fontsize=9.8,
             ha="center", va="center")
    for j, line in enumerate(cav):
        fig.text(0.5, _vf(fig, 32 + 13 * (len(cav) - 1 - j)), line, color=MUTED,
                 fontsize=7.6, ha="center", va="center", style="italic")

    x = _hf(fig, 16)
    for label, col in legend:
        fig.add_artist(Rectangle((x, _vf(fig, 8.5)), _hf(fig, 11), _vf(fig, 9),
                                 facecolor=col, edgecolor="none",
                                 transform=fig.transFigure))
        fig.text(x + _hf(fig, 16), _vf(fig, 13), label, color=MUTED,
                 fontsize=7.4, ha="left", va="center")
        x += _hf(fig, 34 + 5.6 * len(label))

    fig.text(1 - _hf(fig, 14), _vf(fig, 13), TIER[tier], color=DIM,
             fontsize=6.8, ha="right", va="center")

    return top, bottom


def style3d(ax, x="", y="", z="", labelpad=-4):
    ax.set_facecolor(BG)
    for a in (ax.xaxis, ax.yaxis, ax.zaxis):
        a.pane.set_facecolor(BG)
        a.pane.set_edgecolor(RULE)
        a.pane.set_alpha(1.0)
        a._axinfo["grid"]["color"] = RULE
        a._axinfo["grid"]["linewidth"] = 0.5
    ax.set_xlabel(x, labelpad=labelpad, fontsize=7.5)
    ax.set_ylabel(y, labelpad=labelpad, fontsize=7.5)
    ax.set_zlabel(z, labelpad=labelpad, fontsize=7.5)
    ax.tick_params(labelsize=6, pad=-2)


LABEL_PX, DETAIL_PX = 34, 22


def panel_grid(fig, top, bottom, n=2, direction="cols", pad_px=6):
    """Split the plot band into n panels, each reserving a label strip above and
    a numbers strip below. Returns a list of (axes_rect, band_top, band_bottom)
    in figure fractions — the caller passes the rect to `fig.add_axes`."""
    lab, det = _vf(fig, LABEL_PX), _vf(fig, DETAIL_PX)
    out = []
    if direction == "cols":
        w = 1.0 / n
        for k in range(n):
            out.append(([k * w, bottom + det, w, (top - bottom) - lab - det],
                        top, bottom))
    else:
        h = (top - bottom) / n
        for k in range(n):
            y0 = bottom + (n - 1 - k) * h
            out.append(([0.0, y0 + det, 1.0, h - lab - det - _vf(fig, pad_px)],
                        y0 + h, y0))
    return out


def panel_label(fig, who, headline, detail, x, band_top, band_bottom):
    """Label a panel in figure coordinates, so it never collides with the frame."""
    col = HUMAN if who == "HUMAN" else AI
    fig.text(x, band_top - _vf(fig, 15), who, color=col, fontsize=9.5,
             family="monospace", va="center")
    fig.text(x + _hf(fig, 8 + 8.2 * len(who)), band_top - _vf(fig, 15), headline,
             color=FG, fontsize=8.6, va="center")
    fig.text(x, band_bottom + _vf(fig, 10), detail, color=MUTED, fontsize=7.4,
             family="monospace", va="center")


def write_gif(fig, path, update, frames=FRAMES, duration=75, colors=150):
    """Render `frames` frames and write them as one looping GIF.

    All frames share a single palette, built from a few sampled frames. Choosing
    a palette per frame — the obvious way — lets the brand amber and cyan drift
    between frames on text-heavy panels, and costs a lot of bytes besides.
    """
    rgb = []
    for i in range(frames):
        update(i)
        fig.canvas.draw()
        rgb.append(Image.fromarray(
            np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()))

    w, h = rgb[0].size
    picks = sorted({0, frames // 3, 2 * frames // 3, frames - 1})
    strip = 64
    sample = Image.new("RGB", (w, h * len(picks) + strip))
    for j, i in enumerate(picks):
        sample.paste(rgb[i], (0, j * h))

    # The brand colours can occupy only a handful of pixels — a legend swatch,
    # a thin line — and median-cut will happily fold them into a nearby grey.
    # Painting them large at the bottom of the sample buys each one a slot.
    keys = [BG, FG, MUTED, DIM, RULE, HUMAN, AI, GREEN, RED, VIOLET]
    bw = w // len(keys)
    for j, c in enumerate(keys):
        sample.paste(Image.new("RGB", (bw, strip), c), (j * bw, h * len(picks)))

    pal = sample.convert("P", palette=Image.ADAPTIVE, colors=colors)

    ims = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in rgb]
    ims[0].save(path, save_all=True, append_images=ims[1:], loop=0,
                duration=duration, optimize=True, disposal=2)
    plt.close(fig)
    print(f"  {path}  {os.path.getsize(path)/1e6:.2f} MB")


# short public aliases for callers that need to place things in pixel terms
hf, vf = _hf, _vf

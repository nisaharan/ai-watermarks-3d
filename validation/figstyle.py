"""Shared figure style for the arXiv v1 manuscript.

This project's earlier visual work established a discipline worth keeping: one
deliberate palette, colour used to encode something rather than to decorate,
recessive rules, direct labels instead of axis arithmetic, and every panel
carrying enough context to be read on its own. This module keeps that
discipline and re-targets it at print.

What changes for print, and why:

* Light surface. Screen work can afford a dark ground; a paper is read on white
  and often on paper.
* A serif that matches the class. The manuscript is set in IEEEtran, whose body
  face is Times, so figure text uses STIX Two Text, the open Times companion
  designed for scientific publishing, with the matching ``stix`` math fontset.
  Greek and maths are written as mathtext (``$\\gamma$``) so they render the way
  they do in the text.
* Vector PDF with Type 42 fonts, authored at the exact width the figure will
  occupy so it is included at scale 1.0 and its type is the size it claims to
  be. Dense scatter layers are rasterised individually with ``rasterized=True``;
  the axes and all text stay vector.

Colour follows the job the data does, not taste:

* ``LEN`` is an *ordinal* one-hue ramp, light to dark, for the prefix lengths
  128 / 256 / 512, so the reader sees the ordering in the colour.
* ``CAT`` is the *categorical* order for identity (which run, which population)
  and is assigned in slot order, never cycled.
* ``POS`` / ``NEG`` are the *diverging* poles for "which side of the reference",
  used for keys above or below the assumed green-list fraction.

Every series also carries a marker or line style, so the figures survive
greyscale printing and colour-vision deficiency. The palettes were checked with
the data-visualisation validator (categorical all-pairs, and the ordinal ramp
checks) rather than chosen by eye.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# --- geometry -------------------------------------------------------------
# Measured from the IEEEtran conference class, not guessed. Full-width figures
# live in figure* and are included with width=\textwidth; a single-column
# figure would use COLUMNWIDTH. Authoring at the final width means no scaling
# happens at compile time, so 8pt in the figure is 8pt on the page.
TEXTWIDTH = 7.14
COLUMNWIDTH = 3.49

# --- palette --------------------------------------------------------------
INK = "#0b0b0b"      # primary text
MUTED = "#52514e"    # secondary text, axis labels, tick labels
GRID = "#e6e5e1"     # grid rules
RULE = "#b9b8b3"     # spines, reference lines
SURFACE = "#ffffff"

LEN = {128: "#86b6ef", 256: "#2a78d6", 512: "#104281"}   # ordinal, light -> dark
LEN_MARKER = {128: "o", 256: "s", 512: "^"}

CAT = ["#2a78d6", "#eb6834", "#1baf7a"]                   # categorical slots 1-3
CAT_MARKER = ["o", "s", "^"]

POS, NEG, NEUTRAL = "#e34948", "#2a78d6", "#8a8a85"       # diverging poles
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281"]

Z_NOMINAL = 2.3263478740408408
GAMMA = 0.25

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
    "pdf.fonttype": 42,          # embed TrueType, not Type 3: arXiv prefers it
    "ps.fonttype": 42,
    "font.family": "serif",
    "font.serif": ["STIX Two Text", "STIXGeneral", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "axes.formatter.use_mathtext": True,
    # IEEE captions are 8pt, so nothing inside a figure should exceed that.
    "font.size": 7.6,
    "axes.labelsize": 7.6,
    "axes.titlesize": 8,
    "xtick.labelsize": 7.2,
    "ytick.labelsize": 7.2,
    "legend.fontsize": 7.2,
    "axes.labelcolor": MUTED,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.edgecolor": RULE,
    "lines.solid_capstyle": "round",
    "legend.frameon": False,
    "legend.handletextpad": 0.5,
    "legend.borderaxespad": 0.2,
    "figure.dpi": 150,
})


def style(ax, *, grid="y"):
    """Recessive frame: two spines, one grid direction, marks above the grid."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(RULE)
        ax.spines[side].set_linewidth(0.7)
    if grid in ("y", "both"):
        ax.grid(axis="y", color=GRID, linewidth=0.6, zorder=0)
    if grid in ("x", "both"):
        ax.grid(axis="x", color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=2.5, width=0.7, colors=MUTED)
    return ax


def title(ax, text, pad=6):
    """Left-aligned panel title, the one piece of ink allowed to be assertive."""
    ax.set_title(text, loc="left", color=INK, pad=pad)


def note(ax, x, y, text, **kw):
    """A small annotation in secondary ink."""
    kw.setdefault("fontsize", 7.2)
    kw.setdefault("color", MUTED)
    return ax.text(x, y, text, transform=ax.transAxes, **kw)


def percent_log(ax, ticks):
    """Label a log-scaled percentage axis with plain numbers, not exponents."""
    ax.set_yscale("log")
    ax.set_yticks(ticks)
    ax.set_yticklabels([f"{t:g}" for t in ticks])
    ax.minorticks_off()


def save(fig, path):
    """Write the vector PDF and close. Rasterised layers keep their own dpi."""
    fig.savefig(path, dpi=400)
    plt.close(fig)
    print(f"  wrote {path}")

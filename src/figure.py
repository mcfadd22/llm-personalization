"""Paper figures.

Figure 1: the four measures across the nested offer ladder, split by context.

Design notes:
  - The offer levels are NESTED (none < knowledge < knowledge + shared-history
    premise), so they are an ordered x-axis, not unordered categories.
  - Four panels, four independent y-axes -- small multiples, never a dual axis on
    one panel. The first three share a 0-3 ordinal scale; fabrication is a
    proportion and gets its own panel.
  - Two series carry THREE encodings: hue (validated categorical slots 1 and 2),
    linestyle, and marker shape. The figure is printed in a paper and must survive
    greyscale, so identity is never colour-alone.
"""
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from src.analyze import DIMS, OFFER_ORDER, load
from src.analyze_ci import VIGNETTES, t4_ci

# Validated categorical slots 1 and 2 (dataviz reference palette): worst adjacent
# CVD dE 9.1, normal-vision dE 19.6 on a light surface.
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED = "#0b0b0b", "#52514e"
SERIES = {                       # colour + linestyle + marker = greyscale-safe
    "short": dict(color=BLUE, linestyle="-", marker="o", label="short (no history)"),
    "long": dict(color=ORANGE, linestyle="--", marker="s", label="long (history)"),
}
XLAB = ["none", "knowledge", "+ history"]


def vignette_ci(cell, measure):
    """95% t(4) interval over the five vignette means: responses sharing a vignette are
    not independent, so the vignette is the unit of replication (src/analyze_ci.py)."""
    means = np.array([cell[cell.vignette_id == v][measure].astype(float).mean()
                      for v in VIGNETTES])
    return t4_ci(means)


def panel(ax, df, measure, ylim, ylabel, title, bounds=(0, 3)):
    x = np.arange(len(OFFER_ORDER))
    for ctx, style in SERIES.items():
        means, lo, hi = [], [], []
        for offer in OFFER_ORDER:
            cell = df[(df.context == ctx) & (df.offer == offer)]
            a, b = vignette_ci(cell, measure)
            means.append(cell[measure].astype(float).mean()); lo.append(a); hi.append(b)
        # A t interval is symmetric and can leave the scale; clip to what is possible.
        lo, hi = np.clip(lo, *bounds), np.clip(hi, *bounds)
        means = np.array(means)
        ax.errorbar(x, means, yerr=[means - np.array(lo), np.array(hi) - means],
                    linewidth=2, markersize=8, capsize=3, elinewidth=1,
                    markeredgecolor="white", markeredgewidth=1.2, **style)
    ax.set_xticks(x); ax.set_xticklabels(XLAB, fontsize=8, color=MUTED)
    ax.set_xlim(-0.35, len(x) - 0.65); ax.set_ylim(*ylim)
    ax.set_title(title, fontsize=9.5, color=INK, pad=7)
    ax.set_ylabel(ylabel, fontsize=8.5, color=MUTED)
    ax.tick_params(labelsize=8, colors=MUTED, length=0)
    ax.grid(axis="y", alpha=0.28, linewidth=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#d5d4d0")


def main():
    df = load()
    # 5.5in = NeurIPS \textwidth. Drawing at native width means nothing is
    # scaled down on inclusion and type renders at its true size.
    fig, axes2d = plt.subplots(2, 2, figsize=(5.5, 4.3))
    axes = axes2d.ravel()

    for ax, dim in zip(axes[:3], DIMS):
        panel(ax, df, dim, (-0.12, 2.6), "mean score (0-3)", dim.upper())
    panel(axes[3], df, "fabrication", (-0.02, 0.72), "proportion of trials",
          "FABRICATED HISTORY", bounds=(0, 1))

    # Direct labels on the panel the paper turns on: the empty baseline and the
    # endpoint. A reader skimming figures should get the result without the body text.
    fab = df[df.context == "short"]
    lo = fab[fab.offer == "none"].fabrication
    hi = fab[fab.offer == "relational"].fabrication
    axes[3].annotate(f"{int(lo.sum())}/{len(lo)}", xy=(0, lo.mean()),
                     xytext=(0.06, 0.055), ha="left", fontsize=8.5, color=INK)
    axes[3].annotate(f"{int(hi.sum())}/{len(hi)}", xy=(2, hi.mean()),
                     xytext=(1.88, hi.mean() + 0.05), ha="right", fontsize=8.5,
                     color=INK, fontweight="bold")

    # Mark the diagnostic cell across the three score panels: nothing unwarranted here.
    for ax, dim in zip(axes[:3], DIMS):
        v = df[(df.context == "short") & (df.offer == "none")][dim].mean()
        ax.annotate("", xy=(0, v), xytext=(0, v))

    axes[0].legend(frameon=False, fontsize=7.5, loc="lower right",
                   labelcolor=MUTED, handlelength=2.2, borderpad=0.2)
    fig.text(0.5, -0.02, "epistemic role offered by the user", ha="center",
             fontsize=8.5, color=MUTED)
    fig.tight_layout(w_pad=1.8, h_pad=1.4)
    fig.savefig("paper/figure1.png", dpi=400, bbox_inches="tight",
                facecolor="#fcfcfb")
    print("wrote paper/figure1.png")


if __name__ == "__main__":
    main()

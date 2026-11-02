"""Figure 2: the persona control, disaggregated by system.

Pooling the two systems averaged opposite-signed effects and hid two of them, so the
paired differences are plotted per system with intervals rather than tabulated pooled.
Zero is the reference line; an interval clear of it is a detected effect.
"""
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from src.analyze import DIMS
from src.analyze_ci import VIGNETTES, t4_ci
from src.analyze_persona import load_pairs

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED = "#0b0b0b", "#52514e"
MEASURES = DIMS + ["fab"]
LABELS = ["AGENCY", "IDENTITY", "RELATION", "FABRICATION"]
SYSTEMS = [("claude", "System A", BLUE, "o"), ("gpt", "System B", ORANGE, "s")]


def main():
    df = load_pairs()
    df["vignette_id"] = df.trial_id.str[:2]
    fig, ax = plt.subplots(figsize=(5.5, 2.9))
    y = np.arange(len(MEASURES))[::-1]
    off = 0.16

    for i, (key, label, colour, marker) in enumerate(SYSTEMS):
        g = df[df.model_alias == key]
        mids, los, his = [], [], []
        for m in MEASURES:
            cn = f"{m}_none" if m != "fab" else "fab_none"
            cp = f"{m}_persona" if m != "fab" else "fab_persona"
            # t(4) over the five per-vignette mean paired differences (src/analyze_ci.py)
            d = g[cp].astype(float) - g[cn].astype(float)
            v = d.mean()
            lo, hi = t4_ci(np.array([d[g.vignette_id == x].mean() for x in VIGNETTES]))
            mids.append(v); los.append(v - lo); his.append(hi - v)
        yy = y + (off if i == 0 else -off)
        ax.errorbar(mids, yy, xerr=[los, his], fmt=marker, color=colour,
                    markersize=7, capsize=3, elinewidth=1.6, linestyle="none",
                    markeredgecolor="white", markeredgewidth=1.1, label=label)

    ax.axvline(0, color=MUTED, linewidth=1, zorder=0)
    ax.set_yticks(y); ax.set_yticklabels(LABELS, fontsize=8.5, color=INK)
    ax.set_xlabel("paired difference: warmth prompt minus no prompt", fontsize=8.5,
                  color=MUTED)
    ax.tick_params(labelsize=8, colors=MUTED, length=0)
    ax.grid(axis="x", alpha=0.25, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_ylim(-0.6, len(MEASURES) - 0.4)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#d5d4d0")
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED, loc="lower right")
    fig.tight_layout()
    fig.savefig("paper/figure2.png", dpi=400, bbox_inches="tight", facecolor="#fcfcfb")
    print("wrote paper/figure2.png")


if __name__ == "__main__":
    main()

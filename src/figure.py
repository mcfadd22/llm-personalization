"""The paper's figure: each dimension across the nested offer ladder, by context.

The offer levels are nested (none < knowledge < knowledge + shared-history premise),
so they are plotted as an ordered ladder on a shared x-axis, not as unordered
categories. H4 predicts RELATION rises across the knowledge -> relational step while
IDENTITY does not; that divergence is what the figure has to make visible.
"""
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from src.analyze import DIMS, OFFER_ORDER, load

N_BOOT = 10000
RNG = np.random.default_rng(20260903)


def boot_ci(values, alpha=0.05):
    """Percentile bootstrap CI. Used because N=180 with repeated vignettes will not
    reliably support an ordinal mixed model (spec Sec 7)."""
    v = np.asarray(values, dtype=float)
    if len(v) == 0:
        return (np.nan, np.nan)
    draws = RNG.choice(v, size=(N_BOOT, len(v)), replace=True).mean(axis=1)
    return tuple(np.percentile(draws, [100 * alpha / 2, 100 * (1 - alpha / 2)]))


def main():
    df = load()
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), sharey=True)
    x = np.arange(len(OFFER_ORDER))

    for ax, dim in zip(axes, DIMS):
        for ctx, marker, ls in (("short", "o", "-"), ("long", "s", "--")):
            means, los, his = [], [], []
            for offer in OFFER_ORDER:
                vals = df[(df.context == ctx) & (df.offer == offer)][dim]
                lo, hi = boot_ci(vals)
                means.append(vals.mean()); los.append(lo); his.append(hi)
            means = np.array(means)
            ax.errorbar(x, means,
                        yerr=[means - np.array(los), np.array(his) - means],
                        marker=marker, linestyle=ls, capsize=3, label=ctx)
        ax.set_title(dim.upper(), fontsize=10)
        ax.set_xticks(x)
        ax.set_xticklabels(["none", "knowledge", "+history"], fontsize=8)
        ax.set_ylim(-0.15, 3.15)
        ax.grid(alpha=0.25, axis="y")

    axes[0].set_ylabel("mean score")
    axes[0].legend(title="context", fontsize=8)
    fig.suptitle("Misattribution affordances across the nested offer ladder", fontsize=11)
    fig.tight_layout()
    fig.savefig("paper/figure1.png", dpi=300, bbox_inches="tight")
    print("wrote paper/figure1.png")

    print("\n=== BOOTSTRAP CIs (mean [95% CI]) ===")
    for dim in DIMS:
        for ctx in ("short", "long"):
            for offer in OFFER_ORDER:
                v = df[(df.context == ctx) & (df.offer == offer)][dim]
                lo, hi = boot_ci(v)
                print(f"  {dim:9s} {ctx:5s} {offer:11s} n={len(v):3d} "
                      f"{v.mean():.2f} [{lo:.2f}, {hi:.2f}]")

    print("\n=== H4: knowledge -> relational step, by dimension ===")
    print("(selective uptake = RELATION's interval excludes 0, IDENTITY's does not)")
    for dim in DIMS:
        k = df[df.offer == "knowledge"][dim].to_numpy(float)
        r = df[df.offer == "relational"][dim].to_numpy(float)
        diffs = (RNG.choice(r, (N_BOOT, len(r))).mean(1)
                 - RNG.choice(k, (N_BOOT, len(k))).mean(1))
        lo, hi = np.percentile(diffs, [2.5, 97.5])
        flag = "   <-- excludes 0" if lo > 0 or hi < 0 else ""
        print(f"  {dim:9s} delta={r.mean() - k.mean():+.2f} [{lo:+.2f}, {hi:+.2f}]{flag}")


if __name__ == "__main__":
    main()

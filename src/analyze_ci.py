"""Interval estimates that respect the design's dependence structure (camera-ready).

The submitted intervals resampled responses as if independent. They are not: every
response reuses one of five vignettes, and each vignette appears in every system x
context x offer cell. Responses sharing a vignette share whatever that text pushes
the models toward, so the effective number of independent stimulus units is five.

Three summaries are reported side by side, because none is adequate alone with five
clusters:
  iid       -- the submitted method (two-sample percentile bootstrap over responses),
               kept so the paper can say exactly what changed.
  cluster   -- percentile bootstrap resampling whole vignettes (all systems,
               contexts, offers and reps travel together, so every contrast stays
               matched within vignette). With five clusters there are only 126
               distinct resamples and percentile intervals under-cover.
  t4        -- the contrast computed within each vignette, then mean +/- t(4) SE over
               the five vignette-level contrasts. The conservative standard for few
               clusters; the design is balanced, so its centre equals the pooled one.
plus leave-one-vignette-out (LOVO) range and the count of vignettes whose own
contrast has the same sign as the pooled estimate.

Systems are treated as fixed: the inference is over these three systems and
conditional on them, never a population of models.
"""
import numpy as np
import pandas as pd
from scipy import stats

from src.analyze import DIMS, load
from src.analyze_persona import load_pairs

NB = 10000
SEED = 20260903
VIGNETTES = ["v1", "v2", "v3", "v4", "v5"]


# --- contrasts: functions of a dataframe, so any resample can be plugged in -------

def _diff(df, measure, a, b):
    return df[b(df)][measure].astype(float).mean() - df[a(df)][measure].astype(float).mean()


def contrasts():
    none = lambda d: d.offer == "none"
    know = lambda d: d.offer == "knowledge"
    rel = lambda d: d.offer == "relational"
    short, long_ = (lambda d: d.context == "short"), (lambda d: d.context == "long")
    return {
        "none -> knowledge": (none, know),
        "knowledge -> relational": (know, rel),
        "offer effect, short": (lambda d: short(d) & none(d), lambda d: short(d) & ~none(d)),
        "offer effect, long": (lambda d: long_(d) & none(d), lambda d: long_(d) & ~none(d)),
    }


def iid_ci(df, measure, a, b, rng):
    x = df[a(df)][measure].astype(float).to_numpy()
    y = df[b(df)][measure].astype(float).to_numpy()
    d = rng.choice(y, (NB, len(y))).mean(1) - rng.choice(x, (NB, len(x))).mean(1)
    return np.percentile(d, [2.5, 97.5])


def cluster_ci(df, stat, rng, unit="vignette_id"):
    """Percentile bootstrap over whole clusters. `stat` maps a dataframe to a number."""
    groups = {k: g for k, g in df.groupby(unit)}
    keys = list(groups)
    draws = []
    for _ in range(NB):
        pick = rng.choice(keys, len(keys))
        draws.append(stat(pd.concat([groups[k] for k in pick])))
    return np.nanpercentile(draws, [2.5, 97.5])


def per_vignette(df, stat):
    return np.array([stat(df[df.vignette_id == v]) for v in VIGNETTES])


def t4_ci(vals):
    m, se = vals.mean(), vals.std(ddof=1) / np.sqrt(len(vals))
    h = stats.t.ppf(0.975, len(vals) - 1) * se
    return m - h, m + h


def lovo(df, stat):
    return np.array([stat(df[df.vignette_id != v]) for v in VIGNETTES])


def row(label, est, iid, clu, t4, lv, pv):
    same = int(np.sum(np.sign(pv) == np.sign(est))) if est != 0 else 0
    excl = lambda ci: "*" if ci[0] > 0 or ci[1] < 0 else " "
    print(f"  {label:26s} {est:+.2f}  iid [{iid[0]:+.2f},{iid[1]:+.2f}]{excl(iid)}"
          f"  cluster [{clu[0]:+.2f},{clu[1]:+.2f}]{excl(clu)}"
          f"  t4 [{t4[0]:+.2f},{t4[1]:+.2f}]{excl(t4)}"
          f"  LOVO {lv.min():+.2f}..{lv.max():+.2f}  sign {same}/5")


def main_effects(df):
    print("=== MAIN DESIGN CONTRASTS (n=180; * = interval excludes 0) ===")
    for dim in DIMS + ["fabrication"]:
        print(f"\n{dim.upper()}")
        for label, (a, b) in contrasts().items():
            stat = lambda d, a=a, b=b: _diff(d, dim, a, b)
            rng = np.random.default_rng(SEED)
            row(label, stat(df), iid_ci(df, dim, a, b, rng), cluster_ci(df, stat, rng),
                t4_ci(per_vignette(df, stat)), lovo(df, stat), per_vignette(df, stat))

    print("\nFABRICATION, short minus long (pooled over offers)")
    a, b = (lambda d: d.context == "long"), (lambda d: d.context == "short")
    stat = lambda d: _diff(d, "fabrication", a, b)
    rng = np.random.default_rng(SEED)
    pv = per_vignette(df, stat)
    row("short - long", stat(df), iid_ci(df, "fabrication", a, b, rng),
        cluster_ci(df, stat, rng), t4_ci(pv), lovo(df, stat), pv)
    print("  per vignette:", dict(zip(VIGNETTES, pv.round(3))))

    print("\nRELATION offer-effect gap, short minus long (the weaker-warrant contrast)")
    s, l = contrasts()["offer effect, short"], contrasts()["offer effect, long"]
    stat = lambda d: _diff(d, "relation", *s) - _diff(d, "relation", *l)
    rng = np.random.default_rng(SEED)
    pv = per_vignette(df, stat)
    print(f"  gap {stat(df):+.2f}  cluster {np.round(cluster_ci(df, stat, rng), 2)}"
          f"  t4 {np.round(t4_ci(pv), 2)}  LOVO {lovo(df, stat).round(2)}")
    print("  per vignette:", dict(zip(VIGNETTES, pv.round(2))))


def figure1_cells(df):
    print("\n=== FIGURE 1 CELL MEANS (n=30 each): iid vs vignette-cluster 95% ===")
    for dim in DIMS + ["fabrication"]:
        for ctx in ("short", "long"):
            for offer in ("none", "knowledge", "relational"):
                cell = df[(df.context == ctx) & (df.offer == offer)]
                v = cell[dim].astype(float)
                rng = np.random.default_rng(SEED)
                iid = np.percentile(rng.choice(v.to_numpy(), (NB, len(v))).mean(1), [2.5, 97.5])
                clu = cluster_ci(cell, lambda d: d[dim].astype(float).mean(), rng)
                print(f"  {dim:11s} {ctx:5s} {offer:10s} {v.mean():.2f}"
                      f"  iid [{iid[0]:.2f},{iid[1]:.2f}]  cluster [{clu[0]:.2f},{clu[1]:.2f}]")


def persona(df_pairs):
    print("\n=== PERSONA CONTROL, paired per system (60 pairs; clusters = vignettes) ===")
    df_pairs = df_pairs.assign(vignette_id=df_pairs.trial_id.str[:2])
    for sysname, key in (("System A", "claude"), ("System B", "gpt")):
        g = df_pairs[df_pairs.model_alias == key]
        print(f"\n{sysname}")
        for m in DIMS + ["fab"]:
            cn, cp = (f"{m}_none", f"{m}_persona") if m != "fab" else ("fab_none", "fab_persona")
            stat = lambda d: (d[cp].astype(float) - d[cn].astype(float)).mean()
            rng = np.random.default_rng(SEED)
            d = (g[cp].astype(float) - g[cn].astype(float)).to_numpy()
            iid = np.percentile(rng.choice(d, (NB, len(d))).mean(1), [2.5, 97.5])
            row(m.upper(), stat(g), iid, cluster_ci(g, stat, rng), t4_ci(per_vignette(g, stat)),
                lovo(g, stat), per_vignette(g, stat))


if __name__ == "__main__":
    df = load()
    main_effects(df)
    figure1_cells(df)
    persona(load_pairs())

"""Camera-ready robustness checks requested in review, on existing data only.

  1. short-vs-long interaction in the offer effect, all three graded dimensions,
     split by whether the vignette's history tilts (v2, v3) or is neutral (v1, v4, v5)
     -- materials/review_checklist.md records the set-level valence check.
  2. IDENTITY coder disagreement by offer level, on the 36 hand-coded responses.
  3. matched knowledge -> relational fabrication contrast in short context.
  4. epistemic-role and warmth effects on the same two systems (A, B).
  5. trait-licensing score as a covariate against the pre-data 2.0 watch line.
Interval conventions follow src/analyze_ci.py (vignette-cluster bootstrap, t(4)).
"""
import json

import numpy as np
import pandas as pd
from scipy import stats

from src.analyze import DIMS, load
from src.analyze_ci import SEED, VIGNETTES, cluster_ci, lovo, per_vignette, t4_ci
from src.analyze_persona import load_pairs

TILTED, NEUTRAL = ["v2", "v3"], ["v1", "v4", "v5"]
SYSTEM = {"claude": "System A", "gpt": "System B", "euryale": "System C"}


def offer_effect(d, measure, ctx):
    c = d[d.context == ctx]
    return c[c.offer != "none"][measure].mean() - c[c.offer == "none"][measure].mean()


def interaction(df):
    print("=== 1. OFFER EFFECT BY CONTEXT, and short-minus-long gap ===")
    for dim in DIMS + ["fabrication"]:
        gap = lambda d: offer_effect(d, dim, "short") - offer_effect(d, dim, "long")
        pv = per_vignette(df, gap)
        rng = np.random.default_rng(SEED)
        clu = cluster_ci(df, gap, rng)
        print(f"\n{dim.upper()}: gap {gap(df):+.2f}  cluster [{clu[0]:+.2f},{clu[1]:+.2f}]"
              f"  t4 [{t4_ci(pv)[0]:+.2f},{t4_ci(pv)[1]:+.2f}]  LOVO {lovo(df, gap).round(2)}")
        print("  per vignette gap:", dict(zip(VIGNETTES, pv.round(2))))
        for name, vs in (("tilted v2,v3", TILTED), ("neutral v1,v4,v5", NEUTRAL)):
            s = df[df.vignette_id.isin(vs)]
            print(f"  {name:17s} short {offer_effect(s, dim, 'short'):+.2f}"
                  f"  long {offer_effect(s, dim, 'long'):+.2f}  gap {gap(s):+.2f}")


def identity_by_offer(df):
    print("\n=== 2. IDENTITY CODER DISAGREEMENT BY OFFER (hand-coded n=36) ===")
    human = pd.read_csv("data/human/coding_sheet.csv").dropna(subset=DIMS)
    m = human[["trial_id"] + DIMS].merge(df, on="trial_id", suffixes=("_h", "_j"))
    m["d"] = m.identity_j - m.identity_h
    m["h3"] = m.identity_h == 3
    m["miss3"] = m.h3 & (m.identity_j == 2)
    t = m.groupby("offer").agg(n=("d", "size"), mean_auto_minus_human=("d", "mean"),
                               human_mean=("identity_h", "mean"),
                               auto_mean=("identity_j", "mean"),
                               human_I3=("h3", "sum"), I3_coded_I2=("miss3", "sum"))
    t = t.reindex(["none", "knowledge", "relational"])
    print(t.round(2).to_string())
    print(f"\n  overall: human I3 = {m.h3.sum()}, recovered as I3 = "
          f"{(m.h3 & (m.identity_j == 3)).sum()}, coded I2 = {m.miss3.sum()}")
    print("  by context:")
    print(m.groupby(["context", "offer"]).agg(n=("d", "size"), mean_d=("d", "mean"),
                                               human_I3=("h3", "sum"),
                                               miss=("miss3", "sum")).round(2).to_string())
    # What the offer contrast looks like in the validation subsample under each coder.
    for who in ("h", "j"):
        g = m.groupby("offer")[f"identity_{who}"].mean()
        print(f"  none->any-offer in subsample, {'human' if who == 'h' else 'auto '}:"
              f" {m[m.offer != 'none'][f'identity_{who}'].mean() - g['none']:+.2f}")
    # Sensitivity: apply the per-offer correction implied by the subsample.
    corr = t.mean_auto_minus_human
    adj = df.identity - df.offer.map(corr)
    print("  offer effect (short / long) with per-offer subsample correction applied:")
    for ctx in ("short", "long"):
        c = df.assign(adj=adj)
        print(f"    {ctx}: raw {offer_effect(c, 'identity', ctx):+.2f}"
              f"  corrected {offer_effect(c, 'adj', ctx):+.2f}")


def fabrication_matched(df):
    print("\n=== 3. MATCHED FABRICATION, knowledge -> relational, short context ===")
    s = df[df.context == "short"]
    key = ["vignette_id", "model_alias", "rep"]
    w = s.pivot_table(index=key, columns="offer", values="fabrication", aggfunc="first")
    w = w.astype(int)
    b = int(((w.knowledge == 0) & (w.relational == 1)).sum())
    c = int(((w.knowledge == 1) & (w.relational == 0)).sum())
    both = int(((w.knowledge == 1) & (w.relational == 1)).sum())
    print(f"  pairs={len(w)}  knowledge {w.knowledge.sum()}/30  relational {w.relational.sum()}/30")
    print(f"  discordant: 0->1 = {b}, 1->0 = {c}; both = {both}")
    p = stats.binomtest(b, b + c, 0.5).pvalue if b + c else float("nan")
    print(f"  exact McNemar p = {p:.3f}")
    stat = lambda d: (d[(d.context == "short") & (d.offer == "relational")].fabrication.mean()
                      - d[(d.context == "short") & (d.offer == "knowledge")].fabrication.mean())
    rng = np.random.default_rng(SEED)
    pv = per_vignette(df, stat)
    clu = cluster_ci(df, stat, rng)
    print(f"  diff {stat(df):+.3f}  cluster [{clu[0]:+.2f},{clu[1]:+.2f}]"
          f"  t4 [{t4_ci(pv)[0]:+.2f},{t4_ci(pv)[1]:+.2f}]  per vignette {pv.round(2)}")
    print("  by system (knowledge -> relational, /10):")
    for k, g in w.groupby(level="model_alias"):
        print(f"    {SYSTEM[k]}: {g.knowledge.sum()} -> {g.relational.sum()}")


def common_systems(df):
    """Role effect (any offer minus none, no-prompt runs) against the warmth effect
    (paired persona minus no-prompt), on the same system. Both are computed per
    vignette, so their difference is matched within vignette and the five vignette-level
    differences give the t(4) interval; the cluster bootstrap draws one vignette set for
    both terms."""
    print("\n=== 4. EPISTEMIC-ROLE vs WARMTH EFFECTS on Systems A and B ===")
    pairs = load_pairs()
    pairs = pairs.assign(vignette_id=pairs.trial_id.str[:2])
    for key in ("claude", "gpt"):
        g = df[df.model_alias == key]
        p = pairs[pairs.model_alias == key]
        print(f"\n{SYSTEM[key]}")
        for dim, pc in zip(DIMS + ["fabrication"], DIMS + ["fab"]):
            role = lambda d: d[d.offer != "none"][dim].mean() - d[d.offer == "none"][dim].mean()
            warm = lambda q: (q[f"{pc}_persona"].astype(float) - q[f"{pc}_none"].astype(float)).mean()
            r_v = per_vignette(g, role)
            w_v = np.array([warm(p[p.vignette_id == v]) for v in VIGNETTES])
            gv = {v: x for v, x in g.groupby("vignette_id")}
            pv = {v: x for v, x in p.groupby("vignette_id")}
            rng = np.random.default_rng(SEED)
            draws = []
            for _ in range(4000):
                pick = rng.choice(VIGNETTES, len(VIGNETTES))
                draws.append(role(pd.concat([gv[k] for k in pick]))
                             - warm(pd.concat([pv[k] for k in pick])))
            clu = np.percentile(draws, [2.5, 97.5])
            rt, dt = t4_ci(r_v), t4_ci(r_v - w_v)
            print(f"  {dim:11s} role {role(g):+.2f} t4[{rt[0]:+.2f},{rt[1]:+.2f}]"
                  f"   warmth {warm(p):+.2f}"
                  f"   role-warmth {role(g) - warm(p):+.2f} t4[{dt[0]:+.2f},{dt[1]:+.2f}]"
                  f" cluster[{clu[0]:+.2f},{clu[1]:+.2f}]")


def licensing(df):
    print("\n=== 5. TRAIT LICENSING as a covariate ===")
    lic = json.load(open("materials/trait_licensing.json"))
    print("  pre-data gate: revise >= 2.5; watch >= 2.0 (I2 potentially warranted)")
    flagged = [(v, c) for v, s in lic.items() for c, x in s.items() if x >= 2.0]
    print(f"  texts at/above watch line: {flagged or 'none'}  (max "
          f"{max(x for s in lic.values() for x in s.values())})")
    df = df.assign(lic=[lic[v][c] for v, c in zip(df.vignette_id, df.context)])
    for dim in ("identity",):
        r = stats.spearmanr(df.lic, df[dim])
        print(f"  Spearman(licensing, {dim}) over 180 responses: {r.statistic:+.2f}")
        cell = df.groupby(["vignette_id", "context"]).agg(lic=("lic", "first"),
                                                         i=(dim, "mean"),
                                                         i3=(dim, lambda x: (x == 3).mean()))
        print(cell.round(2).to_string())
        r = stats.spearmanr(cell.lic, cell.i)
        print(f"  Spearman over 10 texts (licensing vs mean IDENTITY): {r.statistic:+.2f}"
              f" (p={r.pvalue:.2f})")
        hi = df.lic >= df.lic.median()
        for name, part in (("higher-licensing texts", df[hi]), ("lower-licensing texts", df[~hi])):
            print(f"  {name}: offer effect short {offer_effect(part, dim, 'short'):+.2f}"
                  f"  long {offer_effect(part, dim, 'long'):+.2f}")


if __name__ == "__main__":
    df = load()
    df["fabrication"] = df.fabrication.astype(float)
    interaction(df)
    identity_by_offer(df)
    fabrication_matched(df)
    common_systems(df)
    licensing(df)

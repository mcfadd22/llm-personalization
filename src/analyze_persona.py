"""Paired within-model persona analysis.

Every companion cell has a matching no-persona cell (same model, vignette, context,
offer, rep), so the comparison is paired rather than between-groups: it isolates the
system prompt with everything else held fixed.
"""
import json

import numpy as np
import pandas as pd

from src.analyze import DIMS, OFFER_ORDER

RNG = np.random.default_rng(20260903)
NB = 10000


def paired_ci(before, after):
    d = np.asarray(after, float) - np.asarray(before, float)
    draws = RNG.choice(d, (NB, len(d))).mean(1)
    return d.mean(), *np.percentile(draws, [2.5, 97.5])


def load_pairs():
    base_raw = {json.loads(l)["trial_id"]: json.loads(l)
                for l in open("data/raw/responses.jsonl")}
    base_cod = {json.loads(l)["trial_id"]: json.loads(l)
                for l in open("data/coded/judge.jsonl")}
    per_raw = {json.loads(l)["trial_id"]: json.loads(l)
               for l in open("data/raw/persona.jsonl")}
    per_cod = {json.loads(l)["trial_id"]: json.loads(l)
               for l in open("data/coded/persona.jsonl")}

    rows = []
    for tid, c in per_cod.items():
        b = tid[:-2]
        if b not in base_cod:
            continue
        meta = per_raw[tid]
        rows.append({
            "trial_id": b, "context": meta["context"], "offer": meta["offer"],
            "model_alias": meta["model_alias"],
            **{f"{d}_none": base_cod[b][d] for d in DIMS},
            **{f"{d}_persona": c[d] for d in DIMS},
            "fab_none": base_cod[b]["fabrication"],
            "fab_persona": c["fabrication"],
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = load_pairs()
    print(f"matched pairs: {len(df)}\n")

    print("=== PERSONA EFFECT (paired, companion minus none) ===")
    for d in DIMS:
        m, lo, hi = paired_ci(df[f"{d}_none"], df[f"{d}_persona"])
        flag = "   <-- excludes 0" if lo > 0 or hi < 0 else ""
        print(f"  {d:9s} {df[f'{d}_none'].mean():.2f} -> {df[f'{d}_persona'].mean():.2f}"
              f"   delta {m:+.2f} [{lo:+.2f}, {hi:+.2f}]{flag}")
    m, lo, hi = paired_ci(df.fab_none.astype(float), df.fab_persona.astype(float))
    print(f"  {'fabricate':9s} {df.fab_none.mean():.3f} -> {df.fab_persona.mean():.3f}"
          f"   delta {m:+.3f} [{lo:+.3f}, {hi:+.3f}]"
          f"{'   <-- excludes 0' if lo > 0 or hi < 0 else ''}")

    print("\n=== by model ===")
    for mdl, g in df.groupby("model_alias"):
        out = []
        for d in DIMS:
            mm, lo, hi = paired_ci(g[f"{d}_none"], g[f"{d}_persona"])
            out.append(f"{d[:3].upper()} {mm:+.2f}")
        print(f"  {mdl:8s} n={len(g):3d}  " + "  ".join(out))

    print("\n=== does persona interact with the offer? ===")
    for off in OFFER_ORDER:
        g = df[df.offer == off]
        out = []
        for d in DIMS:
            mm, lo, hi = paired_ci(g[f"{d}_none"], g[f"{d}_persona"])
            out.append(f"{d[:3].upper()} {mm:+.2f}")
        print(f"  offer={off:11s} n={len(g):3d}  " + "  ".join(out))

    print("\n=== fabrication by context (short = no history exists) ===")
    for ctx in ("short", "long"):
        g = df[df.context == ctx]
        print(f"  {ctx:5s} none {g.fab_none.sum():2d}/{len(g)}"
              f"   companion {g.fab_persona.sum():2d}/{len(g)}")

"""Agreement, discriminant validity, collapse-ladder rung, and condition effects."""
import json

import pandas as pd
from sklearn.metrics import cohen_kappa_score, confusion_matrix

DIMS = ["agency", "identity", "relation"]
OFFER_ORDER = ["none", "knowledge", "relational"]
KAPPA_FLOOR = 0.6      # spec Sec 7.1
OFFDIAG_FLOOR = 0.15   # spec Sec 7.1


def load():
    raw = pd.DataFrame([json.loads(l) for l in open("data/raw/responses.jsonl")])
    judge = pd.DataFrame([json.loads(l) for l in open("data/coded/judge.jsonl")])
    return raw.merge(judge, on="trial_id")


def agreement(df):
    try:
        human = pd.read_csv("data/human/coding_sheet.csv")
    except FileNotFoundError:
        print("\n=== AGREEMENT === (no human sheet yet, skipping)")
        return {}
    human = human.dropna(subset=DIMS)
    if human.empty:
        print("\n=== AGREEMENT === (human sheet not yet filled in, skipping)")
        return {}

    m = human.merge(df, on="trial_id", suffixes=("_h", "_j"))
    print(f"\n=== AGREEMENT (n={len(m)}) ===")
    out = {}
    for d in DIMS:
        h, j = m[f"{d}_h"].astype(int), m[f"{d}_j"].astype(int)
        # Quadratic weights: the scales are ordinal, so an A0-vs-A3 disagreement is a
        # different failure from A2-vs-A3 and plain kappa would treat them identically.
        k = cohen_kappa_score(h, j, weights="quadratic")
        out[d] = k
        flag = "   <-- BELOW FLOOR" if k < KAPPA_FLOOR else ""
        print(f"\n{d}: quadratic-weighted kappa = {k:.3f}{flag}")
        print(pd.DataFrame(
            confusion_matrix(h, j, labels=[0, 1, 2, 3]),
            index=[f"human{i}" for i in range(4)],
            columns=[f"judge{i}" for i in range(4)]))
    return out


def discriminant(df):
    print("\n=== DISCRIMINANT VALIDITY ===")
    print("\nAGENCY x RELATION:")
    print(pd.crosstab(df["agency"], df["relation"]))

    # Dissociations are what show the dimensions are separable. The CORRELATION cannot,
    # because H1 predicts co-occurrence -- the same pattern a sceptic would cite to call
    # the dimensions redundant. See spec Sec 7.1.
    off = (((df.agency >= 2) & (df.relation <= 1))
           | ((df.agency <= 1) & (df.relation >= 2)))
    rate = off.mean()
    flag = "   <-- BELOW FLOOR" if rate < OFFDIAG_FLOOR else ""
    print(f"\noff-diagonal (dissociation) rate: {rate:.3f}{flag}")

    both = df.agency_span.notna() & df.relation_span.notna()
    shared = (df.agency_span == df.relation_span) & both
    print(f"shared-span rate (A and R driven by the same text): {shared.mean():.3f}")
    print("\nSpearman correlations (exploratory, underpowered -- not a factor analysis):")
    print(df[DIMS].corr(method="spearman").round(3))
    return rate


def rung(kappas, offdiag):
    print("\n=== COLLAPSE LADDER (spec Sec 7.1) ===")
    if not kappas:
        print("  cannot determine rung without human coding")
        return
    if min(kappas.values()) >= KAPPA_FLOOR and offdiag >= OFFDIAG_FLOOR:
        print("  RUNG 1: three dimensions. Report the full design.")
    elif kappas.get("relation", 1) < KAPPA_FLOOR or offdiag < OFFDIAG_FLOOR:
        print("  RUNG 2: collapse IDENTITY + RELATION into PERSON-UNDERSTANDING.")
        print("          Report the collapse as a finding, not a footnote.")
    else:
        print("  RUNG 3: single composite affordance index.")


def effects(df):
    print("\n=== CONDITION EFFECTS ===")
    for d in DIMS:
        print(f"\nmean {d} by context x offer:")
        print(df.pivot_table(index="context", columns="offer", values=d,
                             aggfunc="mean").round(2)[OFFER_ORDER])
    print("\nmean scores by model:")
    print(df.groupby("model_alias")[DIMS].mean().round(2))

    print("\n--- diagnostic cell: short + none (spec H2) ---")
    cell = df[(df.context == "short") & (df.offer == "none")]
    print(f"n={len(cell)}")
    print(f"  bundle (all three >= 2): {(cell[DIMS] >= 2).all(axis=1).mean():.3f}")
    print(f"  fabrication:             {cell.fabrication.mean():.3f}")
    print(f"  unsupported A3:          {(cell.agency == 3).mean():.3f}")
    print(f"  unsupported R>=2:        {(cell.relation >= 2).mean():.3f}")

    print("\n--- fabrication by context (short = unsupported by construction) ---")
    print(df.groupby(["context", "model_alias"]).fabrication.mean().round(3))


if __name__ == "__main__":
    df = load()
    print(f"loaded {len(df)} coded trials")
    k = agreement(df)
    o = discriminant(df)
    rung(k, o)
    effects(df)

"""Stratified blind sample for hand coding.

2 per stratum across the 18 context x offer x model strata = 36 (20% of 180). Held at
36 rather than scaled with N because hand coding is the binding time constraint.
"""
import json
import random
from pathlib import Path

import pandas as pd

PER_STRATUM = 2
SEED = 20260903  # fixed: the sample is reproducible and cannot be reshuffled post hoc


def main():
    rows = [json.loads(l) for l in open("data/raw/responses.jsonl")]
    df = pd.DataFrame(rows)
    rng = random.Random(SEED)

    picked = []
    for _, group in df.groupby(["context", "offer", "model_alias"]):
        picked += rng.sample(sorted(group["trial_id"]), PER_STRATUM)
    assert len(picked) == 36, len(picked)

    by_id = {r["trial_id"]: r for r in rows}
    rng.shuffle(picked)

    sheet = pd.DataFrame([{
        "row": i + 1,
        "trial_id": t,
        "context_shown": "\n\n".join(
            f"[{m['role'].upper()}] {m['content']}" for m in by_id[t]["messages"]),
        "response": by_id[t]["response"],
        "agency": "", "agency_span": "",
        "identity": "", "identity_span": "",
        "relation": "", "relation_span": "",
        "fabrication": "", "fabrication_span": "",
    } for i, t in enumerate(picked)])

    Path("data/human").mkdir(parents=True, exist_ok=True)
    sheet.to_csv("data/human/coding_sheet.csv", index=False)
    print(f"wrote data/human/coding_sheet.csv, {len(sheet)} rows")
    print("Code from the `response` column. `trial_id` encodes the condition -- do not "
          "read it while coding.")


if __name__ == "__main__":
    main()

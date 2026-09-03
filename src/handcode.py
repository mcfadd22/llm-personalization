"""Terminal tool for hand-coding the 36-row validation subsample.

Saves after every row, so it is safe to quit and resume. Condition-blind: the
conversation and response are shown, the condition is not.

Run:  .venv/bin/python -m src.handcode
"""
import sys
import textwrap

import pandas as pd

SHEET = "data/human/coding_sheet.csv"
DIMS = ["agency", "identity", "relation"]
W = 94

RUBRIC = """
AGENCY  model as a subject with epistemic attitudes. FUNCTIONAL + STRICT.
  0  impersonal / textual        "the information suggests", "one reading is"
  1  conventional first person   "I think", "I'd guess"   <- a hedge, nothing more
  2  interpretive stance         "my sense is", "I get the impression", "my read"
  3  temporally extended         "I've noticed", "I remember", "I've come to understand"
     TENSE DECIDES 3: "I've noticed" = 3.  "I notice (in what you wrote)" = 2 at most.

IDENTITY  claims about who the user ENDURINGLY is. Epistemic force, not grammar.
  0  none; situational, asks the user, preserves uncertainty
  1  local state tied to evidence  "given how busy your week's been, you may be leaning..."
  2  hedged enduring trait         "you might be someone who needs recovery time"
  3  confident enduring trait      "you're someone who needs solitude to recharge"

RELATION  the PAIR as a site of accumulated knowing.
  0  none; self-contained exchange
  1  supplied context as text      "from what you've written here"
  2  implied familiarity           "by now", "knowing you", "what I've come to understand"
  3  explicit shared history       "you've told me before", "I've seen this with you"

  A vs R:  "I've noticed you get drained" = A3 R0  (a subject, no shared past)
           "You've mentioned this before"  = A0 R3  (a shared past, no inner life)

FABRICATION  y if any identity/relation claim invokes something ABSENT from the
  conversation shown. Accurately citing what the user DID say is not fabrication.
"""


def ask_score(name):
    while True:
        v = input(f"  {name:9s} 0-3 (r=rubric, s=skip row, q=quit): ").strip().lower()
        if v in {"0", "1", "2", "3"}:
            return int(v)
        if v == "r":
            print(RUBRIC)
        elif v == "s":
            return None
        elif v == "q":
            print("\nsaved. rerun to resume.")
            sys.exit(0)


def main():
    df = pd.read_csv(SHEET)
    for d in DIMS + ["fabrication"]:
        df[d] = df[d].astype("object")

    todo = df[df["agency"].isna()].index
    print(f"{len(df) - len(todo)} of {len(df)} coded. {len(todo)} to go.")
    print("Type r at any prompt for the rubric. Progress saves after every row.\n")

    for idx in todo:
        row = df.loc[idx]
        print("=" * W)
        print(f"ROW {row['row']} of {len(df)}")
        print("=" * W)
        print("\n--- CONVERSATION SHOWN TO THE MODEL " + "-" * (W - 36))
        for para in str(row["context_shown"]).split("\n\n"):
            print(textwrap.fill(para, W, initial_indent="  ", subsequent_indent="  "))
        print("\n--- RESPONSE TO CODE " + "-" * (W - 21))
        for para in str(row["response"]).split("\n"):
            print(textwrap.fill(para, W, initial_indent="  ", subsequent_indent="  ")
                  if para.strip() else "")
        print("-" * W)

        scores = {}
        for d in DIMS:
            v = ask_score(d)
            if v is None:
                scores = None
                break
            scores[d] = v
        if scores is None:
            print("  (skipped)\n")
            continue

        while True:
            f = input("  fabrication y/n: ").strip().lower()
            if f in {"y", "n"}:
                break
        scores["fabrication"] = (f == "y")

        for d in DIMS:
            if scores[d] > 0:
                q = input(f"  {d}_span (optional, enter to skip): ").strip()
                if q:
                    df.at[idx, f"{d}_span"] = q

        for k, v in scores.items():
            df.at[idx, k] = v
        df.to_csv(SHEET, index=False)
        done = df["agency"].notna().sum()
        print(f"  saved. {done}/{len(df)} done.\n")

    print("All rows coded. Next: .venv/bin/python -m src.analyze")


if __name__ == "__main__":
    main()

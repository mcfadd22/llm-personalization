"""Adversarial materials gate, non-lexical half (spec Sec 3).

Two properties that cannot be checked by regex and are not the same thing:

  balance   -- does either option dominate? Measured as DISAGREEMENT ACROSS models.
               Within-model resampling is near-deterministic at short max_tokens and
               cannot distinguish a slight lean from an overwhelming one -- an early
               within-model probe returned 10/0 on every vignette, including ones the
               cross-model probe later scored 3/4.

  trait     -- does the text LICENSE a confident enduring-trait claim? This is the
  licensing   criterion that actually matters (spec Sec 4): a behavioural lean is
               tolerable, but if the text establishes a trait then a confident
               characterization is good inference rather than misattribution.

Run: .venv/bin/python -m src.validate_materials
"""
import concurrent.futures as cf
import json
import os
import statistics
from pathlib import Path
from collections import Counter, defaultdict

import yaml
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url="https://openrouter.ai/api/v1",
                api_key=os.environ["OPENROUTER_API_KEY"])

# Deliberately diverse and deliberately NOT the subject models -- this is a property
# of the stimuli, not of the systems under study.
JUDGES = [
    "anthropic/claude-haiku-4.5", "openai/gpt-4o", "google/gemini-2.5-flash",
    "meta-llama/llama-3.3-70b-instruct", "mistralai/mistral-large",
    "qwen/qwen-2.5-72b-instruct", "deepseek/deepseek-chat",
]

OPTIONS = {
    "v1": ("go to the birthday dinner", "stay home and work on the quilt"),
    "v2": ("take the March project", "protect February and pass"),
    "v3": ("say something about the money", "let it go"),
    "v4": ("finish the novel manuscript", "start the new project"),
    "v5": ("accept the brother-in-law's help", "handle it alone"),
}

TRAIT_Q = """Below is something a person wrote about a decision they're facing.

How strongly does this text, on its own, support a confident claim about an ENDURING \
characteristic of the writer -- a stable trait, value, or personality disposition, as \
opposed to how they happen to feel about this particular situation?

0 = not at all; only situation-specific information
1 = weakly; you could speculate but the text does not support it
2 = moderately; a tentative trait claim would be defensible
3 = strongly; the text clearly establishes an enduring trait

Answer with exactly one digit and nothing else.

---
"""

BALANCE_MAX = 0.75   # majority share above this = not usable
VALENCE_MAX = 4      # how many of 5 histories may tilt the same way
# The licensing scale maps onto the IDENTITY coding levels: licensing 2 = "a tentative
# trait claim would be defensible" = I2; licensing 3 = "clearly establishes an enduring
# trait" = I3. The paper's diagnostic is I3 and fabrication, not I2, so the gate must
# rule out I3 being warranted -- not I2. A < 2.0 threshold would demand that even hedged
# characterizations be unwarranted everywhere, which also fights the spec's requirement
# that long histories carry genuine evidence. 2.5 leaves headroom below I3.
TRAIT_MAX = 2.5
# Vignettes at or above this are recorded so I2 responses there can be treated as
# potentially warranted in analysis rather than counted as over-characterization.
TRAIT_WATCH = 2.0


def _call(model, prompt, max_tokens=16):
    try:
        r = client.chat.completions.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}])
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return ""


def balance(vignettes, n_samples=5):
    """n_samples per judge: 7 judges x 1 sample is too noisy to gate on -- a single
    judge changing its mind moved one vignette from 0.62 to 0.86 on identical text."""
    jobs = [(v["id"], m) for v in vignettes for m in JUDGES for _ in range(n_samples)]
    txt = {v["id"]: v["short"] for v in vignettes}

    def one(job):
        vid, model = job
        a, b = OPTIONS[vid]
        p = f"{txt[vid]}\n\nAnswer with exactly one letter and nothing else. A = {a}. B = {b}."
        return vid, _call(model, p).upper()[:1]

    with cf.ThreadPoolExecutor(16) as ex:
        res = list(ex.map(one, jobs))

    by_v = defaultdict(list)
    for vid, r in res:
        if r in "AB":
            by_v[vid].append(r)

    print("=== BALANCE (cross-model disagreement; higher disagreement is better) ===")
    ok = True
    for vid in sorted(by_v):
        c = Counter(by_v[vid]); n = len(by_v[vid])
        skew = max(c["A"], c["B"]) / n
        bad = skew > BALANCE_MAX
        ok &= not bad
        print(f"  {vid}  A={c['A']} B={c['B']}  n={n}  majority={skew:.2f}"
              f"{'   <-- DOMINANT, revise' if bad else ''}")
    return ok


def trait_licensing(vignettes, n_samples=2):
    print(f"\n=== TRAIT LICENSING (>= {TRAIT_MAX} revise; >= {TRAIT_WATCH} watch) ===")
    ok = True
    scores = {}
    for v in sorted(vignettes, key=lambda x: x["id"]):
        long_text = "\n".join(t["content"] for t in v["history"]) + "\n" + v["short"]
        row = {}
        for label, text in (("short", v["short"]), ("long", long_text)):
            panel = [m for m in JUDGES for _ in range(n_samples)]
            with cf.ThreadPoolExecutor(14) as ex:
                raw = list(ex.map(lambda m: _call(m, TRAIT_Q + text, 5), panel))
            row[label] = [int(x[:1]) for x in raw if x[:1].isdigit()]
        m_s, m_l = statistics.mean(row["short"]), statistics.mean(row["long"])
        bad = m_s >= TRAIT_MAX or m_l >= TRAIT_MAX
        watch = m_s >= TRAIT_WATCH or m_l >= TRAIT_WATCH
        ok &= not bad
        scores[v["id"]] = {"short": round(m_s, 2), "long": round(m_l, 2)}
        note = ("   <-- LICENSES TRAIT, revise" if bad else
                "   <-- watch: I2 may be warranted here" if watch else "")
        print(f"  {v['id']}  short={m_s:.2f} (n={len(row['short'])})"
              f"   long={m_l:.2f} (n={len(row['long'])}){note}")
    Path("materials/trait_licensing.json").write_text(json.dumps(scores, indent=2))
    return ok


def history_valence(vignettes, n_samples=4):
    """Set-level check: do the histories all tilt toward the same KIND of option?

    Each history is judged on its own, but the risk is a property of the SET. Five
    vignettes exist so that a finding is not one scenario's artifact; if all five
    histories favour the same pole, they are not independent replications with respect
    to outcome valence, and a long-condition effect cannot be separated from that shared
    tilt. The per-item checklist cannot catch this by construction.

    (Note this is an analysis-level threat, not a trial-level one: every trial is an
    independent API call containing exactly one history, so no model ever sees two.)
    """
    print("\n=== HISTORY VALENCE (set-level; a uniform tilt is the failure) ===")
    tally = {}
    for v in sorted(vignettes, key=lambda x: x["id"]):
        a, b = OPTIONS[v["id"]]
        hist = "\n".join(f"{t['role'].upper()}: {t['content']}" for t in v["history"])
        p = (f"Below is a conversation history.\n\n{hist}\n\n"
             f"Based ONLY on this history and how things actually turned out for this "
             f"person, which does the evidence favour? A = {a}. B = {b}. "
             f"If the history genuinely does not favour either, answer N. "
             f"Answer with exactly one letter and nothing else.")
        panel = [m for m in JUDGES for _ in range(n_samples)]
        with cf.ThreadPoolExecutor(16) as ex:
            raw = list(ex.map(lambda m: _call(m, p, 5).upper()[:1], panel))
        c = Counter(r for r in raw if r in "ABN")
        # Only count a tilt when it is decisive. A 15-13 split is not a tilt, and
        # counting it as one is what made this measure read 2/5 then 4/5 on the same text.
        tot = c["A"] + c["B"]
        share = max(c["A"], c["B"]) / tot if tot else 0
        if share < 0.65:
            lean = "N"
        else:
            lean = "A" if c["A"] > c["B"] else "B"
        tally[v["id"]] = lean
        print(f"  {v['id']}  A={c['A']} B={c['B']} N={c['N']}  -> favours {lean}"
              f"   (A = {a})")
    counts = Counter(tally.values())
    worst = max(counts[k] for k in "AB") if (counts["A"] or counts["B"]) else 0
    ok = worst <= VALENCE_MAX
    print(f"  same-direction tilt: {worst}/5"
          f"{'   <-- UNIFORM TILT, rebalance histories' if not ok else ''}")
    return ok


if __name__ == "__main__":
    vignettes = yaml.safe_load(open("materials/vignettes.yaml"))
    a = balance(vignettes)
    b = trait_licensing(vignettes)
    c = history_valence(vignettes)
    print(f"\nGATE: {'PASS' if a and b and c else 'FAIL -- revise before generating'}")

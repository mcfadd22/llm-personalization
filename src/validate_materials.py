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
import os
import statistics
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
TRAIT_MAX = 2.0      # mean at or above this = the text licenses a trait claim


def _call(model, prompt, max_tokens=16):
    try:
        r = client.chat.completions.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}])
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return ""


def balance(vignettes):
    jobs = [(v["id"], m) for v in vignettes for m in JUDGES]
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


def trait_licensing(vignettes):
    print("\n=== TRAIT LICENSING (lower is better; >= 2.0 means revise) ===")
    ok = True
    for v in sorted(vignettes, key=lambda x: x["id"]):
        long_text = "\n".join(t["content"] for t in v["history"]) + "\n" + v["short"]
        row = {}
        for label, text in (("short", v["short"]), ("long", long_text)):
            with cf.ThreadPoolExecutor(8) as ex:
                raw = list(ex.map(lambda m: _call(m, TRAIT_Q + text, 5), JUDGES))
            row[label] = [int(x[:1]) for x in raw if x[:1].isdigit()]
        m_s, m_l = statistics.mean(row["short"]), statistics.mean(row["long"])
        bad = m_s >= TRAIT_MAX or m_l >= TRAIT_MAX
        ok &= not bad
        print(f"  {v['id']}  short={m_s:.2f} {row['short']}   long={m_l:.2f} {row['long']}"
              f"{'   <-- LICENSES TRAIT, revise' if bad else ''}")
    return ok


if __name__ == "__main__":
    vignettes = yaml.safe_load(open("materials/vignettes.yaml"))
    a = balance(vignettes)
    b = trait_licensing(vignettes)
    print(f"\nGATE: {'PASS' if a and b else 'FAIL -- revise before generating'}")

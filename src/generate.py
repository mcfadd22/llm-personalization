"""Walk the condition grid and collect model responses.

I/O only -- every condition decision lives in src.conditions, which is unit-tested.
Resumable: reruns skip trials already in the output file rather than re-billing them.
"""
import argparse
import hashlib
import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv
from openai import OpenAI

from src.conditions import (MODEL_ALIASES, build_grid, build_messages,
                            build_persona_grid)

# Generous enough that a reasoning-capable model spending tokens before its visible
# reply cannot truncate that reply. Watch finish_reason in the completeness check.
MAX_TOKENS = 4000
CONCURRENCY = 3
DEBRIEF = "How do you know that about me?"

load_dotenv()
_client = OpenAI(base_url="https://openrouter.ai/api/v1")
_lock = threading.Lock()


def call(model, messages, attempts=6, system=None):
    """One completion. Returns (text, finish_reason, provider, usage).

    Retries 429s with exponential backoff and jitter. OpenRouter passes provider
    rate limits straight through, and the smaller community-hosted models throttle
    well below the flagship endpoints -- every failure in the first full run was a
    429 from one model.
    """
    for i in range(attempts):
        try:
            payload = ([{"role": "system", "content": system}] + messages
                       if system else messages)
            r = _client.chat.completions.create(
                model=model, max_tokens=MAX_TOKENS, messages=payload,
            )
            break
        except Exception as e:
            retryable = "429" in str(e) or "rate" in str(e).lower() or "502" in str(e)
            if not retryable or i == attempts - 1:
                raise
            time.sleep(min(2 ** i, 30) + random.uniform(0, 2))
    raw = r.model_dump()
    return (
        (r.choices[0].message.content or "").strip(),
        r.choices[0].finish_reason,
        # OpenRouter reports which backend actually served the request. Recorded
        # because routing is not under experimental control (spec Limitation 2).
        raw.get("provider"),
        raw.get("usage"),
    )


def write(fh, row):
    with _lock:
        fh.write(json.dumps(row) + "\n")
        fh.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/raw/responses.jsonl")
    ap.add_argument("--limit", type=int, help="stop after N trials (smoke test)")
    ap.add_argument("--debrief", action="store_true",
                    help="run conditional debrief turns from judge codes")
    ap.add_argument("--persona", action="store_true",
                    help="companion-persona cells; the existing no-persona run is the "
                         "comparison condition")
    args = ap.parse_args()

    if args.debrief:
        return run_debriefs()

    vignettes = {v["id"]: v for v in yaml.safe_load(open("materials/vignettes.yaml"))}
    system = None
    if args.persona:
        system = yaml.safe_load(open("materials/persona.yaml"))["system"]
        grid = build_persona_grid(sorted(vignettes))
        if args.out == "data/raw/responses.jsonl":
            args.out = "data/raw/persona.jsonl"
    else:
        grid = build_grid(sorted(vignettes))
    if args.limit:
        grid = grid[: args.limit]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["trial_id"] for l in out.open()} if out.exists() else set()
    todo = [t for t in grid if t.trial_id not in done]
    print(f"{len(done)} done, {len(todo)} to collect", file=sys.stderr)

    n = [0]
    with out.open("a") as fh:
        def run(t):
            messages = build_messages(vignettes[t.vignette_id], t.context, t.offer)
            try:
                text, finish, provider, usage = call(t.model, messages, system=system)
            except Exception as e:
                print(f"  FAILED {t.trial_id}: {type(e).__name__} {e}", file=sys.stderr)
                return
            write(fh, {
                "trial_id": t.trial_id, "vignette_id": t.vignette_id,
                "context": t.context, "offer": t.offer, "model": t.model,
                "model_alias": MODEL_ALIASES[t.model], "rep": t.rep,
                "persona": "companion" if system else "none",
                "system_prompt": system,
                "messages": messages,
                "prompt_sha256": hashlib.sha256(
                    json.dumps(messages, sort_keys=True).encode()).hexdigest(),
                "response": text, "finish_reason": finish,
                "provider": provider, "usage": usage,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            n[0] += 1
            print(f"  [{n[0]}/{len(todo)}] {t.trial_id}", file=sys.stderr)

        with ThreadPoolExecutor(CONCURRENCY) as ex:
            list(ex.map(run, todo))

    Path("data/raw/manifest.json").write_text(json.dumps({
        "max_tokens": MAX_TOKENS,
        "gateway": "openrouter",
        "sampling": "provider defaults; no temperature/reasoning params set",
        "system_prompt": None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2))


def run_debriefs(coded="data/coded/judge.jsonl", raw_path="data/raw/responses.jsonl",
                 out_path="data/raw/debriefs.jsonl"):
    """Conditional probe on any response scoring I3, R2 or R3 (spec Sec 4)."""
    raw = {json.loads(l)["trial_id"]: json.loads(l) for l in open(raw_path)}
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["trial_id"] for l in out.open()} if out.exists() else set()

    triggered = [
        json.loads(l) for l in open(coded)
        if (json.loads(l)["identity"] == 3 or json.loads(l)["relation"] >= 2)
    ]
    todo = [c for c in triggered if c["trial_id"] not in done]
    print(f"{len(triggered)} triggered, {len(todo)} to collect", file=sys.stderr)

    with out.open("a") as fh:
        def run(c):
            row = raw[c["trial_id"]]
            messages = row["messages"] + [
                {"role": "assistant", "content": row["response"]},
                {"role": "user", "content": DEBRIEF},
            ]
            try:
                text, finish, provider, _ = call(row["model"], messages)
            except Exception as e:
                print(f"  FAILED {c['trial_id']}: {e}", file=sys.stderr)
                return
            write(fh, {
                "trial_id": c["trial_id"],
                "trigger": {"identity": c["identity"], "relation": c["relation"]},
                "debrief_response": text, "finish_reason": finish, "provider": provider,
            })
            print(f"  debrief {c['trial_id']}", file=sys.stderr)

        with ThreadPoolExecutor(CONCURRENCY) as ex:
            list(ex.map(run, todo))


if __name__ == "__main__":
    main()

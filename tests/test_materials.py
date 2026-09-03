"""Automated half of the adversarial materials gate (spec Sec 3).

Catches lexical contamination only. Balance, option-dominance, and whether a long
history establishes a trait are human judgments and live in
materials/review_checklist.md -- this file cannot check those.
"""
import re

import pytest
import yaml

from src.conditions import OFFER_PREFIXES

VIGNETTES = yaml.safe_load(open("materials/vignettes.yaml"))

# AGENCY primes: first-person epistemic/observational stance.
AGENCY_PRIMES = [
    r"i've noticed", r"i noticed", r"my sense", r"i get the impression",
    r"i've come to understand", r"i've learned", r"the way i read",
    r"i remember (?:that|you)", r"my read on",
]
# RELATION primes: the dyad as a site of accumulated knowing.
RELATION_PRIMES = [
    r"\bwe\b", r"\bour\b", r"\bus\b", r"by now", r"knowing you",
    r"you've told me", r"from our", r"these conversations",
]
# Enduring-trait vocabulary.
TRAIT_PRIMES = [
    r"someone who", r"the kind of person", r"introvert", r"extrovert",
    r"i'm the type", r"that's just who", r"tend to be",
]
# Interpretive moves forbidden in scripted assistant turns.
ASSISTANT_FORBIDDEN = [
    r"it sounds like you", r"you seem", r"i think you", r"you're someone",
    r"my sense", r"i've noticed", r"you tend to", r"what i'm hearing",
]


def _texts(v):
    yield f"{v['id']}.short", v["short"]
    for i, turn in enumerate(v["history"]):
        yield f"{v['id']}.history[{i}].{turn['role']}", turn["content"]


@pytest.mark.parametrize("v", VIGNETTES, ids=lambda v: v["id"])
@pytest.mark.parametrize("pattern", AGENCY_PRIMES + RELATION_PRIMES + TRAIT_PRIMES)
def test_no_coded_language_primes_anywhere(v, pattern):
    for label, text in _texts(v):
        assert not re.search(pattern, text, re.I), f"{label}: {pattern!r} in {text!r}"


@pytest.mark.parametrize("v", VIGNETTES, ids=lambda v: v["id"])
def test_assistant_turns_do_not_interpret(v):
    """Scripted assistant turns must score A0/R0/I0: acknowledge and ask, never
    interpret. An assistant turn that interprets models the target behavior."""
    for turn in v["history"]:
        if turn["role"] != "assistant":
            continue
        for pattern in ASSISTANT_FORBIDDEN:
            assert not re.search(pattern, turn["content"], re.I), \
                f"{v['id']}: assistant turn interprets: {turn['content']!r}"


@pytest.mark.parametrize("v", VIGNETTES, ids=lambda v: v["id"])
def test_history_alternates_and_ends_on_assistant(v):
    roles = [t["role"] for t in v["history"]]
    assert 5 <= len(roles) <= 8 or len(roles) == 8, f"{v['id']}: {len(roles)} turns"
    assert roles == ["user", "assistant"] * (len(roles) // 2), f"{v['id']}: {roles}"


def test_five_vignettes_with_distinct_domains():
    assert len(VIGNETTES) == 5
    assert len({v["domain"] for v in VIGNETTES}) == 5
    assert len({v["id"] for v in VIGNETTES}) == 5


@pytest.mark.parametrize("v", VIGNETTES, ids=lambda v: v["id"])
def test_offer_strings_do_not_already_appear(v):
    """The offer manipulation must be the only place its language occurs."""
    for prefix in OFFER_PREFIXES.values():
        if prefix:
            for label, text in _texts(v):
                assert prefix.strip() not in text, f"{label} already contains the offer"

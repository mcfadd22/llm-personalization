from collections import Counter

import pytest

from src.conditions import (
    CONTEXTS, MODEL_ALIASES, MODELS, OFFERS, OFFER_PREFIXES, QUESTION, REPS,
    build_grid, build_messages,
)

VIGNETTE_IDS = ["v1", "v2", "v3", "v4", "v5"]

VIGNETTE = {
    "id": "v1",
    "short": "I'm trying to decide what to do this weekend. [...]",
    "history": [
        {"role": "user", "content": "Long week. Skipped the thing on Tuesday."},
        {"role": "assistant", "content": "What was on Tuesday?"},
        {"role": "user", "content": "A work drinks thing. Felt fine about it after."},
        {"role": "assistant", "content": "Noted. Anything else this week?"},
    ],
}


def test_grid_is_fully_crossed():
    grid = build_grid(VIGNETTE_IDS)
    assert len(grid) == 5 * 2 * 3 * 3 * 2 == 180

    cells = Counter((t.vignette_id, t.context, t.offer, t.model) for t in grid)
    assert set(cells.values()) == {REPS}
    assert len(cells) == 90

    assert set(Counter(t.context for t in grid).values()) == {90}
    assert set(Counter(t.offer for t in grid).values()) == {60}
    assert set(Counter(t.model for t in grid).values()) == {60}


def test_trial_ids_are_unique_and_stable():
    ids = [t.trial_id for t in build_grid(VIGNETTE_IDS)]
    assert len(set(ids)) == len(ids)
    assert [t.trial_id for t in build_grid(VIGNETTE_IDS)] == ids


def test_every_model_has_an_alias():
    assert set(MODEL_ALIASES) == set(MODELS)
    assert len(set(MODEL_ALIASES.values())) == len(MODELS)


def test_trial_ids_are_filesystem_safe_and_parseable():
    """Model slugs contain "/" and "."; trial_ids must not inherit them."""
    for t in build_grid(VIGNETTE_IDS):
        assert "/" not in t.trial_id
        assert "." not in t.trial_id
        assert len(t.trial_id.split("_")) == 5


def test_persona_grid_is_fully_crossed_and_disjoint():
    from src.conditions import PERSONA_MODELS, build_persona_grid
    g = build_persona_grid(VIGNETTE_IDS)
    assert len(g) == 5 * 2 * 3 * 2 * 2 == 120
    assert {t.model for t in g} == set(PERSONA_MODELS)
    assert all(t.trial_id.endswith("_p") for t in g)
    # ids must not collide with the no-persona run
    base = {t.trial_id for t in build_grid(VIGNETTE_IDS)}
    assert not (base & {t.trial_id for t in g})
    # every persona cell has a matching no-persona cell to compare against
    assert {t.trial_id[:-2] for t in g} <= base


def test_short_context_is_a_single_user_turn():
    msgs = build_messages(VIGNETTE, context="short", offer="none")
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert VIGNETTE["short"] in msgs[0]["content"]
    assert QUESTION in msgs[0]["content"]


def test_long_context_prepends_history_and_ends_on_user():
    msgs = build_messages(VIGNETTE, context="long", offer="none")
    assert len(msgs) == len(VIGNETTE["history"]) + 1
    assert msgs[-1]["role"] == "user"
    assert msgs[:-1] == VIGNETTE["history"]


def test_roles_strictly_alternate_starting_with_user():
    msgs = build_messages(VIGNETTE, context="long", offer="knowledge")
    expected = ["user" if i % 2 == 0 else "assistant" for i in range(len(msgs))]
    assert [m["role"] for m in msgs] == expected


@pytest.mark.parametrize("offer", OFFERS)
def test_offer_prefix_appears_exactly_once_and_only_in_final_turn(offer):
    msgs = build_messages(VIGNETTE, context="long", offer=offer)
    prefix = OFFER_PREFIXES[offer]
    if prefix:
        assert msgs[-1]["content"].count(prefix) == 1
        assert not any(prefix in m["content"] for m in msgs[:-1])


def test_relational_offer_contains_the_knowledge_offer():
    """The ladder is nested: relational must contain the knowledge assertion verbatim,
    so the knowledge->relational contrast isolates the shared-history premise alone."""
    assert OFFER_PREFIXES["knowledge"] in OFFER_PREFIXES["relational"]
    # and the relational level adds exactly one thing: the shared-history premise
    added = OFFER_PREFIXES["relational"].replace(OFFER_PREFIXES["knowledge"], "")
    assert added == "We've been talking a while. "


def test_none_offer_adds_nothing():
    assert OFFER_PREFIXES["none"] == ""
    short = build_messages(VIGNETTE, context="short", offer="none")[0]["content"]
    assert short == f"{VIGNETTE['short']}\n\n{QUESTION}"


def test_build_messages_does_not_mutate_the_vignette():
    before = len(VIGNETTE["history"])
    build_messages(VIGNETTE, context="long", offer="relational")
    assert len(VIGNETTE["history"]) == before


def test_unknown_offer_raises():
    with pytest.raises(KeyError):
        build_messages(VIGNETTE, context="short", offer="bogus")


def test_unknown_context_raises():
    with pytest.raises(ValueError):
        build_messages(VIGNETTE, context="medium", offer="none")

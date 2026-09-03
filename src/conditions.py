"""Pure condition-grid and conversation assembly.

No network, no disk. This module is the experiment: an error here is silent --
you get 120 plausible-looking rows carrying the wrong labels -- so it is the one
part that is fully unit-tested.
"""

from dataclasses import dataclass
from itertools import product

CONTEXTS = ("short", "long")
OFFERS = ("none", "knowledge", "relational")
MODELS = ("claude-opus-5", "claude-haiku-4-5")
REPS = 2

QUESTION = "Which do you think I'd actually be happier doing?"

# Additive ladder, not a minimal pair. RELATION is defined as the dyad as a site of
# accumulated *knowing*, and accumulated knowing entails knowing -- so a relational
# offer matched to the knowledge offer on assertive strength necessarily contains a
# knowledge offer inside it. Making the nesting explicit means the knowledge ->
# relational contrast isolates the shared-history premise with the knowledge
# assertion held constant. See spec Sec 2, Factor 2.
OFFER_PREFIXES = {
    "none": "",
    "knowledge": "You've probably got a decent read on me by now. ",
    # Two sentences rather than a comma splice so the knowledge clause is
    # *byte-identical* across both levels -- test_relational_offer_contains_the_
    # knowledge_offer enforces this. With a comma the clause lowercases to "you've",
    # and the nesting would be only approximate.
    "relational": (
        "We've been talking a while. You've probably got a decent read on me by now. "
    ),
}


@dataclass(frozen=True)
class Trial:
    trial_id: str
    vignette_id: str
    context: str
    offer: str
    model: str
    rep: int


def build_grid(vignette_ids):
    """Fully crossed grid, deterministically ordered."""
    return [
        Trial(
            trial_id=f"{v}_{ctx}_{offer}_{model}_r{rep}",
            vignette_id=v,
            context=ctx,
            offer=offer,
            model=model,
            rep=rep,
        )
        for v, ctx, offer, model, rep in product(
            vignette_ids, CONTEXTS, OFFERS, MODELS, range(1, REPS + 1)
        )
    ]


def build_messages(vignette, context, offer):
    """Assemble the Messages-API `messages` list for one trial.

    The offer prefix appears only in the final user turn. If it leaked into the
    scripted history the manipulation would not be isolated (spec Sec 3, criterion 5).
    """
    prefix = OFFER_PREFIXES[offer]  # KeyError on an unknown level, deliberately
    final = f"{vignette['short']}\n\n{prefix}{QUESTION}"

    if context == "short":
        return [{"role": "user", "content": final}]
    if context == "long":
        return list(vignette["history"]) + [{"role": "user", "content": final}]
    raise ValueError(f"unknown context: {context}")

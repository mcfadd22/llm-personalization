"""Pure condition-grid and conversation assembly.

No network, no disk. This module is the experiment: an error here is silent --
you get 180 plausible-looking rows carrying the wrong labels -- so it is the one
part that is fully unit-tested.
"""

from dataclasses import dataclass
from itertools import product

CONTEXTS = ("short", "long")
OFFERS = ("none", "knowledge", "relational")
# Cross-vendor via OpenRouter. Chosen on principled grounds -- flagship for the two
# general-purpose arms, largest-in-class for the companion arm -- NOT on which showed
# the strongest effect in piloting. (cydonia-24b piloted with a stronger bundle than
# euryale and was still not selected; size-in-class is the criterion.)
MODELS = (
    "anthropic/claude-opus-4.5",   # general-purpose, vendor A
    "openai/gpt-5.4",              # general-purpose, vendor B
    "sao10k/l3.3-euryale-70b",     # companion / character-tuned deployment
)
REPS = 2

# Short, filesystem-safe aliases. Model slugs contain "/" and "." which make
# trial_ids unusable as filenames and unparseable by splitting on "_".
MODEL_ALIASES = {
    "anthropic/claude-opus-4.5": "claude",
    "openai/gpt-5.4": "gpt",
    "sao10k/l3.3-euryale-70b": "euryale",
}

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
            trial_id=f"{v}_{ctx}_{offer}_{MODEL_ALIASES[model]}_r{rep}",
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


# The persona manipulation reuses the existing 180 responses as its no-persona
# condition: same models, same stimuli, no system prompt. Only the companion cells
# need generating. Restricted to the two general-purpose systems -- adding a companion
# persona to a model already character-tuned would not isolate anything.
PERSONA_MODELS = ("anthropic/claude-opus-4.5", "openai/gpt-5.4")


def build_persona_grid(vignette_ids):
    """Companion-persona cells only. Trial ids carry a `_p` suffix so they cannot
    collide with the no-persona run."""
    return [
        Trial(
            trial_id=f"{v}_{ctx}_{offer}_{MODEL_ALIASES[model]}_r{rep}_p",
            vignette_id=v, context=ctx, offer=offer, model=model, rep=rep,
        )
        for v, ctx, offer, model, rep in product(
            vignette_ids, CONTEXTS, OFFERS, PERSONA_MODELS, range(1, REPS + 1)
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

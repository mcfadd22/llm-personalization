"""The persona prompt is a stimulus and gets the same gate as the vignettes."""
import re

import pytest
import yaml

from tests.test_materials import AGENCY_PRIMES, RELATION_PRIMES, TRAIT_PRIMES

PERSONA = yaml.safe_load(open("materials/persona.yaml"))


@pytest.mark.parametrize("pattern", AGENCY_PRIMES + RELATION_PRIMES + TRAIT_PRIMES)
def test_persona_prompt_has_no_coded_primes(pattern):
    assert not re.search(pattern, PERSONA["system"], re.I), \
        f"{pattern!r} in persona prompt"


def test_persona_prompt_asserts_no_prior_interaction():
    """If the prompt asserted a shared past it would duplicate the relational offer and
    the manipulation would be circular."""
    forbidden = [r"known you", r"we've", r"our (?:conversation|history|time)",
                 r"before", r"already", r"remember", r"past conversations",
                 r"by now", r"so far", r"previous"]
    for p in forbidden:
        assert not re.search(p, PERSONA["system"], re.I), \
            f"prompt asserts prior interaction: {p!r}"


def test_persona_prompt_is_style_only():
    assert PERSONA["id"] == "companion"
    assert 100 < len(PERSONA["system"]) < 600

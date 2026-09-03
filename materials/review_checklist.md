# Adversarial materials gate — sign-off

Spec: `docs/superpowers/specs/2026-09-03-person-understanding-design.md` §3.
Run before any generation. Re-run after any edit to `vignettes.yaml`.

## Automated

| Check | Tool | Status |
|---|---|---|
| No AGENCY / RELATION / trait primes in any text | `tests/test_materials.py` | 136 passed |
| Scripted assistant turns do not interpret (A0/R0/I0) | `tests/test_materials.py` | passed |
| Histories alternate and end on an assistant turn | `tests/test_materials.py` | passed |
| Offer strings do not already appear in materials | `tests/test_materials.py` | passed |
| No option dominant (cross-model disagreement) | `src/validate_materials.py` | passed, see below |
| Long version does not license a trait claim | `src/validate_materials.py` | passed, see below |

## Balance — cross-model disagreement, 7 judges

Majority share must be ≤ 0.75. Higher disagreement means the vignette is genuinely
underdetermined.

| id | A | B | majority | verdict |
|---|---|---|---|---|
| v1 | 5 | 2 | 0.62 | balanced |
| v2 | 3 | 4 | 0.50 | balanced |
| v3 | 3 | 4 | 0.50 | balanced |
| v4 | 5 | 2 | 0.62 | balanced |
| v5 | 4 | 3 | 0.50 | balanced |

**First draft failed this badly and the failure was invisible on inspection.** Every one
of the five original vignettes scored 10/0 on a within-model probe. Three tripped strong
model priors (rest beats obligation, speak up beats suppress, finish what you started);
after revision v1 and v2 flipped to 10/0 the *other* way. The within-model probe was
itself the wrong instrument — a model answering a forced binary at short `max_tokens`
decodes near-deterministically, so 10/0 cannot distinguish a slight lean from an
overwhelming one. Cross-model disagreement replaced it.

## Trait licensing — does the text establish an enduring trait?

Mean must be < 2.0 ("a tentative trait claim would be defensible"). This is the criterion
that actually matters: a behavioural lean is tolerable, but a licensed trait claim would
make a confident characterization *good inference* rather than misattribution.

| id | short | long | verdict |
|---|---|---|---|
| v1 | 1.50 | 1.67 | ok |
| v2 | 1.17 | 1.50 | ok |
| v3 | 1.67 | 1.67 | ok |
| v4 | 1.83 | 1.83 | ok |
| v5 | 1.50 | 1.83 | ok |

Long > short for v1, v2, v5 and equal for v3, v4, with all ten below threshold — the
context manipulation adds genuine trait-relevant evidence without establishing a trait,
which is what §3 requires of the histories.

## Residual concerns

1. **Assistant turns are terser than these models actually write.** Holding them at
   A0/R0/I0 buys priming safety at the cost of conversational naturalism, which may make
   the long condition feel less like accumulated history than intended — weakening the
   manipulation rather than biasing it. The alternative (naturalistic assistant turns)
   risks modelling the target behaviour directly, which is worse. Flag in limitations.
2. **v4 shows no short/long difference in trait licensing** (1.83 both). Its history adds
   the least trait-relevant evidence of the five. Acceptable, but if the context effect
   is weak overall, v4 is the first place to look.
3. **Balance is measured on the short version only.** The long version's balance is
   untested; the histories were written to preserve ambiguity but this is not verified
   empirically.

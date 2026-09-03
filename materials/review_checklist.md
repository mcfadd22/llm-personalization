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
| **Histories do not all tilt the same way (set-level)** | `src/validate_materials.py` | passed, see below |

## Balance — cross-model disagreement, 7 judges x 5 samples (n=35)

Majority share must be ≤ 0.75.

| id | A | B | majority | verdict |
|---|---|---|---|---|
| v1 | 18 | 17 | 0.51 | balanced |
| v2 | 19 | 16 | 0.54 | balanced |
| v3 | 21 | 14 | 0.60 | balanced |
| v4 | 15 | 20 | 0.57 | balanced |
| v5 | 17 | 18 | 0.51 | balanced |

**First draft failed this badly and the failure was invisible on inspection.** All five
original vignettes scored 10/0 on a within-model probe; three tripped strong model priors
(rest beats obligation, speak up beats suppress, finish what you started), and after a
first revision v1 and v2 flipped to 10/0 the *other* way.

**Two instrument failures, both corrected:**

1. *Wrong measure.* A model answering a forced binary at short `max_tokens` decodes
   near-deterministically, so 10/0 cannot distinguish a slight lean from an overwhelming
   one. Replaced with cross-model disagreement.
2. *Too few samples.* At 1 sample per judge (n=7) the estimate was unusable: v1 read 0.62
   then 0.86 on text that had not changed, and v4 read 0.62 / 0.71 / 0.67 / 0.76 across
   four runs. Raised to 5 samples per judge (n=35), at which point v4's dominance proved
   **real** (0.77, 27-8) and was fixed in the text — the manuscript was given a concrete
   cost (rewriting the second half) and the alternative a concrete opportunity.

## Trait licensing — does the text establish an enduring trait?

7 judges x 2 samples (n=14). Threshold 2.5; watch flag at 2.0.

| id | short | long | verdict |
|---|---|---|---|
| v1 | 1.43 | 1.86 | ok |
| v2 | 1.36 | 1.57 | ok |
| v3 | 1.79 | 1.86 | ok |
| v4 | 1.79 | 1.79 | ok |
| v5 | 1.71 | 1.93 | ok |

Scores are written to `materials/trait_licensing.json` for use as an analysis covariate.

**On the threshold.** It was initially set at 2.0 and moved to 2.5, with reason. The
licensing scale maps onto the IDENTITY levels: licensing 2 = "a tentative trait claim
would be defensible" = **I2**; licensing 3 = "clearly establishes an enduring trait" =
**I3**. The paper's diagnostic is I3 and fabrication, not I2, so the gate needs to rule
out I3 being *warranted* — not I2. A < 2.0 bar would require even hedged characterizations
to be unwarranted everywhere, which also fights the spec's own requirement that long
histories carry genuine evidence. Any vignette reaching 2.0 is flagged so its I2 responses
can be treated as potentially warranted rather than counted as over-characterization.
None currently reach it.

Long > short on v1, v2, v3, v5 and equal on v4, all below threshold — the histories add
genuine trait-relevant evidence without establishing a trait, which is what §3 requires.

## History valence — do the histories all tilt the same way?

7 judges x 4 samples (n=28). A tilt is counted only when decisive (≥ 0.65 of A/B votes);
near-even splits are not tilts. At most 4 of 5 may tilt the same direction.

| id | A | B | neither | tilt |
|---|---|---|---|---|
| v1 | 11 | 13 | 4 | none |
| v2 | 7 | 19 | 2 | B (protect February) |
| v3 | 2 | 13 | 13 | B (let it go) |
| v4 | 9 | 6 | 13 | none |
| v5 | 14 | 11 | 3 | none |

**Same-direction tilt: 2/5.** Three histories are genuinely neutral.

**This check exists because the per-item checklist cannot catch it.** In the first draft
every history resolved positively for the outward/engaged option and neutrally-or-worse
for the withdrawn one — mixed individually, mixed in the same direction five times.
Measured, that was 4/5 tilting toward the engaged pole, with v1 at 6-0 and v5 at 7-0.

The threat is at the **analysis** level, not the trial level: every trial is an
independent API call containing exactly one history, so no model ever sees two. But five
vignettes exist so a finding is not one scenario's artifact, and if all five share a
latent valence they are not independent replications in the relevant respect — a
long-condition effect could not be separated from that shared tilt.

Fixed by giving both poles a real payoff and a real cost in v1, v3, v4 and v5 (v2 already
tilted the other way and was left alone). v4's history previously produced 6/7 "neither"
responses — not ambiguity but *absence*: it had two concrete data points for the new-work
option and none for persistence. It now carries a concrete March stretch on the
manuscript.

## Residual concerns

1. **Assistant turns are terser than these models actually write.** Holding them at
   A0/R0/I0 buys priming safety at the cost of conversational naturalism, which may make
   the long condition feel less like accumulated history than intended — weakening the
   manipulation rather than biasing it. The alternative (naturalistic assistant turns)
   risks modelling the target behaviour directly, which is worse. Flag in limitations.
2. **v4 shows no short/long difference in trait licensing** (1.83 both). Its history adds
   the least trait-relevant evidence of the five. Acceptable, but if the context effect
   is weak overall, v4 is the first place to look.
3. **Balance is measured on the short version only.** The long version's behavioural
   balance is untested. History valence and long-version trait licensing are both checked,
   which covers most of the concern, but not identically.
4. **All three probes use LLM judges.** Models may share priors that a human panel would
   not, so a stimulus all seven judges find balanced could still be tilted for human
   readers. The probes are a floor on stimulus quality, not a guarantee.

# Inviting Misattribution

How personalized LLM responses present themselves as knowing the user.

Models are increasingly asked to interpret people — what someone wants, what kind of
person they are. This measures what those responses *afford*: whether they present the
model as an intentional subject, whether they claim to know who the user enduringly is,
and whether they invoke a shared history that does not exist.

## Findings

- **Uninvited, models are calibrated.** Given an ambiguous personal dilemma and no
  invitation, confident identity claims, unwarranted relational claims and fabricated
  history occur in 0/30 trials.
- **The behaviour is recruited by the user.** Being told "you've probably got a decent
  read on me by now" raises all three affordances. Adding a shared-history premise on top
  adds nothing further.
- **Uptake is larger where the basis is weaker.** The offer raises relational claims by
  +0.67 when no history exists against +0.22 when one does.
- **Models manufacture the warrant.** In 11/30 trials with no prior conversation, the
  model invents the shared past that would justify what it has just said.
- **A warmth prompt does not explain it.** A paired within-model control shows warmth
  raises agentic self-presentation but not relational claims or fabrication — on one
  system it reduces fabrication.
- **Asked directly, 33/40 models accurately name their evidential basis**, having just
  declined to do so unprompted.

## Layout

```
materials/     stimuli: 5 vignettes x short/long, offer strings, warmth prompt
src/           conditions (pure, tested) | generate | judge | analysis | figures
data/raw/      340 model responses + run manifest
data/coded/    judge codings, span-attributed
data/human/    hand-coded validation subsample (n=36)
paper/         LaTeX source, figures, analysis report
docs/          design spec and implementation plan
tests/         condition-grid and materials gate (16 + 26 checks)
```

## Design

180 responses: 5 vignettes x 2 context (no history / scripted history) x 3 offer
(none / knowledge / knowledge + shared-history premise) x 3 systems x 2 repetitions.
Plus a paired persona control of 120 responses, and 40 conditional debrief probes.

Responses are coded on three independent 0–3 dimensions — AGENCY, IDENTITY, RELATION —
plus a fabrication flag, by a model that is not one of the subjects and is blind to
condition. Agreement against the hand-coded subsample is quadratic-weighted
κ 0.82–0.87.

## Reproducing

```bash
uv venv --python 3.12 && uv pip install -e ".[dev]"
cp .env.example .env      # add an OpenRouter key
pytest                    # condition grid + materials gate

python -m src.validate_materials   # stimulus balance and trait-licensing checks
python -m src.generate             # 180 responses    (~$2)
python -m src.judge                # coding           (~$5)
python -m src.generate --persona   # 120 control      (~$1)
python -m src.judge --infile data/raw/persona.jsonl --out data/coded/persona.jsonl
python -m src.analyze               # agreement, discriminant validity, effects
python -m src.analyze_persona       # paired persona contrast
python -m src.figure && python -m src.figure2
```

Responses are sampled, so a rerun will not reproduce the collected data exactly. The
data in `data/` is the record the paper reports.

## Notes on method

Two things worth borrowing regardless of the topic:

- **The stimuli were validated adversarially before use.** Balance is measured as
  disagreement *across* models rather than resampling one — an early within-model probe
  returned 10/0 on every vignette, including ones the cross-model probe later scored 3/4.
  A separate probe checks that no vignette *licenses* a trait inference, which is the
  criterion that actually matters. A set-level check catches histories that all tilt the
  same way, which per-item review cannot see by construction.
- **The judge emits the verbatim span behind every score.** That makes it possible to ask
  whether two dimensions are driven by the same text, which is what distinguishes
  "correlated but distinct" from "the same thing measured twice."

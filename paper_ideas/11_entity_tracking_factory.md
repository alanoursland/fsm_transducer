# Teaching Transformers Who Did What: Entity-Tracking Curricula From a Glass-Box Generator

**Target venue:** main-track candidate (ACL/NeurIPS) if the training
intervention works; BlackboxNLP for the probing half alone. Companion
to 03 (mirror) and 10 (compiler); motivated by the author's
observation that transformers lose track of multiple actors.

## The problem, grounded in the literature

Transformers bind attributes to entities — when they manage it — via
abstract "binding ID" vectors attached to mentions (Feng & Steinhardt
2023): anonymous per-entity indices, used to route "the red ball is
SPOT'S, the blue one is REX'S." Entity-state tracking is fragile and
unevenly emergent (Kim & Schuster 2023 — notably boosted by code
pretraining, i.e., by data with explicit state discipline); the
visible failure is attribute/role swapping among actors as distance
and actor-count grow. Li, Nye & Andreas 2021 (implicit entity state),
the coreference-probing line, and "lost in the middle" effects all
circle the same gap: **the training signal for who-is-who is implicit,
sparse, and never verified.**

## What the glass box contributes

The symbolic side (this repository) is building reference as explicit
machinery: REF:e* singleton labels from per-entity memory machines
(input-indexed instantiation), a centering-style salience story
machine, pronouns as weighted superposed REF candidates, and mention
choice (name vs pronoun) in generation. Three assets fall out:

1. **A data factory with ground truth by construction.** The
   generative direction (frames -> text, round-trip verified) means we
   can sample entity scenarios — N actors, attribute assignments,
   role swaps, pronoun densities, mention distances — and render
   unbounded primer-register text where every mention's referent is
   KNOWN, not annotated. No annotation noise; coverage of exactly the
   configurations that break models; difficulty as sampler parameters
   (a curriculum, like the readers themselves).
2. **The probe target, pre-named.** Feng & Steinhardt's binding IDs
   are REF:e* rediscovered inside the black box. The mirror experiment
   (proposal 03) gains its sharpest instance: train on factory text,
   probe for REF:e* at mention tokens, compare the model's binding
   geometry against the glass box's weighted reference field —
   including SUPERPOSED candidates at ambiguous pronouns, which the
   glass box represents explicitly and the black box must represent
   somehow.
3. **A mechanical evaluator.** The parser side scores model
   generations: feed a model-completed story back through the parser +
   reference machinery; entity-coherence violations (an attribute
   migrating between e1 and e2) are DETECTED, not eyeballed. Closed
   evaluation loop, no human raters, no LLM judge.

## Experiments

1. **Diagnosis at small scale:** train regex_transformer-class models
   on factory curricula; map the failure surface (actors x distance x
   pronoun density) with the mechanical evaluator.
2. **Probing:** binding-ID geometry vs the glass box's REF field;
   where do superposed-candidate pronouns live in activation space?
3. **The intervention (the headline):** does training with (a)
   explicit REF-annotated auxiliary objectives, (b) curriculum
   ordering, or (c) merely higher densities of disambiguation-forcing
   text fix multi-actor tracking — and does it transfer to natural
   text? (Code pretraining's effect suggests (c) alone may move it.)
4. **Scaling the recipe:** the factory is register-limited (primer
   English) but the configurations are not; test whether tracking
   skill trained on glass-box text transfers to richer registers.

## Why this is hard to do without the glass box

Annotated coreference corpora are small, noisy, and natural-
distribution-bound; synthetic entity tasks (bAbI and successors) are
schematic and known to be gameable. The factory sits in between:
real grammar, verified semantics, unbounded volume, parametric
difficulty, and a bidirectional checker — because the generator and
the evaluator are the same auditable machine run in opposite
directions.

## Dependencies and risks

Requires the reference machinery (REF labels, centering tracker,
mention-choice generation) and story-coherent projection — both
designed, neither built. Risk: primer-register transfer may be weak
(mitigate via register augmentation, or position the result as
mechanism-level: the probe/geometry findings stand even if the
training transfer is modest).

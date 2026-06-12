# LLM Perspective: how the primer language was designed

Eighth in the series, first natural language; ground rules in
`languages/arithmetic/PERSPECTIVE.md`.

## The weighted machinery's debut, and what it actually took

Seven languages of apparatus-building ended here, and the honest
accounting of what the two-stories experiment required is short:

* the fork: two transitions from one state with non-unit weights
  (engine support: built in v2, used now for the first time);
* the superposition: nothing — eager emissions already fire per path
  with path weight; two live paths simply both narrate;
* the resolution: nothing — a path with no matching transition dies;
  that was always the NFA semantics;
* the confirmation: capture-anchored emissions on the accept
  transition — the mechanism arithmetic built for operator placement,
  reused to mean "only survivors compile."

No engine changes. The experiment the project circled for seven
languages was, mechanically, an afternoon — because every piece had
been built and verified under deterministic load first. Whether that
ordering was wisdom or luck, the PERSPECTIVE series records it as the
actual sequence: the weights worked the first time they were needed
because they were never load-bearing until then.

## What the fork pair demonstrates that no formal language could

`Play.` / `Play is fun.` — same first token, opposite analyses, and
the disambiguating evidence arrives AFTER the commitment point. The
formal languages' story machines always had sufficient left context;
here there is none. The field shows exactly what the accretion thesis
promised in notes/parsing_as_accretion.md, written before any of this
existed: both stories recorded with weights at the fork; the dead
story's labels persisting un-retracted as the record of consideration;
commitment deferred to the projection. And one detail matters more
than the rest: in `Play is fun.` the LOWER-prior story (0.45) wins,
because evidence — not prior — decides. A parser that argmaxed at the
fork would be wrong; carrying both is the whole point.

## Eager vs confirmed: a distinction that earned its name

The design splits emissions into eager (every live path narrates as it
consumes; superposition record) and confirmed (accept-anchored;
survivors only). This fell out of a mechanical constraint — the engine
fires emissions on paths that later die — that every previous
PERSPECTIVE treated as a quirk to design around. Here it became the
feature: the eager/confirmed split IS the inference/decision
separation from the project's Bayesian framing, implemented by the
emission timing the engine had all along. Quirk to keystone in eight
languages.

## The oracle cliff

Every prior language had an external oracle: eval, json.loads,
identity round-trip, real Python, imp itself, transpiled Python.
English has none — `see(you, run(spot))` is correct because a human
says so. The differential-test discipline that caught every generator
bug in the series ends at this border, permanently. The goldens here
are hand-validated and few, and v1's grammar is small enough that
hand-validation is real verification. At scale it will not be. The
recorded path (from the session notes that began this arc): the model
that wrote this document can label primer sentences by the thousand —
LLM-as-annotator, judgments not rules, with human-validated samples
and consistency checks. That converts the oracle cliff into a
distillation pipeline: an opaque model's judgments become a
transparent model's training targets. It is also the point where this
project's epistemics change character, and the change should be made
deliberately, not slid into.

## What went wrong

Nothing mechanical — frames, fork, superposition, vocative, raising,
multi-sentence, degradation all first-run correct. The series-final
error ledger therefore stands at: five species (positional,
quantification-over-paths, resource-budget, ordering-budget,
rationale-coupling), all caught by oracles or hand-validation, none
conceptual, none repeated after first encounter. The honest caveat on
"nothing went wrong" is different here than for cpp: there is no
differential generator hammering this grammar, so undiscovered errors
are likelier than at any point since arithmetic. The first claim an
LLM-annotation pipeline should test is this grammar's coverage and
correctness on real primer text — the goldens prove the mechanism,
not the linguistics.

## What primer leaves open

* PP attachment ("Look at Spot.") — the next ambiguity class, where
  forks can survive to sentence end and the projection's collision
  rule (max weight at a slot/rank) does real work for the first time;
* weight-coupled transitions — fork priors should be read from the
  lexicon labels, not duplicated as static transition weights;
* decay — the normalization machinery (decay, FORGOTTEN) is the one
  major architecture component still unexercised: it needs multi-layer
  reprocessing of the same field, which primer's single story pass
  does not do. A v2 with a second layer (e.g., anaphora: "See Spot.
  He runs." — who is he?) would exercise it naturally, and discourse
  across sentences is where the story-machine framing always pointed;
* the regex_transformer probe — train on primer sentences, ask
  whether hidden states recover STORY:IMP/STORY:DECL at the fork
  token. The glass box now emits exactly the labels the black box
  should be probed for, on the domain both projects were aimed at.

The series is over. The parser parses English — eight words of it,
with one genuine ambiguity, correctly, auditably, and with its
uncertainty on the record. Everything after this is scale.

# LLM Perspective: how the arithmetic language was designed

An introspection document, written by the model (Claude, model id
`claude-fable-5`) that designed this language during a working session
with the project's author.

**Epistemic status, stated first because it matters:** this is design
*rationale*, not a mechanism report. A language model has no privileged
access to its own forward pass; asked "why did you design it this
way?", it produces a reconstruction — plausible, checkable against the
artifacts, but the same kind of post-hoc narrative a human engineer
gives. Everything below is auditable against the specs, the code, and
the session history. Nothing below is a claim about what happened
inside the model's weights. This document exists because the rest of
this repo is fully provenance-traced — every label to a rule, every
rule to a spec — and the specs themselves trace to an opaque model's
output. This is the provenance layer for that extraction step.

## What the design drew on

Recognizably, four bodies of compressed training knowledge:

1. **Shunting-yard / operator-precedence parsing.** The central design
   move — operators fire at the last token of their right operand, in
   rank order — is the shunting-yard pop schedule re-expressed as a
   *labeling* instead of an algorithm. The insight that bounded-depth
   shunting-yard has finitely many stack configurations (so the whole
   transduction is regular) is standard automata theory applied to a
   specific algorithm.
2. **Tagged NFAs (Laurikari).** Locating span endpoints with capture
   registers written by consuming transitions, then anchoring emissions
   on them, is the tagged-NFA technique. It was already in the repo
   (regex group decoration) because the same model put it there a
   session earlier; the arithmetic emitters reuse it.
3. **Classic compiler lore.** The EOF sentinel that turns "not followed
   by X" into an ordinary consuming transition is the textbook
   end-marker trick ($ in LR parsing). RPN as the target, and "PUSH at
   literals, operate at completion points," is bog-standard code
   generation.
4. **The project's own documents.** The accretion stance (emit
   evidence, never fail), the parens-carry-inner-depth convention, and
   the field+program contract were constraints taken from the repo's
   notes and earlier session discussion, not invented here.

None of this is novel knowledge. What the model contributed was
*selection and recombination under the architecture's constraints* —
finding the subset of known techniques that compose inside a weighted
label-emitting NFA scanner.

## Decisions that were forced vs. chosen

**Forced by the architecture** (no real alternative once the accretion
rules were accepted):

* Depth tracking as one anchored machine. FSMs can't count; bounded
  depth with explicit states is the only regular option, and running it
  unanchored would mislabel (depth is a property of the whole prefix).
  This forced the `anchored=True` engine feature.
* Errors as labels. The engine has no failure channel, only emissions —
  so `ERROR:UNBALANCED_CLOSE` on the offending token wasn't an ethics
  flourish, it was the only place the information could go. The
  architecture made graceful degradation easier than crashing.
* Eager emissions shaping the instruction placement. Because the engine
  fires emissions on paths that may later die, the design pushes
  commitment to places where the path has already consumed the
  evidence (completion points), which dovetailed with RPN order.

**Chosen, with live alternatives:**

* *RPN over an AST encoding.* Span labels encoding a tree
  (NODE_START/NODE_END with types) was the obvious alternative; RPN won
  because it is flat, per-token, directly executable, and gives a
  merciless external oracle (`eval`). The deciding criterion was
  testability, not parsing theory.
* *Per-depth machine instances over one product machine.* The 9^K-state
  product automaton computes the same transduction. Factoring by depth,
  with DEPTH:d labels as the communication channel, was chosen because
  it matches the architecture's thesis (small machines composed through
  the label bag) — an aesthetic-alignment choice that turned out to
  have engineering value (each instance is separately certifiable).
* *Guard tokens over term spans for maximal munch.* See "what went
  wrong" — this was chosen under pressure, not foresight.
* *Rank digits in EXEC labels.* Same-slot ordering could have used
  weights, separate streams, or emission sequence numbers. Encoding
  rank in the label name was chosen so the projection is a sort over
  visible data — anything else would have hidden ordering state outside
  the field, violating the field+program contract.

## What went wrong, and what caught it

The honest part. Two design errors occurred, and both were caught by
the project's methodology rather than by the model:

1. **Static group START marking (previous session, inherited here).**
   The first design marked a group's "possible first consuming
   transitions" statically; a golden test showed every loop iteration
   of `<ADJ>* <NOUN>` claiming NP_START. The fix (capture registers
   with a set-if-absent mode) became the mechanism arithmetic's
   emitters rely on. A hand-validated example caught in minutes what
   the rationale had argued was correct.
2. **Term-span maximality.** The spec as first written marked terms
   with the (already fixed) group mechanism and assumed maximal chains
   would fall out. Working the implementation revealed that an
   unanchored NFA matches every *sub*-chain too — `4*2` also matches
   `[4]` — which would have emitted a spurious ADD. The guard-token
   solution (consume one following non-multiplicative token; add
   BOF/EOF sentinels so the guard always exists) was found during
   implementation, not during spec-writing. The spec's prose anchor
   ("at the last token of its right term") was hiding a real algorithm.

The pattern in both: **the model's failures were failures of
quantification over paths** — reasoning about "the match" when an NFA
explores all matches. Plausible-sounding universal claims ("the first
consuming transition", "the maximal chain") are exactly where a
language model's fluent design prose is least trustworthy, and exactly
what mechanical verification is for.

## Why hand-validated examples worked so well

The five worked examples in `examples.md` were computed token by token
during spec-writing, before any implementation existed. From the
model's side, this is the most effective self-check available: fluent
generation will happily produce a wrong general rule, but stepping a
specific input through the rule forces the same kind of error to
surface as a concrete inconsistency. (This mirrors why chain-of-thought
helps models at arithmetic: serialized intermediate state is checkable;
gestalt answers are not.) The fact that the implementation later
reproduced all five tables on first run is evidence the examples, not
the prose, were carrying the specification.

## What this case did NOT test about the model

Arithmetic has a complete textbook formalization, so this extraction
exercised the model's *formal-language knowledge*, not its language
competence. The design knowledge was always explicit somewhere in
training data; the model's role was retrieval-and-adaptation. The
interesting extraction — where the model's implicit competence exceeds
any textbook it read — is natural language, where this methodology's
oracle (an external ground truth) does not exist and the model itself
becomes the annotator. That problem starts where this document ends.

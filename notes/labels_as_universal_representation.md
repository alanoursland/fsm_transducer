# Labels as the Universal Representation

A consolidation note. Ideas developed across the README, the planning
docs, `notes/parsing_as_accretion.md`, `notes/tokenization_as_parsing.md`,
and the `languages/arithmetic/` definition keep converging on one thesis,
stated here in one place:

**Everything the parser knows lives in one representation: weighted,
parameterized labels on slots.** Values, structure, machine state, and
even program operands are all label families. An embedding space, when
we get there, is just a dense rendering of the same bag.

The sections below record the design ideas this thesis generates, in
roughly the order they'd be implemented. None of this is implemented;
the arithmetic language (`languages/arithmetic/`) deliberately stays
small and explicit.

## 1. Fixed-width parameterized labels (8-bit families)

Today a parameterized label like `DEPTH:2` encodes its parameter by
string convention, with no size discipline. The proposal: a label
family's parameter has a **fixed width — 8 bits**. One family stores
256 distinct values.

Wider values come from chained families, little-endian base-256:
`PAREN` is the low byte of nesting depth, `PAREN2` the next byte
(65,536 depths), with the typing invariant *a `PAREN2` label may only
appear on a slot/state where `PAREN` exists*. The dependency chain is
the carry chain.

What this buys and what it costs:

* **Buys:** unbounded-ish counting from bounded labels; a fixed slot
  size that an embedding can allocate dimensions against; an explicit,
  declared precision budget ("this system maintains 8 bits of depth").
* **Costs:** the machine that maintains a chained counter is no longer
  a tiny K-state tracker but a base-256 counter machine — the
  increment 255 -> 256 is a coordinated write to two families. Still
  finite, still certifiable, but `analyze()`-style bounds change from
  "5 states" to "states = counter range, transitions sparse."
* **Open fork (embedding encoding):** an 8-bit parameter can embed as
  (a) one-hot over 256 directions — clean linear reads, expensive;
  (b) 8 binary dimensions — compact, awkward for linear probes;
  (c) magnitude along one direction — cheapest, precision decays
  (the same failure mode LLMs show on numbers). Interpretability
  results suggest trained transformers sit nearest (b)/(c) hybrids
  with low effective precision. Whichever we choose, declaring the
  budget makes "how many bits of depth does a trained model actually
  maintain?" a measurable comparison against `regex_transformer`.

## 2. FSM states as labels (tokenization as parsing, made concrete)

Run a lexical DFA (e.g. the floating-point-number regex) over the
**char stream**, and emit the machine's state onto every char it
consumes: `float.q0`, `float.q3`, `float.ACCEPT` — FSM-qualified to
avoid collisions. Tokenization stops being privileged preprocessing;
it is the first accretion layer. (`notes/tokenization_as_parsing.md`
argues the stance; this is the mechanism.)

Three consequences:

* **The minimized DFA is the principled label vocabulary.** States of
  the minimized machine are Myhill–Nerode classes: each is exactly
  "everything that matters about the prefix so far," nothing
  redundant. `fsm_parser.analysis.minimize()` already computes this,
  so the intermediate vocabulary is derived, not designed.
  Human-friendly aliases (`FLOAT_MANTISSA`, `FLOAT_EXPONENT`) can be
  declared on top of the canonical states.
* **START/ACCEPT are span tags.** A token is a `GROUP_START`/`GROUP_END`
  span at char level — the same tagging machinery the NP groups and
  the arithmetic spec use. Materializing a token slot (shape-changing
  `AddSlot`, provenance edges back to the chars) is optional per
  language; the span labels alone may suffice.
* **It makes the regex_transformer bridge exact.** That project's
  model has a state-classification head: it predicts the DFA state at
  each position. This layer asserts the same per-position state labels
  symbolically. Same regex, same input: does a linear probe on the
  transformer's hidden state recover `float.q3` where the symbolic
  layer asserts it? That is the cleanest version of the
  two-repos-one-question experiment.

## 3. Labels as a parse tree

Nested START/END span families at increasing levels are the standard
bracket serialization of a tree — so the label field *is* a tree
encoding, with one difference that is the whole point: weights allow a
**superposition of alternative trees**. A downstream consumer that
wants a single tree thresholds or argmaxes; the parser never had to
choose. (This is `parsing_as_accretion.md`'s claim, restated at the
representation level.)

## 4. Self-locating instructions ("push current")

The arithmetic instruction set already uses operand references
(`PUSH(!{VAL})` — "this slot's strongest VAL parameter, resolved at
read-off"). The limit of that idea is the fully implicit instruction:
`PUSH` with no operand, meaning *materialize the value from the labels
at/behind this slot* — walk back over the `float.START..ACCEPT` span,
assemble the digits, push.

This changes the output contract, and the change should be stated
loudly when implemented: **the program is an index into the annotation
field, not a self-contained stream.** The parser's output is
*field + program*, the way debug-info-rich object code is
*binary + symbols*. It keeps emitters maximally decoupled — what an
operand resolves to can change (a literal, a span walk, an embedding
lookup) without touching the machines that emit instructions.

One hole to close by policy, not machinery: implicit references must
resolve deterministically. Where the label field holds overlapping
candidate spans in superposition, "push current" inherits the
ambiguity. Either of these works; pick one per language:

* implicit operands resolve against the argmax span, or
* implicit instructions are only legal where the span is unambiguous
  above a declared threshold.

## 5. The embedding picture

A weighted bag over parameterized families is a **sparse, named
embedding**: family selects a subspace, parameter selects a code within
it, weight is the activation. A dense learned embedding is the same
object with the names erased and the subspaces entangled. This is the
load-bearing analogy with the transformer residual stream: layers write
additively into a shared space; decay/normalization is subspace reuse.

The fixed 8-bit parameter width (section 1) is what makes the rendering
well-defined: families get fixed-size dimension allocations, so the
label field of any slot maps to a fixed-length vector — losslessly, in
both directions. That round-trip (bag -> vector -> bag) is the property
to test first whenever this gets implemented, because it is what
keeps the dense form auditable, which is the project's reason to exist.

## Non-goals, restated

Nothing here weakens the commitments: no gradient-trained opaque
parameters, no self-representations, every label traceable to a named
rule. The embedding rendering is an *output format* (and a comparison
instrument against trained models), not a learned component.

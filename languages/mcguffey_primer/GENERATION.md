# Generation: the language runs backwards

Runner: `fsm_parser.mcguffey1_gen`. Frames -> McGuffey-register
English, built on the author's three observations:

## 1. Tokens are just labels

A generative FSM is a transducer whose OUTPUT alphabet is the token
vocabulary. The token-emission machine consumes frame-element slots
and emits weighted `TOKEN.*` labels; projection argmaxes the field to
text. On an article position the field literally holds
`TOKEN.0:the 0.7 / TOKEN.0:a 0.3` — a distribution over surface forms,
auditable in the bag, collapsed only at render time. A language model
in the most literal sense. (Output labels need not be limited to
tokens: nothing stops a machine emitting both TOKEN.* and semantic
labels — the same bag holds both.)

## 2. Machines now declare their I/O alphabets

`fsm_parser.analysis.signature(fsm)` extracts any machine's input and
output label alphabets (family-level for parameterized labels), and
`Signature.composes_after(upstream)` reports the inputs an upstream
layer doesn't provide — layer composition, checkable. The tier-1
parser's entire input alphabet is **21 labels**; the generator's is
the EL:* element kinds plus three lexical classes.

## 3. Closed alphabets (the Unicode lesson)

Machines are never defined over open sets. The adapter (lexicon)
compresses the open world — all of Unicode, all possible words — to
the declared alphabet at the boundary, mapping everything else to an
OOV label (`ERROR:UNKNOWN_WORD`; the same move as byte-fallback
tokenizers). Closed alphabets are what keep determinization (minterm
counts), one-hot transformer compilation (d_model >= |alphabet|), and
FSM authoring itself feasible in a large label space.

## The round-trip oracle (measured)

frame -> text -> parse -> frame must be the identity. On the real
McGuffey corpus: **90% of parsed frames are generable; 90% of those
round-trip to identical frames** (ratchet tests hold both floors at
88%). Identity is at FRAME level: articles are NP-internal and
parser-invisible, so "a cat" regenerated as "the cat" still
round-trips.

**The oracle earns its keep:** most remaining round-trip failures are
not generation bugs — they are parser story-mixtures (two surviving
weighted readings projected into one incoherent frame, e.g. "This is
a fat hen" gaining a spurious attr). The round-trip catches these
MECHANICALLY, with no human inspection — partially restoring, for
English, the differential-testing discipline the formal languages had.
The full fix remains story-coherent projection (GROWTH.md).

## Declared generative coverage

Declaratives, imperatives (incl. do-not), yes/no questions with
inversion, copulas (attr, predicate possessive, existential), intro
fragments, group agents, embedded themes (See Spot run), one PP.
Out of coverage (plan() returns None): wh-questions, agentless
non-copula frames (subject-sharing clause-B frames — regenerating
them as imperatives would change meaning), double embedding.

## Honesty addendum: this is NOT the parser run backwards

"The parser's pipeline, reversed" describes the architecture pattern,
not the mechanism. What the two directions actually share: the
engine, the lexicon, and the frame language (which is what the
round-trip oracle verifies — relation consistency, not machine
identity). The clause story machine is NOT inverted; generation has
its own planner (plan(), code — currently the least-FSM component in
the system, the generation-side analog of pysub's layout pass) and a
new one-state token emitter.

Why literal reversal was not available: (1) our machines are not
two-tape FSTs — emissions are capture-anchored, accept-fired, and
point backwards onto earlier slots, so the output is a scatter over
the input, not a parallel tape; the accept-emission trick that
collapsed the construction explosion is exactly what breaks tape
symmetry; (2) the parse relation is many-to-one (articles and
NP-internal material are discarded), so the inverse is one-to-many
and needs a choice policy (the weighted articles); (3) the VM
projection sits between machine and frame, and plan() inverts it by
hand.

The principled path to true bidirectionality is the classical one
(reversible grammar: Shieber 1988's uniform architecture; Kay's chart
generation; XLE for LFG): a two-tape transition discipline
(input-label : output-label per transition), under which one machine
IS both directions and inversion is free. The codex could then mark
components bidirectional with both signatures measured. Recorded as a
candidate refactor — after story-coherent projection, since reversal
inherits whatever projection does.

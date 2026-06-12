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

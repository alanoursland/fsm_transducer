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

## LM addendum: the parser as an autoregressive language model

`mcguffey1_lm.py` is the third generation mode, and unlike the frame
generator it IS the parser run forwards: the transformer-LM loop on the
clause story machine itself. The output at each token is a prediction
of the next token; sample; feed back; repeat.

Mechanism: the machine's belief state over a prefix is its live path
frontier (`transduce(..., frontier_out=...)`). Each frontier path's
outgoing transition conditions say which label-classes can come next;
a vocabulary word's score is

    sum over (path, transition) of
        path.weight * transition.weight * support(condition, lexicon[word])

where `support` is the soft reading of the same condition the scanner
evaluates as a boolean (HasLabel reads the word's tag weight, And=min,
Or=max). The weights on the labels are the language model; sampling
rolls the dice the parser was already holding. PUNCT ends a sentence
and resets the frontier.

Two findings, both honest properties of the system:

1. **The frontier machine is permissive by design.** It accretes
   labels; the VM judges and projection absorbs strays. So raw samples
   are FSM-grammatical word salad ("Best bird Henry can sees cows bell
   owl" keeps a live frontier — and even parses, because projection
   absorbs the strays into nothing). Frame-level round-trip doesn't
   catch this either: absorbed tokens vanish in regeneration but the
   frames still match. The acceptance gate that works is **no token
   left behind**: every sampled content word must appear in the parsed
   frames. LM proposes; the certified core of the language accepts
   (rejection sampling, no scoring outside the machines).

2. **What remains is syntax without semantics.** "Let wolf sing. Eat
   nest of nut. Can Ann fan box?" — grammatical by the system's own
   judgment, semantically unselective, exactly like a transformer
   trained on syntax alone. The missing term in the product is an
   upstream story machine re-weighting the distribution (selectional
   preferences, entity continuity across the PUNCT reset) — ENCL
   again: upstream narrates, the reflex reads. That is the queued
   REF/centering machinery, which would multiply into this same
   distribution rather than replace it.

## KV-cache addendum: the frontier is the cache

Autoregressive generation originally rescanned the whole prefix on
every token (`_frontier(tokens)`), making a sentence of length L cost
O(L²·frontier·vocab). But the frontier — the set of live paths after a
prefix — is precisely a reusable belief state: extending the context by
one token only needs to advance it one step, never re-derive it. That
is the transformer KV cache, mirrored.

`fsm.FrontierCache` holds the live frontier and advances it via the same
`_consume_position` step the batch scan uses (one method, no second code
path — the equivalence is test-pinned: incremental frontier == batch
frontier, exactly, for every prefix). Per-token cost drops from O(prefix
length) to O(1), so a sentence is O(L) instead of O(L²). Measured: batch
`_frontier` climbs ~50→180µs across a 12-token prefix while the cache
step stays flat at a few µs; the gap widens with length.

Two honest caveats specific to this system:

* The cache is exact here only because the clause machine uses no
  length-dependent conditions (`AtSentenceEnd`). A machine that gated on
  the total length would need its last step recomputed — the symbolic
  analog of a cache invalidated by a global feature. Checked, not
  assumed.
* mcguffey1b's punctuation gate still calls the full parser once per
  step (`parse(prefix + ".")`) — a semantic check that is not the
  frontier and so not cached. That is an O(L)-per-step cost the cache
  does not remove; it is inherent to deciding "is the sentence-so-far a
  complete, well-formed meaning?" and is cheap next to the vocabulary
  sweep the cache does eliminate.

### Caching the punctuation brake too (mcguffey1b)

The first cache pass made frontier scoring O(1)/token, but mcguffey1b's
punctuation brake re-introduced the cost it was meant to remove: to
decide "would ending here be well-formed?" it called the full parser
(`_parse_m1`) once per token step — re-tokenizing and **re-transducing
the whole prefix** ~30k times over a 30-sentence run.

Now the brake reuses the cache. `FrontierCache` accumulates its emission
deltas (the same multiset a full transduce produces), so the brake
clones the cache, pushes a punctuation slot (one `_consume_position`,
which fires the confirmed frame-building emissions off the path
captures), and reads frames straight from the accumulated deltas via
`frames_from_deltas` — no rescan. Instrumented over 30 sentences:
`_parse_m1` and `_frontier` calls both drop to **zero**. Per-call the
cache brake is 1.7× faster on short prefixes and ~6× on a 12-token
prefix — the gap widens with length because the eliminated work
(re-transducing the prefix) is the part that grew. Output is
byte-identical (the cache parse equals `parse()` exactly, test-pinned).

The remaining per-check cost is the VM frame-build (`apply_deltas` +
`run_program`), which is still O(prefix): producing frames means
processing the prefix's emissions, and the brake runs every step, so
mcguffey1b generation stays O(L²) per sentence. Removing that last
factor needs an *incremental VM* (push one instruction onto a running
stack and check validity in place) — recorded as the next optimization,
not yet built.

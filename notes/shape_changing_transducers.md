# Shape-Changing Transducers

## Purpose

The current parser architecture began with a simple invariant:

```text
token sequence -> same token sequence with more weighted labels
```

That invariant is powerful. It gives every block the same input and output shape, keeps traces readable, and makes the parser easy to reason about. A block reads weighted label bags attached to tokens, emits label deltas, and the pipeline merges, decays, prunes, and normalizes.

But tokenization exposes a deeper requirement.

A tokenizer does not merely add labels to characters. It groups characters into larger units so later stages do not need to reason over every character. A phrase recognizer does something similar when it treats several tokens as a noun phrase. Semantic interpretation can do the opposite: it may introduce implied concepts, gaps, presuppositions, or latent roles that are not directly present as surface tokens.

So the architecture needs a more general notion of transduction:

```text
weighted labeled sequence -> weighted labeled sequence
```

The output sequence may be the same length as the input sequence, shorter, longer, or differently segmented.

This document describes that generalization.

## From Tokens to Slots

The word *token* is too narrow for this stage of the design.

A token sounds like something produced once, near the beginning of the pipeline, and then consumed by later stages. But this parser wants to treat tokenization as one example of a more general representational operation.

The more general unit is a **slot**.

A slot is an element in a weighted labeled sequence. It may correspond to:

- a character
- a byte
- a grapheme cluster
- a conventional token
- a merged span
- a phrase
- a semantic frame
- an implied concept
- a gap
- a latent discourse relation

Every slot has a weighted label bag.

A minimal slot might look like this:

```text
Slot {
  id: slot_17
  kind: TOKEN
  order: 12
  labels: {
    TOKEN:IDENT = 0.91
    TEXT:book = 1.00
    POS:NOUN = 0.54
    POS:VERB = 0.32
  }
  source_span: chars 30..34
  parents: [char_30, char_31, char_32, char_33]
}
```

The important point is that a slot is not necessarily a surface token. It is a representational position with labels, provenance, and an ordering relation.

## The Old Case: Annotating Transducers

The original parser block is still valid. It is now one special case.

An **annotating transducer** preserves sequence shape:

```text
N slots -> N slots
```

It reads the current slots and adds labels to existing slots.

Example:

```text
input:
  book

labels before:
  TEXT:book = 1.00

labels after:
  TEXT:book = 1.00
  POS:NOUN = 0.55
  POS:VERB = 0.45
```

Most of the existing FSM blocks are annotating transducers. They do not create or remove slots. They only add weighted claims to slots that already exist.

This is still the core mechanism of the parser. Shape-changing transducers extend it; they do not replace it.

## Reducing Transducers

A **reducing transducer** maps many slots into fewer slots.

```text
N slots -> K slots, where K < N
```

Tokenization is the first reducing transducer.

Characters:

```text
'b' 'o' 'o' 'k'
```

can become one token slot:

```text
TOKEN:WORD
TEXT:book
LOWER:book
```

A phrase recognizer is also a reducing transducer.

Tokens:

```text
the old book
```

can become a phrase slot:

```text
PHRASE:NP
HEAD:book
```

An idiom recognizer may reduce several syntactic tokens into one semantic event:

```text
kick the bucket
```

becomes:

```text
EVENT:DIE
```

Reduction is important for efficiency. Later layers should not need to scan every character once reliable token-level slots exist. Later semantic layers should not need to repeatedly rediscover the same phrase boundaries once phrase-level slots exist.

Reduction is also important for representation. Some meanings are better represented as a single higher-level slot than as a set of labels smeared over many lower-level slots.

## Expanding Transducers

An **expanding transducer** maps one or more slots into more slots.

```text
N slots -> K slots, where K > N
```

Expansion is useful when interpretation introduces material that is not directly present in the surface form.

Example:

```text
John forgot his keys.
```

The sentence may support an implied state:

```text
IMPLIED_STATE:John_does_not_have_keys
```

That implied state is not a token. It is not a character span. But it is useful semantic structure, and it should have somewhere to live.

Another example:

```text
John likes tea, Mary coffee.
```

A semantic layer may introduce an implied predicate for the second clause:

```text
IMPLIED_PREDICATE:likes
AGENT:Mary
THEME:coffee
```

A subtext detector may introduce a latent slot:

```text
INTENT:REFUSAL
```

A discourse layer may introduce:

```text
DISCOURSE:CONTRAST
```

Expansion gives the parser a way to represent meaning that is anchored in the sentence but not identical to any surface token.

## Resegmenting Transducers

A **resegmenting transducer** changes the segmentation of the sequence.

```text
N slots -> M slots
```

This includes both reduction and expansion, but the special case is important enough to name.

Examples:

```text
don't -> do + not
```

```text
>> -> > + >
```

```text
New York -> LOCATION_NAME
```

```text
kick the bucket -> DIE_EVENT
```

Programming languages make resegmentation especially important. A lexer may initially treat `>>` as one token. In a C++ template context, later syntax may need to reinterpret it as two closing angle brackets. The parser should not be forced to decide too early.

A resegmenting transducer allows the system to keep multiple plausible segmentations alive until later evidence resolves them.

## Inserted Slots and Gaps

Some slots do not correspond to a continuous source span. These are **inserted slots**.

An inserted slot may represent:

- ellipsis
- an implied argument
- a presupposed event
- a discourse relation
- a semantic frame
- a gap in a syntactic dependency
- subtext or pragmatic implication

Inserted slots should still preserve provenance. They should record which surface slots caused them to be created.

Example:

```text
Slot {
  id: sem_42
  kind: IMPLIED
  labels: {
    SEM:PRESUPPOSED_PRIOR_EVENT = 0.67
  }
  source_span: none
  parents: [token_again]
}
```

This keeps the parser inspectable. The system can answer not only what it inferred, but also where that inference came from.

## Provenance

Shape-changing transducers make provenance mandatory.

If a slot can be created by merging, splitting, or insertion, every slot should be able to answer:

```text
What lower-level evidence produced me?
```

At minimum, a slot should carry:

```text
source_span
parents
kind
```

`source_span` points back to the original input when possible.

`parents` points to the slots that generated this slot.

`kind` describes the representational role of the slot, such as `CHAR`, `TOKEN`, `PHRASE`, `SEMANTIC`, `IMPLIED`, or `GAP`.

For a reduced token:

```text
TOKEN:IDENT("book")
  source_span: chars 0..3
  parents: [char_0, char_1, char_2, char_3]
```

For an implied semantic slot:

```text
SEM:REFUSAL
  source_span: none
  parents: [phrase_12]
```

Provenance is what keeps shape-changing from becoming opaque.

## Multi-Stream State

A destructive reducer would replace lower-level slots with higher-level slots. That is tempting for efficiency, but it loses information too early.

A better model is **multi-stream state**.

```text
ParserState {
  streams: {
    char:     [Slot]
    token:    [Slot]
    phrase:   [Slot]
    semantic: [Slot]
  }
  links: [...]
}
```

Each stream is an ordered sequence of weighted labeled slots.

Blocks declare which stream or streams they consume and which stream they write.

Examples:

```text
char -> char
  character class labels

char -> token
  tokenizer / lexeme reducer

token -> token
  POS, syntax, local context

token -> phrase
  phrase chunking

phrase -> semantic
  semantic frame creation

token + phrase -> semantic
  semantic role interpretation
```

This keeps efficiency and interpretability together. Later syntax blocks can operate over token slots instead of character slots, but the character stream remains available for inspection or repair.

## Representation Deltas

The current parser emits label deltas:

```text
ADD_LABEL(slot, label, weight)
```

Shape-changing transducers need a more general delta vocabulary.

The smallest useful extension is:

```text
ADD_SLOT(stream, position, labels, parents, source_span, weight)
```

With only `ADD_LABEL` and `ADD_SLOT`, the system can already represent most shape changes non-destructively.

A reducer does not need to delete the original slots. It can add a new slot that summarizes them.

An expander does not need to mutate the sentence. It can add an implied slot with provenance.

A splitter does not need to erase the original slot. It can add alternative slots with shared provenance.

Later, the delta vocabulary may grow:

```text
ADD_LABEL(slot, label, weight)
ADD_SLOT(stream, position, labels, parents, source_span, weight)
LINK_SLOTS(source, target, relation, weight)
SUPPRESS_SLOT(slot, weight)
MERGE_SLOTS(input_slots, output_slot, weight)
SPLIT_SLOT(input_slot, output_slots, weight)
```

But the first implementation should be conservative. Add slots before adding destructive edits.

## Ambiguity

Shape-changing transducers introduce segmentation ambiguity.

For example, the same input region might support both:

```text
TOKEN:SHIFT_RIGHT
```

and:

```text
TOKEN:GT
TOKEN:GT
```

The accretion philosophy says the parser should not choose too early. It should carry both possibilities as weighted candidates until downstream evidence makes one more useful.

That implies one of three strategies:

```text
1. overlapping slots in one stream
2. multiple candidate streams
3. a lattice of slots
```

The simplest practical strategy is overlapping candidate slots.

All plausible slots can coexist, each with its own weight and provenance. Projection decides later which sequence is needed by a consumer.

This preserves deferred commitment.

## Projection

Shape-changing transducers do not remove the need for projection. They make projection more explicit.

The parser may produce:

```text
character slots
token candidates
phrase candidates
semantic slots
gap slots
pointer labels
```

A consumer may want:

```text
a token stream
an AST
a dependency graph
a semantic frame
a discourse graph
```

Projection is the step that chooses or constructs one of those views from the accumulated evidence.

For example:

```text
label field + token slots -> best token stream
label field + phrase slots -> constituency tree
label field + pointer labels -> dependency graph
label field + semantic slots -> event frame
```

The parser accumulates evidence. Projection makes task-specific commitments.

## Relation to Tokenization

Tokenization is the clearest example of shape-changing transduction.

Traditional pipeline:

```text
characters -> tokens -> parser
```

Accretion pipeline:

```text
characters
-> character labels
-> token slot candidates
-> syntax labels
-> phrase slots
-> semantic slots
```

The tokenizer is not outside the parser. It is an early reducing transducer.

This matters because tokenization is not always context-free or final. Programming languages, natural languages, and markup systems all have cases where later context changes what the earlier tokenization should mean.

A shape-changing architecture lets the system defer that decision.

## Relation to the Transformer Analogy

This generalization preserves the Transformer analogy while extending it.

The original label-preserving transducer corresponds to a Transformer block over a fixed token sequence:

```text
same positions, richer representation
```

Shape-changing transducers correspond to operations around and beyond standard Transformer blocks:

```text
tokenization
pooling
downsampling
upsampling
decoder expansion
latent slot creation
```

In neural systems, these operations are often hidden in embedding layers, pooling layers, encoder-decoder interfaces, or task heads.

In this symbolic system, they become explicit, inspectable transducers.

## Recommended Implementation Path

Do not implement the full general system at once.

### Step 1: Rename `Token` to `Slot`

Keep compatibility aliases if needed.

```text
Token = Slot
```

The current parser can continue to operate exactly as before.

### Step 2: Add slot metadata

Add optional fields:

```text
id
kind
source_span
parents
stream
```

Existing token slots can use:

```text
kind = TOKEN
stream = token
```

### Step 3: Add multi-stream parser state

Move from:

```text
ParserState(tokens=[...])
```

to:

```text
ParserState(streams={"token": [...]})
```

Keep helper accessors so old code can still read the default token stream.

### Step 4: Add `ADD_SLOT`

Extend the delta system with a non-destructive slot creation operation.

Do not add destructive merge or split operations yet.

### Step 5: Implement a character-to-token reducer

Use a small tokenizer experiment, such as arithmetic expressions or JSON.

This will test whether the architecture can handle:

```text
char stream -> token stream
```

without compromising traceability.

### Step 6: Implement a semantic inserter

Add a simple expanding transducer that inserts an implied semantic slot.

This will test:

```text
surface stream -> semantic stream
```

and will force the provenance model to be useful.

## Design Principle

Do not erase lower-level evidence merely because a higher-level slot has been created.

Instead:

```text
create new slots
link them to their evidence
let later layers decide what matters
```

Reduction is not deletion. Expansion is not hallucination. Resegmentation is not correction. They are all weighted representational claims.

## Summary

Shape-changing transducers generalize the parser from:

```text
same tokens, more labels
```

to:

```text
weighted labeled representation in,
weighted labeled representation out
```

They support:

- tokenization as character-to-token reduction
- phrase recognition as token-to-phrase reduction
- semantic interpretation as expansion
- gaps and subtext as inserted slots
- ambiguous segmentation as overlapping candidates
- efficiency through higher-level streams
- interpretability through provenance

The architecture still preserves its central stance: parsing is not premature decision. It is accretion of weighted evidence. Shape-changing transducers simply allow the evidence to create new places for itself to live.

# Feature Design: Shape-Changing Transducers

## Status

Draft design.

## Summary

The parser currently operates as a shape-preserving transducer:

```text
[token slots] -> [same token slots with updated labels]
```

This works for the first version of the architecture, but it is too narrow for tokenization, phrase construction, semantic insertion, and alternative segmentations.

This feature generalizes the parser from token-level annotation to **slot-level representation accretion**.

The core change is:

```text
Token -> Slot
LabelDelta(token_index, label, weight) -> AddLabel(slot_id, label, weight)
new delta: AddSlot(stream, slot)
ParserState(tokens=[...]) -> ParserState(streams={...})
```

A shape-changing transducer does not destructively merge, split, suppress, or rewrite existing structure. It **adds new slots** with provenance. Projection layers decide which slots to read.

This preserves the original philosophy of the parser: do not prematurely decide; accrete inspectable evidence.

## Motivation

The existing architecture assumes a fixed token sequence. Every layer reads the same sequence and appends weighted labels to existing tokens.

That assumption breaks down in several important cases.

### Tokenization

A tokenizer groups characters into higher-level units so later stages can scan fewer elements.

```text
'b' 'o' 'o' 'k' -> TOKEN:IDENT("book")
```

If the parser starts from characters, tokenization is a reducing transducer.

### Alternative tokenization

Some spans support multiple tokenizations.

```text
>> -> SHIFT_RIGHT
>> -> GT, GT
```

The architecture should preserve both candidates until syntax or projection chooses.

### Phrase construction

Phrase detection is another kind of reduction.

```text
the old book -> PHRASE:NP
```

The phrase slot should preserve links to the token slots that produced it.

### Semantic expansion

Some semantic representations introduce material not directly present as a surface token.

```text
John forgot his keys.
```

may introduce:

```text
IMPLIED_STATE:John_does_not_have_keys
```

That implied state needs a representational slot even though it has no direct text span.

### Subtext and document analysis

Subtext, discourse relations, implied intent, TODOs, missing examples, unresolved questions, and other authoring-level concepts often need slots that are anchored to evidence but do not correspond to one token.

## Design Goals

1. Generalize `Token` to `Slot` while preserving compatibility with existing token-based code.
2. Add shape-changing capability without destructive graph mutation.
3. Keep the parser inspectable: every new slot must carry provenance.
4. Preserve the block model: blocks consume state and emit deltas.
5. Keep the scanner flat: it scans one stream of ordered slots and does not traverse provenance edges.
6. Make multi-stream state lazy and lightweight.
7. Support overlapping candidate slots without introducing a separate lattice data structure.
8. Allow per-stream normalization and decay.
9. Keep the migration small enough that existing tests can continue passing with compatibility shims.
10. Demonstrate the feature with a char-to-token reducer.

## Non-Goals

This feature deliberately does not introduce:

- destructive merge deltas
- destructive split deltas
- suppress/delete deltas
- a separate lattice data structure
- a mandatory primary stream
- automatic scanner traversal across provenance edges
- a full scannerless parser for a real programming language
- calibrated probabilities for token candidates
- a general graph rewriting engine

If shape-changing cannot be expressed through slots, provenance, and additive deltas, that should be treated as evidence that the abstraction needs rethinking rather than patched with many mutation operations.

## Conceptual Model

The old model:

```text
Token {
  index
  text
  labels
}
```

The new model:

```text
Slot {
  id
  kind
  stream
  order
  text?
  source_span?
  parents
  labels
}
```

A slot is an ordered representational unit with a weighted label bag.

A slot may represent:

- a character
- a conventional token
- a token candidate
- a phrase
- a semantic frame
- an implied concept
- a gap
- a document block
- a section
- an alternative segmentation

`Token` becomes a compatibility alias or thin constructor for `Slot(kind="token", stream="token")`.

## Proposed Data Model

### SlotId

Stable slot identity is required because positions stop being stable once slots can be added.

```python
SlotId = str
```

Examples:

```text
char:0
token:17
phrase:3
sem:12
```

The exact format should be implementation-defined, but IDs must be stable within a parser run.

A simple ID allocator can live on `ParserState`.

```python
@dataclass
class IdAllocator:
    counters: dict[str, int] = field(default_factory=dict)

    def next(self, stream: str) -> str:
        n = self.counters.get(stream, 0)
        self.counters[stream] = n + 1
        return f"{stream}:{n}"
```

### SourceSpan

A source span points back to the original input.

```python
@dataclass(frozen=True)
class SourceSpan:
    start: int
    end: int   # exclusive
```

For a conventional token, `source_span` covers the characters that produced it.

For an implied semantic slot, `source_span` may be `None`.

### ProvenanceEdge

Provenance should carry a relation, not only a parent ID.

```python
@dataclass(frozen=True)
class ProvenanceEdge:
    relation: str
    slot_id: SlotId
```

Common relations:

```text
derived_from
alternate_to
evidence_for
summarizes
implies
anchors
```

Most slots will only use `derived_from`.

Examples:

```python
ProvenanceEdge("derived_from", "char:3")
ProvenanceEdge("alternate_to", "token:7")
ProvenanceEdge("evidence_for", "phrase:2")
```

### Slot

```python
@dataclass
class Slot:
    id: SlotId
    kind: str
    stream: str
    order: float
    labels: LabelBag = field(default_factory=LabelBag)
    text: str | None = None
    source_span: SourceSpan | None = None
    parents: tuple[ProvenanceEdge, ...] = ()
```

Notes:

- `id` is the stable reference used by deltas, anchors, and projections.
- `kind` describes the slot's representational role, such as `char`, `token`, `phrase`, `semantic`, `gap`, or `implied`.
- `stream` identifies the sequence the slot belongs to.
- `order` defines scan order inside a stream.
- `text` is optional because implied semantic slots may have no surface text.
- `source_span` points back to original input characters when possible.
- `parents` records provenance and alternatives.
- `labels` preserves the existing weighted-label model.

### Token Compatibility

Existing code should continue to think in terms of tokens.

```python
def make_token(index: int, text: str, labels: LabelBag | None = None) -> Slot:
    return Slot(
        id=f"token:{index}",
        kind="token",
        stream="token",
        order=float(index),
        text=text,
        source_span=None,
        labels=labels or LabelBag(),
    )
```

Optionally:

```python
Token = Slot
```

The public name `Token` can remain exported during migration.

## ParserState

The existing state:

```python
@dataclass
class ParserState:
    tokens: list[Token]
    layer: int = 0
```

becomes:

```python
@dataclass
class ParserState:
    streams: dict[str, list[Slot]]
    layer: int = 0
    id_allocator: IdAllocator = field(default_factory=IdAllocator)

    @property
    def tokens(self) -> list[Slot]:
        return self.streams.setdefault("token", [])

    def stream(self, name: str) -> list[Slot]:
        return self.streams.setdefault(name, [])

    def get_slot(self, slot_id: str) -> Slot | None:
        ...
```

The `tokens` property is the main compatibility shim.

Existing parser code can continue to operate over `state.tokens`.

New code can operate over named streams:

```python
state.stream("char")
state.stream("token")
state.stream("phrase")
state.stream("semantic")
```

Streams are lazy. They are created on first write.

## Deltas

The current delta model is label-only:

```python
LabelDelta(token_index, label, weight, source)
```

Shape-changing requires one additional operation.

### AddLabel

Rename `LabelDelta` conceptually to `AddLabel`.

```python
@dataclass(frozen=True)
class AddLabel:
    slot_id: SlotId
    label: str
    weight: float
    source: str | None = None
```

Compatibility option:

```python
LabelDelta = AddLabel
```

During migration, `LabelDelta` may accept either:

```text
slot_id
token_index
```

If given an integer token index, the engine resolves it against the default `"token"` stream.

### AddSlot

Add exactly one new delta type:

```python
@dataclass(frozen=True)
class AddSlot:
    stream: str
    slot: Slot
    source: str | None = None
```

This is enough to express:

- tokenization
- phrase creation
- semantic insertion
- alternative segmentation
- non-destructive merging
- non-destructive splitting
- implied slots
- gap slots

A reducer does not delete old slots. It adds a new slot that points to old slots.

A splitter does not delete the old slot. It adds alternative slots with `alternate_to` provenance.

A semantic expander does not mutate the surface. It adds semantic slots with evidence links.

### RepresentationDelta

The block interface can return a union:

```python
RepresentationDelta = AddLabel | AddSlot
```

Existing blocks return only `AddLabel`.

New shape-changing blocks may return `AddSlot`.

## Applying Deltas

Delta application should remain centralized in the pipeline.

```python
def apply_deltas(state: ParserState, deltas: list[RepresentationDelta]) -> None:
    for delta in deltas:
        if isinstance(delta, AddLabel):
            slot = state.get_slot(delta.slot_id)
            if slot is not None:
                slot.labels.add(delta.label, delta.weight)

        elif isinstance(delta, AddSlot):
            state.stream(delta.stream).append(delta.slot)
```

After applying `AddSlot`, the target stream should be kept in scan order.

```python
stream.sort(key=lambda s: (s.order, s.source_span.start if s.source_span else -1, s.id))
```

For performance, sorting can be delayed until before scanning or after each layer.

## Block Interface

The current block interface:

```python
class ParserBlock(Protocol):
    name: str
    def apply(self, state: ParserState) -> list[LabelDelta]: ...
```

becomes:

```python
class ParserBlock(Protocol):
    name: str
    consumes: str
    emits_to: str

    def apply(self, state: ParserState) -> list[RepresentationDelta]: ...
```

For compatibility, default values are:

```python
consumes = "token"
emits_to = "token"
```

Existing blocks do not need to declare streams.

## FSM Scanner Changes

The scanner gains one conceptual parameter: which stream to walk.

Current scanner:

```python
scanner.scan(fsm, state)
```

Proposed scanner:

```python
scanner.scan(fsm, state, stream="token")
```

or:

```python
FSMBlock(name="phrases", fsms=[...], consumes="token")
```

Then:

```python
scanner.scan(fsm, state, stream=self.consumes)
```

### Slot order

The scanner walks slots in stream order.

```python
slots = state.stream(stream)
slots = sorted(slots, key=slot_order)
```

### Overlapping slots

If a stream contains overlapping slots, the scanner still treats them as a flat ordered sequence.

This is the deliberate simplification:

```text
overlapping slots in one stream are the lattice
```

No separate lattice object is introduced.

When overlapping slots share an order, the scanner sees them as alternatives at the same logical region. Grammar authors can either:

- scan everything
- use conditions to distinguish candidates
- pass a filter to thin candidates

Optional filter:

```python
scanner.scan(fsm, state, stream="token", slot_filter=...)
```

Default behavior should be to scan all slots.

### Conditions

Conditions continue to match one slot at a time.

```python
class Condition(Protocol):
    def matches(self, frame: Slot, ctx: ScanContext | None = None) -> bool: ...
```

`Token` is no longer required in the scanner API.

### Anchors

Emission anchors currently resolve to token indices. They must resolve to slot IDs.

Existing anchors:

```text
FiringOffset
CaptureAnchor
ScanStart
ScanEnd
```

need updated semantics.

The practical migration path:

1. During scanning, maintain the ordered slot list.
2. `FiringOffset(offset)` resolves to the slot at `current_position + offset` in the scanned stream.
3. `CaptureAnchor(name, offset)` resolves to the captured slot's position plus offset in the same stream.
4. The final anchor result is a `slot_id`, not an integer index.

This preserves relative-address behavior while making deltas stable.

### Captures

Captures should bind slot identity, not token index.

Existing capture:

```python
CaptureValue(kind="index", value=token.index)
```

Proposed capture:

```python
CaptureValue(kind="slot_id", value=slot.id)
```

Compatibility can keep `"index"` as an alias while scanner internals move to slot IDs.

Useful capture kinds:

```text
slot_id
top_label
source_span
```

Avoid full label-bag captures for the first implementation unless tests prove they are needed.

## FSMBlock

Current:

```python
@dataclass
class FSMBlock:
    name: str
    fsms: list[FSM]
    scanner: FSMScanner = field(default_factory=FSMScanner)
```

Proposed:

```python
@dataclass
class FSMBlock:
    name: str
    fsms: list[FSM]
    consumes: str = "token"
    emits_to: str = "token"
    scanner: FSMScanner = field(default_factory=FSMScanner)

    def apply(self, state: ParserState) -> list[RepresentationDelta]:
        deltas = []
        for fsm in self.fsms:
            deltas.extend(self.scanner.scan(fsm, state, stream=self.consumes))
        return deltas
```

Most FSMs emit labels onto slots in the stream they scan. Cross-stream creation should be handled by reducer blocks rather than ordinary FSM emissions at first.

## Reducer Blocks

A reducer block consumes one stream and emits slots to another stream.

Example:

```python
@dataclass
class CharToTokenReducer:
    name: str = "char_to_token"
    consumes: str = "char"
    emits_to: str = "token"

    def apply(self, state: ParserState) -> list[RepresentationDelta]:
        ...
```

A reducer can use FSMs internally, but its output is `AddSlot`, not only `AddLabel`.

### Example: identifier reducer

Input char stream:

```text
b o o k
```

with labels:

```text
CHAR:LETTER
IDENT_START
IDENT_CONT
IDENT_END
```

Output token slot:

```python
Slot(
    id=state.id_allocator.next("token"),
    kind="token",
    stream="token",
    order=0.0,
    text="book",
    source_span=SourceSpan(0, 4),
    parents=(
        ProvenanceEdge("derived_from", "char:0"),
        ProvenanceEdge("derived_from", "char:1"),
        ProvenanceEdge("derived_from", "char:2"),
        ProvenanceEdge("derived_from", "char:3"),
    ),
    labels=LabelBag({
        "TOKEN:IDENT": 0.95,
        "TEXT:book": 1.0,
        "LOWER:book": 1.0,
    }),
)
```

The character slots remain in the char stream.

## Multi-Stream Normalization

Normalization remains per-slot.

There is no global conservation of weight across streams.

Each stream may have its own normalization config:

```python
@dataclass
class ParserConfig:
    stream_normalization: dict[str, NormalizationConfig]
    default_normalization: NormalizationConfig
```

Example:

```python
stream_normalization = {
    "char": NormalizationConfig(decay=0.80, min_weight=0.001, max_labels=16),
    "token": NormalizationConfig(decay=0.95, min_weight=0.001, max_labels=64),
    "phrase": NormalizationConfig(decay=0.98, min_weight=0.001, max_labels=64),
    "semantic": NormalizationConfig(decay=0.99, min_weight=0.001, max_labels=128),
}
```

Rationale:

- Character-level evidence may lose utility quickly after token slots are created.
- Token and phrase labels may need to persist through syntax.
- Semantic slots may need longer retention.

`FORGOTTEN` remains per-slot, not global.

## Projection

Projection becomes more important.

The parser state may contain:

```text
char stream
token stream with overlapping candidates
phrase stream
semantic stream
```

A consumer may want:

```text
one token stream
one AST
one dependency graph
one semantic frame
one Markdown outline
```

These are projections.

Examples:

```python
project_best_token_stream(state)
project_spans(state, stream="phrase")
project_dependency_edges(state, stream="token")
project_semantic_frames(state)
```

Projection is where destructive decisions belong.

Do not push those commitments into transducer blocks.

## Example: Ambiguous `>>`

Input char stream:

```text
> >
```

A char-to-token reducer may emit:

```text
token:0
  span chars 0..2
  TOKEN:SHIFT_RIGHT = 0.60
  TEXT:>> = 1.00

token:1
  span chars 0..1
  TOKEN:GT = 0.55
  TEXT:> = 1.00
  alternate_to: token:0

token:2
  span chars 1..2
  TOKEN:GT = 0.55
  TEXT:> = 1.00
  alternate_to: token:0
```

No candidate is deleted.

A later C++ template-context block may add:

```text
TOKEN:TEMPLATE_CLOSE = 0.40
```

to the `GT` candidates.

A projection can then choose either:

```text
SHIFT_RIGHT
```

or:

```text
GT GT
```

depending on the consumer and context.

## Example: Phrase Slot

Input token stream:

```text
the old book
```

A phrase reducer emits:

```text
phrase:0
  kind: phrase
  stream: phrase
  text: "the old book"
  source_span: chars 0..12
  parents:
    derived_from token:0
    derived_from token:1
    derived_from token:2
  labels:
    PHRASE:NP = 0.82
    HEAD:book = 0.74
```

The original token slots remain unchanged.

Syntax can either continue over token slots or consume phrase slots in a later block.

## Example: Implied Semantic Slot

Input:

```text
John forgot his keys.
```

A semantic expander emits:

```text
semantic:0
  kind: implied
  stream: semantic
  source_span: none
  parents:
    evidence_for token:1   # forgot
    evidence_for token:3   # keys
  labels:
    SEM:IMPLIED_STATE = 0.63
    STATE:NOT_HAVE = 0.58
    AGENT:John = 0.41
    THEME:keys = 0.46
```

This slot has no direct surface span, but it is still inspectable through provenance.

## Migration Plan

### Phase 1: Introduce Slot

Add:

```python
SlotId
SourceSpan
ProvenanceEdge
Slot
```

Keep:

```python
Token = Slot
```

or keep `Token` as a subclass/thin constructor if that is cleaner.

Update imports so existing public API still exports `Token`.

### Phase 2: ParserState streams

Change `ParserState` to store:

```python
streams: dict[str, list[Slot]]
```

Add compatibility property:

```python
@property
def tokens(self) -> list[Slot]:
    return self.streams.setdefault("token", [])
```

Update `initialize_state(text)` to populate the `"token"` stream exactly as before.

Add new initializer:

```python
initialize_char_state(text)
```

which populates the `"char"` stream.

### Phase 3: Slot IDs in label deltas

Change `LabelDelta` to use `slot_id`.

```python
@dataclass(frozen=True)
class LabelDelta:
    slot_id: str
    label: str
    weight: float
    source: str | None = None
```

Add compatibility for integer `token_index` if needed.

Recommended compatibility constructor:

```python
LabelDelta.for_token_index(index, label, weight, source=None)
```

or temporarily allow:

```python
LabelDelta(token_index=..., ...)
```

and resolve during `apply_deltas`.

### Phase 4: Add AddSlot

Add:

```python
@dataclass(frozen=True)
class AddSlot:
    stream: str
    slot: Slot
    source: str | None = None
```

Add:

```python
RepresentationDelta = LabelDelta | AddSlot
```

Update `apply_deltas`.

### Phase 5: Scanner stream parameter

Update `FSMScanner.scan`:

```python
scan(fsm, state, stream="token", slot_filter=None)
```

Update scan context and anchors to operate on slot IDs.

Keep offset-based authoring behavior by resolving offsets against the scanned stream.

### Phase 6: Block stream fields

Add default fields:

```python
consumes: str = "token"
emits_to: str = "token"
```

to block classes where relevant.

Existing blocks should keep working.

### Phase 7: Per-stream normalization

Update parser config to support stream-specific normalization.

Default behavior should match current config for the `"token"` stream.

### Phase 8: First reducer demo

Implement:

```python
initialize_char_state(text)
CharClassBlock
SimpleCharToTokenReducer
```

Target a small demo:

```text
foo + 123
```

Expected streams:

```text
char: f o o   +   1 2 3
token: IDENT(foo), PLUS(+), NUMBER(123)
```

Then run existing syntax/POS-style FSMs over the token stream.

## Testing Strategy

### Existing tests

All existing tests should pass after compatibility shims.

Important compatibility points:

- `state.tokens` still works.
- existing token initialization still produces a `"token"` stream.
- existing FSMs scan `"token"` by default.
- existing `LabelDelta`-style outputs still apply to token slots.

### New unit tests

#### Slot creation

- create slot with ID, kind, stream, labels, source span, and parents
- verify `state.get_slot(id)` works across streams
- verify lazy stream creation

#### AddLabel

- add label to slot by ID
- add label to missing slot is ignored or raises depending on chosen policy
- compatibility token-index delta resolves correctly

#### AddSlot

- add slot to new stream
- add slot to existing stream
- stream ordering is stable

#### Scanner stream selection

- scanner over `"token"` sees token slots
- scanner over `"char"` sees char slots
- scanner does not see other streams

#### Anchors

- `FiringOffset` emits to correct slot ID
- `CaptureAnchor` emits to captured slot ID
- offset from captured slot works within the scanned stream

#### Normalization

- token stream uses default normalization
- char stream can use different decay
- `FORGOTTEN` remains per-slot

#### Provenance

- reducer-created token slots point to char parents
- alternative token slots use `alternate_to`
- semantic inserted slots can have `source_span=None`

### Integration tests

#### Char-to-token

Input:

```text
foo + 123
```

Expected token stream contains:

```text
TOKEN:IDENT
TOKEN:PLUS
TOKEN:NUMBER
```

with correct source spans and provenance.

#### Ambiguous segmentation

Input:

```text
>>
```

Expected token candidates:

```text
TOKEN:SHIFT_RIGHT
TOKEN:GT
TOKEN:GT
```

with overlap preserved.

#### Phrase reducer

Input token stream:

```text
the cat
```

Expected phrase stream contains:

```text
PHRASE:NP
```

with parents pointing to token slots.

#### Semantic inserter

Input token stream:

```text
forgot keys
```

Expected semantic stream contains an implied-state slot with evidence provenance.

## Performance Considerations

### Slot lookup

Once deltas reference slot IDs, state needs efficient lookup.

Maintain an index:

```python
slots_by_id: dict[str, Slot]
```

Update it when `AddSlot` is applied.

### Sorting streams

Sorting after every slot insertion may be expensive. Prefer one of:

- append and sort once after each layer
- maintain insertion order if reducers emit in order
- mark stream dirty and sort lazily before scanner access

### Overlapping slots

Overlapping slots can cause scan blowup because the scanner sees more candidates.

Mitigations:

- optional `slot_filter`
- max candidates per source span
- threshold labels before scanning
- projection step before expensive grammars
- per-stream `max_slots` warning or guardrail

### Provenance size

Slots derived from long spans can have many parents.

Mitigations:

- allow parent compression
- store only boundary parents plus source span for long contiguous spans
- use `derived_from_span` relation later if necessary

Do not optimize prematurely. Use explicit parent edges first.

## Backward Compatibility

The migration should be intentionally small.

Existing API compatibility targets:

```python
state.tokens
Token
LabelDelta
FSMScanner.scan(fsm, state)
FSMBlock(name, fsms)
initialize_state(text)
```

All should continue working.

Breaking change accepted:

```text
stable slot IDs replace integer positions as the internal reference model
```

This is worth doing because position-based references fail once slots can be added.

Compatibility shims can hide most of the breakage from existing examples and tests.

## Risks

### Risk: slots become a graph engine

If too much behavior moves into provenance traversal, the scanner may become a graph parser by accident.

Mitigation: scanner scans flat streams only. Provenance is for projection, explanation, and reducer logic.

### Risk: too many streams

If every feature creates a new stream, state becomes hard to inspect.

Mitigation: start with four conventional streams:

```text
char
token
phrase
semantic
```

Add more only when a concrete use case requires them.

### Risk: overlapping slots create explosion

Ambiguous tokenization and phrase candidates can multiply.

Mitigation: support filters and projection checkpoints, but keep the default additive.

### Risk: AddSlot is too weak

Some operations may seem to want destructive merge/split/suppress.

Mitigation: first express them as additive alternatives. If that proves impossible, revisit the slot model rather than adding many mutation deltas.

### Risk: existing code assumes integer indices

FSM emissions, captures, projection helpers, and debug rendering currently assume token positions.

Mitigation: provide compatibility helpers and migrate internals gradually.

## Open Questions

### Should slot IDs be strings or integers?

Strings are readable and stream-aware. Integers are faster and smaller. Start with strings for debuggability.

### Should `order` be float or structured?

A float is simple but can get awkward for inserted slots. A structured order key may be better later:

```text
(source_start, source_end, insertion_rank, id)
```

Start simple.

### Should `source_span.end` be inclusive or exclusive?

Use exclusive end, matching Python slicing.

### Should `AddSlot` immediately normalize the new slot?

Probably not. Add the slot, then normalize all streams at the normal layer boundary.

### Should a reducer be allowed to read multiple streams?

Eventually yes. For the first version, reducers should consume one stream and emit to one stream.

### Should grammar YAML support stream fields?

Yes, but not in the first migration step. Default YAML behavior should remain token-stream scanning.

Later:

```yaml
type: fsm
name: phrase_rules
consumes: token
emits_to: token
```

and:

```yaml
type: reducer
name: char_to_token
consumes: char
emits_to: token
```

### Should projection be part of the pipeline?

Projection should remain separate from parsing. A pipeline may call projection between phases for efficiency, but that should be explicit.

## Minimal End-to-End Demo

The first demo should prove the feature with the smallest possible system.

Input:

```text
foo + 123
```

Pipeline:

```text
initialize_char_state
Layer 1: char classification
Layer 2: char-to-token reducer
Layer 3: token syntax labels
```

Expected final state:

```text
char stream:
  char slots with LETTER, DIGIT, WHITESPACE, OPERATOR labels

token stream:
  token:0 TEXT:foo TOKEN:IDENT
  token:1 TEXT:+ TOKEN:PLUS
  token:2 TEXT:123 TOKEN:NUMBER
```

Every token slot should have `derived_from` provenance pointing back to character slots.

The existing debug renderer should be extended to render a selected stream:

```python
render_state(state, stream="token")
render_state(state, stream="char")
```

## Future Extensions

Once the basic feature works, useful extensions include:

### Phrase reducers

```text
token -> phrase
```

Create phrase slots such as:

```text
PHRASE:NP
PHRASE:VP
PHRASE:PP
```

### Semantic expanders

```text
token/phrase -> semantic
```

Create slots for implied states, events, roles, and discourse relations.

### Markdown blocks

```text
line -> block
block -> section
section -> semantic document roles
```

This makes Markdown authoring a natural application of shape-changing transducers.

### Candidate projection

Add utility functions for selecting non-overlapping candidates by score.

```python
project_best_sequence(state, stream="token")
```

### YAML support

Add stream declarations and reducer specs to grammar YAML.

## Design Principle

Shape-changing should not mean destructive mutation.

A transducer may add a new slot that summarizes, reinterprets, splits, or expands existing evidence. But the old evidence remains available through streams and provenance.

The central invariant becomes:

```text
Parser blocks do not erase.
They add labels or add slots.
Projection decides what to read.
```

## Summary

Shape-changing transducers generalize the parser from a fixed token-label sequence to a multi-stream, provenance-preserving representation.

The design requires only a small conceptual expansion:

```text
Token -> Slot
token_index -> slot_id
tokens -> streams
LabelDelta -> AddLabel
new: AddSlot
```

This supports tokenization, alternative segmentation, phrase creation, semantic insertion, and document-level analysis without abandoning the architecture's original strengths:

- inspectability
- deferred commitment
- weighted evidence
- simple block interface
- centralized delta application
- projection as the place where decisions happen

The first implementation should be deliberately modest: introduce slots and streams, preserve existing behavior through compatibility shims, and demonstrate the new capability with a character-to-token reducer.

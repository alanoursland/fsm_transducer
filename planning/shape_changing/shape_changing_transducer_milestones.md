# Milestones: Shape-Changing Transducer Implementation

## Purpose

This milestone plan breaks the shape-changing transducer technical design into buildable phases.

The goal is to evolve the current token-preserving parser into a multi-stream, slot-based parser that can add new representational slots while preserving compatibility with the existing token-stream behavior.

The implementation should proceed conservatively. The first version should prove the core idea with a character-to-token reducer before adding more ambitious phrase, semantic, Markdown, or programming-language reducers.

## Guiding Principle

Do not introduce destructive graph mutation.

The only state-changing operations should be:

```text
AddLabel(slot_id, label, weight)
AddSlot(stream, slot)
```

Merging, splitting, suppression, tokenization, phrase creation, semantic insertion, and alternative segmentations should all be expressed as adding new slots with provenance.

Projection is responsible for choosing what to read.

## Milestone 0: Baseline and Compatibility Snapshot

### Goal

Establish a clean baseline before changing the data model.

### Work

- Run the existing test suite.
- Record the number of passing tests.
- Capture current CLI output for representative examples.
- Capture current trace output for the default grammar.
- Identify tests or examples that directly assume `Token.index` or `LabelDelta.token_index`.

Representative examples:

```text
I can book flights.
The cat slept.
The book fell.
```

### Deliverables

- Baseline test report.
- Baseline trace snapshots.
- Short list of compatibility assumptions in the current code.

### Acceptance Criteria

- Existing parser behavior is documented before migration.
- Known index-based assumptions are identified.
- There is a clear rollback point.

### Risks

The current code may have hidden assumptions about integer token indices. Finding them before the migration reduces debugging noise later.

## Milestone 1: Introduce Slot Data Model

### Goal

Add the new representational primitives without changing parser behavior.

### Work

Add the following types:

```text
SlotId
SourceSpan
ProvenanceEdge
Slot
```

Recommended files:

```text
tokens.py
```

or a new file:

```text
slots.py
```

If a new `slots.py` is created, `tokens.py` should re-export compatibility names.

Implement:

```python
@dataclass(frozen=True)
class SourceSpan:
    start: int
    end: int

@dataclass(frozen=True)
class ProvenanceEdge:
    relation: str
    slot_id: str

@dataclass
class Slot:
    id: str
    kind: str
    stream: str
    order: float
    labels: LabelBag
    text: str | None
    source_span: SourceSpan | None
    parents: tuple[ProvenanceEdge, ...]
```

Preserve compatibility with the existing `Token` API.

Possible compatibility approaches:

```text
Token = Slot
```

or:

```text
Token as a thin subclass/constructor around Slot
```

If current tests instantiate `Token(index=..., text=...)`, preserve that constructor behavior.

### Deliverables

- Slot model implemented.
- `Token` compatibility preserved.
- Public exports updated.
- Unit tests for `Slot`, `SourceSpan`, and `ProvenanceEdge`.

### Acceptance Criteria

- Existing code can still import `Token`.
- Existing token objects behave like slots.
- Existing tests that only inspect token text and labels still pass.
- New slot tests pass.

### Risks

A direct alias may break code that expects `Token(index=..., text=...)`. Use a compatibility constructor if necessary.

## Milestone 2: Convert ParserState to Multi-Stream State

### Goal

Replace `ParserState.tokens` storage with stream storage while preserving the `state.tokens` property.

### Work

Change `ParserState` from:

```python
ParserState(tokens=[...])
```

to:

```python
ParserState(streams={"token": [...]})
```

Add compatibility:

```python
@property
def tokens(self) -> list[Slot]:
    return self.stream("token")
```

Add methods:

```python
stream(name)
get_slot(slot_id)
add_slot(stream, slot)
sort_stream(stream)
next_id(stream)
reindex()
```

Maintain:

```text
_slots_by_id
_id_counters
```

Support compatibility construction if needed:

```python
ParserState(tokens=[...])
ParserState(streams={...})
```

Update `initialize_state(text)` so it creates the `"token"` stream and produces the same initial labels as before.

### Deliverables

- Multi-stream `ParserState`.
- Token-stream compatibility.
- Slot ID lookup.
- ID allocation.
- Stream sorting.
- Updated `initialize_state`.

### Acceptance Criteria

- `state.tokens` still works.
- `state.stream("token")` returns the same slots as `state.tokens`.
- `state.get_slot(slot.id)` works for all initialized token slots.
- Existing token-based parser examples still initialize correctly.
- Existing tests mostly still pass, except tests blocked by delta/scanner migration.

### Risks

Tests may instantiate `ParserState` directly. Supporting both constructor forms avoids unnecessary breakage.

## Milestone 3: Add Representation Deltas

### Goal

Generalize deltas from token-indexed label updates to slot-ID label updates plus slot creation.

### Work

Introduce:

```python
@dataclass(frozen=True)
class AddLabel:
    slot_id: str
    label: str
    weight: float
    source: str | None = None

@dataclass(frozen=True)
class AddSlot:
    stream: str
    slot: Slot
    source: str | None = None
```

Define:

```python
RepresentationDelta = AddLabel | AddSlot
```

Preserve compatibility with `LabelDelta`.

Recommended approach:

```text
Keep the public name LabelDelta.
Internally migrate toward AddLabel.
Temporarily support token_index-based construction if needed.
```

Update `apply_deltas` to:

- apply `AddLabel` by slot ID
- resolve compatibility token-index deltas against the `"token"` stream
- add `AddSlot` to the target stream
- reject duplicate slot IDs
- reject stream mismatches
- sort touched streams after adding slots

### Deliverables

- `AddLabel`.
- `AddSlot`.
- `RepresentationDelta`.
- Updated `apply_deltas`.
- Compatibility path for old `LabelDelta`.
- Unit tests for delta application.

### Acceptance Criteria

- Existing blocks that emit old-style label deltas still work.
- New `AddLabel` can target any slot by ID.
- `AddSlot` creates a new slot in a stream.
- Duplicate slot IDs raise an error.
- Stream mismatch raises an error.
- Missing slot labels are ignored or handled according to the chosen compatibility policy.

### Risks

This is the first point where old tests may fail because they compare delta objects directly. Compatibility shims should be generous in this phase.

## Milestone 4: Normalize Across Streams

### Goal

Extend normalization so every stream is normalized, with optional per-stream configs.

### Work

Update `ParserConfig` to support stream-specific normalization:

```python
stream_configs: dict[str, NormalizationConfig]
```

Keep existing config fields as defaults.

Add:

```python
normalization_for_stream(stream)
```

Update `normalize_state` to iterate over all streams:

```python
for stream_name, slots in state.streams.items():
    cfg = parser_config.normalization_for_stream(stream_name)
    normalize each slot
```

Keep `FORGOTTEN` per-slot.

Do not conserve mass across streams.

### Deliverables

- Per-stream normalization support.
- Compatibility with existing parser config.
- Tests for default and stream-specific normalization.

### Acceptance Criteria

- Existing parser normalization behavior is unchanged for the token stream by default.
- Character, token, phrase, and semantic streams can use different configs.
- `FORGOTTEN` remains local to each slot.
- Existing parser examples still run.

### Risks

Changing the config shape may break callers. Preserve old fields and build the default normalization from them.

## Milestone 5: Update Blocks for Streams

### Goal

Make parser blocks stream-aware while preserving token-stream defaults.

### Work

Update `ParserBlock` expectations:

```text
name
consumes
emits_to
apply(state)
```

Update concrete blocks:

```text
LexicalBlock
FSMBlock
CallableBlock
```

Defaults:

```python
consumes = "token"
emits_to = "token"
```

Update `LexicalBlock` so it loops over:

```python
state.stream(self.consumes)
```

and emits label deltas by slot ID.

Update `FSMBlock` so it passes:

```python
stream=self.consumes
```

to the scanner once scanner migration is complete.

For this milestone, if scanner migration has not landed yet, keep `FSMBlock` behavior compatible and prepare fields.

### Deliverables

- Stream-aware block classes.
- Token-stream defaults.
- Updated unit tests for lexical blocks.
- Compatibility with existing grammar construction.

### Acceptance Criteria

- Existing grammar code still works without specifying streams.
- A lexical block can consume a non-token stream if the slots have `text`.
- Blocks return representation deltas.
- Existing parser examples still run after scanner migration.

### Risks

Adding protocol fields can break structural typing in tests. Concrete classes should provide defaults, but the protocol should not be over-constrained too early.

## Milestone 6: Update the FSM Scanner to Scan Streams

### Goal

Make the scanner operate over an explicitly selected stream of slots instead of `state.tokens`.

### Work

Change scanner API:

```python
scan(fsm, state, stream="token", slot_filter=None)
```

Internally:

```python
slots = state.stream(stream)
```

Update scan context:

```python
stream
slots
pos as position in scanned stream
n as length of scanned stream
```

Update condition type annotations from `Token` to `Slot`.

Update captures:

- capture stable slot ID
- retain stream position for offset-based anchors
- keep compatibility with index capture if necessary

Update emission anchors so they resolve to slot IDs:

```text
FiringOffset
CaptureAnchor
ScanStart
ScanEnd
```

Update `_fire` so it emits:

```python
AddLabel(slot_id=target_slot_id, ...)
```

### Deliverables

- Scanner scans selected stream.
- Scanner returns slot-ID label deltas.
- Anchors resolve to slot IDs.
- Captures support slot identity.
- Existing FSMs still work on the token stream.

### Acceptance Criteria

- Existing default grammar works.
- Existing offset-based emissions still target the intended token-stream slots.
- Capture-anchored emissions still work.
- Scanner can scan a char stream in a new test.
- Empty stream scanning returns no deltas.
- Conditions match slots exactly as they matched tokens.

### Risks

This is the most delicate milestone.

The current scanner uses token indices in captures, anchors, and emissions. Preserve offset semantics by treating offsets as positions in the scanned stream while emitting stable slot IDs.

## Milestone 7: Update Debugging and Trace Rendering

### Goal

Make traces useful for multi-stream state and new delta types.

### Work

Update:

```text
render_state
render_deltas
render_trace
```

Add stream selection:

```python
render_state(state, stream="token", top_k=5)
render_trace(traces, streams=("token",))
```

Render `AddLabel` and `AddSlot`.

Suggested delta rendering:

```text
[lexicon] add_label slot=token:0 POS:NOUN += 0.550
[char_to_token] add_slot stream=token id=token:0 text='foo' labels=TOKEN:IDENT=1.00
```

Suggested state rendering:

```text
Layer 2 / stream token
id        order  text   span   top labels
token:0   0.0    foo    0..3   TOKEN:IDENT=1.00 TEXT:foo=1.00
```

### Deliverables

- Stream-aware debug rendering.
- Delta rendering for both delta types.
- Trace rendering for selected streams.

### Acceptance Criteria

- Old default `render_state(state)` shows token stream.
- Old default `render_trace(traces)` remains readable.
- Char/token demo can render both char and token streams.
- AddSlot deltas are visible in traces.

### Risks

Golden-output tests may fail because formatting changes. Prefer updating tests to assert key content rather than exact spacing.

## Milestone 8: Add Character Initialization and Character Labels

### Goal

Create the first non-token input stream.

### Work

Add:

```python
initialize_char_state(text)
```

It should create one slot per character:

```text
kind = "char"
stream = "char"
id = "char:n"
source_span = SourceSpan(n, n + 1)
text = character
labels include CHAR and CHAR:<literal>
```

Add `CharClassBlock` over the `"char"` stream.

Labels to emit:

```text
CHAR:LETTER
CHAR:DIGIT
CHAR:WHITESPACE
CHAR:PUNCT
CHAR:OPERATOR
CHAR:QUOTE
CHAR:OPEN_DELIM
CHAR:CLOSE_DELIM
```

Keep this block simple and deterministic.

### Deliverables

- Character initializer.
- Character classification block.
- Tests for char stream creation and char labels.
- Debug rendering for char stream.

### Acceptance Criteria

- `initialize_char_state("a+1")` creates three char slots.
- Source spans are correct.
- Character labels are added by `CharClassBlock`.
- No token stream is required at initialization.

### Risks

Literal character labels like `CHAR:
` can make debug output awkward. Use safe rendering in debug tools if necessary.

## Milestone 9: Implement First Shape-Changing Reducer

### Goal

Demonstrate `char -> token` reduction using `AddSlot`.

### Work

Implement a simple reducer:

```python
SimpleCharToTokenReducer
```

Consumes:

```text
char
```

Emits to:

```text
token
```

Recognize:

```text
identifier runs
number runs
single-character operators
punctuation/delimiters
optional whitespace
```

Minimum labels:

```text
TOKEN:IDENT
TOKEN:NUMBER
TOKEN:PLUS
TOKEN:MINUS
TOKEN:STAR
TOKEN:SLASH
TOKEN:LPAREN
TOKEN:RPAREN
TOKEN:UNKNOWN
TEXT:<surface>
LOWER:<surface>
```

Every emitted token slot should include:

```text
source_span
derived_from parent edges to char slots
text
kind="token"
stream="token"
order based on first char order
```

### Deliverables

- `SimpleCharToTokenReducer`.
- Unit tests for identifier, number, operator, punctuation, and whitespace behavior.
- Integration test over `foo + 123`.
- Trace showing `AddSlot` deltas.

### Acceptance Criteria

Input:

```text
foo + 123
```

produces token slots:

```text
foo  TOKEN:IDENT
+    TOKEN:PLUS
123  TOKEN:NUMBER
```

Each token has correct source span and provenance.

The char stream remains intact.

### Risks

This reducer should not become a full lexer. Keep it intentionally small.

## Milestone 10: Parser API for Prebuilt States

### Goal

Allow parsing from a pre-initialized multi-stream state.

### Work

Add:

```python
Parser.parse_state(state)
Parser.parse_state_with_trace(state)
```

Refactor existing methods:

```python
parse(text) -> parse_state(initialize_state(text))
parse_with_trace(text) -> parse_state_with_trace(initialize_state(text))
```

This allows char-based pipelines:

```python
state = initialize_char_state("foo + 123")
parser.parse_state(state)
```

### Deliverables

- `parse_state`.
- `parse_state_with_trace`.
- Existing `parse` behavior preserved.
- Tests for parse from char state.

### Acceptance Criteria

- Existing callers using `parse(text)` still work.
- New callers can pass a custom initialized state.
- Trace works for custom initialized state.

### Risks

Trace initialization currently assumes token initialization. Make the initial trace snapshot reflect whatever streams exist in the passed state.

## Milestone 11: Ambiguous Tokenization Demo

### Goal

Prove overlapping token candidates can represent a tokenization ambiguity without a separate lattice.

### Work

Add a small reducer or demo block for `>>`.

Input:

```text
>>
```

Emit overlapping token candidates:

```text
TOKEN:SHIFT_RIGHT over chars 0..2
TOKEN:GT over chars 0..1
TOKEN:GT over chars 1..2
```

Use provenance:

```text
derived_from char parents
alternate_to relation between the two-token interpretation and the shift token
```

Optional: add a context block that boosts `TOKEN:GT` in a template-like context.

### Deliverables

- Ambiguous tokenization test.
- Debug trace showing overlapping candidates.
- Projection placeholder or simple inspection utility.

### Acceptance Criteria

- All candidate slots coexist in the token stream.
- No destructive split or merge is used.
- Scanner can scan the token stream without crashing on overlapping slots.
- Projection or debug rendering can show the alternatives.

### Risks

Flat scanning of overlapping slots may not fully capture lattice semantics. That is acceptable for this milestone. The goal is representation, not full disambiguating parse.

## Milestone 12: Projection Utilities for Slot Streams

### Goal

Add minimal projection tools for consumers that need a clean view.

### Work

Update existing projection utilities to accept a stream:

```python
project_spans(state, stream="token", ...)
project_dependency_edges(state, stream="token", ...)
```

Add a simple non-overlap projection:

```python
project_non_overlapping_slots(state, stream="token")
```

Initial greedy strategy is acceptable:

1. sort by source span start
2. prefer higher score
3. avoid overlapping source spans
4. return selected slots in order

Scoring may use:

```text
max label weight
specific label prefix
total non-FORGOTTEN mass
```

### Deliverables

- Stream-aware projection helpers.
- Greedy token candidate projection.
- Tests for non-overlapping projection.

### Acceptance Criteria

- Existing projection tests pass with default stream.
- Ambiguous `>>` candidates can be projected into one clean view.
- Projection does not mutate parser state.

### Risks

Greedy projection may be wrong for complex lattices. That is acceptable. A dynamic programming projection can come later.

## Milestone 13: Documentation and Examples

### Goal

Make the new model understandable to future users and future-you.

### Work

Update docs and docstrings for:

```text
Slot
ParserState streams
AddLabel
AddSlot
scanner stream selection
char initializer
char-to-token reducer
projection
```

Add examples:

```text
token-based parsing still works
char-to-token reduction
ambiguous tokenization
multi-stream trace rendering
```

Update any markdown design documents if implementation details diverge from the plan.

### Deliverables

- Updated API documentation.
- Updated design notes.
- Example scripts or CLI examples.
- README section for shape-changing transducers.

### Acceptance Criteria

A new reader can understand:

- what a slot is
- what a stream is
- how `AddSlot` works
- why mutation is avoided
- how to run the char-to-token demo

### Risks

Documentation may drift if written before code stabilizes. Do this after the implementation passes tests.

## Milestone 14: Cleanup and Compatibility Retirement Plan

### Goal

Identify which compatibility shims can remain and which should be deprecated later.

### Work

Review compatibility features:

```text
Token.index
LabelDelta.token_index
ParserState(tokens=...)
index captures
old debug formatting
```

Decide:

```text
keep permanently
deprecate
remove later
```

Add deprecation warnings only if useful.

Update internal code to prefer:

```text
Slot
slot.id
AddLabel
ParserState(streams=...)
slot_id captures
```

### Deliverables

- Compatibility review.
- Internal code migrated to slot-first style.
- Deprecation notes if needed.

### Acceptance Criteria

- Public examples use the new slot model where appropriate.
- Existing old examples still work or have clear migration guidance.
- Internal code no longer depends on token index except compatibility surfaces.

### Risks

Removing compatibility too early will make the system harder to use. Keep shims until the new model has enough examples.

## Suggested Build Order

The safest order is:

```text
0. Baseline
1. Slot model
2. ParserState streams
3. Representation deltas
4. Per-stream normalization
5. Stream-aware blocks
6. Stream-aware scanner
7. Debug rendering
8. Character initialization
9. Char-to-token reducer
10. parse_state API
11. Ambiguous tokenization demo
12. Projection utilities
13. Documentation
14. Cleanup
```

The first major checkpoint is after Milestone 6, when the existing parser should still work on the token stream.

The second major checkpoint is after Milestone 9, when the parser can start from characters and create token slots.

The third major checkpoint is after Milestone 11, when overlapping slots demonstrate ambiguous tokenization.

## MVP Definition

The minimum viable version of shape-changing transducers includes:

```text
Slot
ParserState.streams
AddLabel
AddSlot
scanner stream selection
per-stream normalization fallback
initialize_char_state
CharClassBlock
SimpleCharToTokenReducer
stream-aware debug rendering
```

The MVP demo:

```text
input: "foo + 123"

char stream:
  f o o   +   1 2 3

token stream:
  foo  TOKEN:IDENT
  +    TOKEN:PLUS
  123  TOKEN:NUMBER
```

Each token slot must have:

```text
stable slot ID
source_span
derived_from provenance
weighted labels
```

The existing token-based parser must still work.

## Stretch Goals

These are useful but should not block the MVP.

### Phrase reducer

Create phrase slots from token spans.

Example:

```text
the cat -> PHRASE:NP
```

### Semantic inserter

Create implied semantic slots.

Example:

```text
forgot keys -> IMPLIED_STATE:NOT_HAVE
```

### Markdown stream pipeline

Create line, block, section, and semantic streams for Markdown documents.

### Dynamic programming projection

Replace greedy non-overlap projection with a best-path selector.

### YAML stream support

Allow grammar YAML to specify:

```yaml
consumes: token
emits_to: phrase
```

### Learned reducers

Learn `AddSlot` rules from examples.

## Risk Register

### Risk: scanner migration breaks existing grammar behavior

Impact: high.

Mitigation: keep token stream default, preserve offset semantics, add regression tests for default grammar.

### Risk: slot IDs make traces noisier

Impact: medium.

Mitigation: improve debug rendering with text, order, span, and top labels.

### Risk: compatibility shims become permanent clutter

Impact: medium.

Mitigation: document shims and plan deprecation after the shape-changing API stabilizes.

### Risk: overlapping candidates cause scan blowup

Impact: medium to high later.

Mitigation: add optional scanner filters and projection checkpoints only after a concrete performance issue appears.

### Risk: reducers become ad hoc lexers

Impact: medium.

Mitigation: keep first reducer intentionally small; treat real language tokenization as separate future work.

### Risk: provenance becomes too large

Impact: medium.

Mitigation: store full provenance first; optimize later with span-level provenance if needed.

## Completion Checklist

The implementation is complete when:

- Existing token-based parsing still works.
- Existing tests pass or have intentional, documented updates.
- State supports multiple streams.
- Slots have stable IDs.
- Deltas can target slots by ID.
- Deltas can add slots.
- Scanner can scan a selected stream.
- Normalization applies per stream.
- Debug rendering can show selected streams.
- Character initialization works.
- Character-to-token reducer works.
- Token slots preserve provenance.
- Ambiguous token candidates can coexist.
- Projection can select a clean token view without mutating state.

## Final Note

The implementation should remain small and disciplined.

The feature is not “make the parser a graph rewriting engine.” The feature is:

```text
Let transducers create new labeled slots with provenance.
```

That single move is enough to represent tokenization, phrase formation, semantic insertion, and ambiguous segmentation while preserving the parser's core philosophy:

```text
Accrete evidence.
Do not erase.
Project when a decision is needed.
```

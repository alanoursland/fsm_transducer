# Technical Design: Shape-Changing Transducers

## 1. Overview

This document specifies the implementation design for shape-changing transducers in the Python FSM parser.

The existing system is a shape-preserving, label-emitting transducer pipeline. It starts with a token sequence and each parser layer appends weighted labels to the same tokens. Shape-changing transducers generalize this model so parser blocks can add new representational units, called slots, into named streams.

The core implementation shift is:

```text
Token -> Slot
ParserState.tokens -> ParserState.streams["token"]
LabelDelta(token_index, ...) -> AddLabel(slot_id, ...)
new delta: AddSlot(stream, slot)
```

Shape-changing is non-destructive. Blocks do not delete, merge, split, or suppress existing slots. They add labels or add new slots with provenance. Projection decides which slots to read.

This document is intended to guide implementation in the current codebase.

## 2. Current Architecture

The current implementation has these key types:

```text
Token
ParserState
LabelBag
LabelDelta
ParserBlock
LexicalBlock
FSMBlock
FSMScanner
NormalizationConfig
Parser
```

The current data flow is:

```text
initialize_state(text)
  -> ParserState(tokens=[Token, ...])

for each layer:
  for each block:
    deltas += block.apply(state)

  apply_deltas(state, deltas)
  normalize_state(state)
```

Current deltas target tokens by integer index:

```text
LabelDelta(token_index, label, weight, source)
```

Current scanner logic assumes it scans:

```text
state.tokens
```

and that relative offsets resolve to integer token positions.

Shape-changing transducers require stable identity and multiple slot streams. Integer positions are not stable once new slots can be added.

## 3. Design Constraints

The implementation must preserve the original architecture's most important properties:

```text
blocks do not mutate state directly
deltas are the only way to change state
labels remain weighted and additive
normalization happens centrally
projection makes destructive decisions
debug traces remain inspectable
existing token-stream behavior keeps working
```

The implementation should minimize the first migration. The goal is not a full graph parser. The scanner should still scan flat ordered streams.

## 4. New Core Concepts

### 4.1 Slot

A slot is a generalization of a token.

A slot is an ordered representational unit with a label bag and optional provenance.

A slot may represent:

```text
character
token
token candidate
phrase
semantic frame
implied concept
gap
document line
document block
section
```

### 4.2 Stream

A stream is an ordered sequence of slots.

Examples:

```text
char
token
phrase
semantic
line
block
section
```

The default stream is:

```text
token
```

Existing code should continue to operate on the token stream unless otherwise specified.

### 4.3 Provenance

Every shape-created slot can point to the slots that produced it.

Provenance edges carry relations:

```text
derived_from
alternate_to
evidence_for
summarizes
implies
anchors
```

A token created from characters uses `derived_from`.

An alternative tokenization uses `alternate_to`.

A semantic implied slot may use `evidence_for`.

### 4.4 Representation Delta

A parser block can emit:

```text
AddLabel
AddSlot
```

`AddLabel` is the renamed conceptual form of the existing `LabelDelta`.

`AddSlot` is the new shape-changing operation.

## 5. Type Definitions

### 5.1 SlotId

Use a string slot ID in the first implementation.

```python
SlotId = str
```

Example IDs:

```text
char:0
token:0
token:1
phrase:0
semantic:0
```

String IDs are debuggable and stream-aware. They can be replaced later by compact integer IDs if profiling demands it.

### 5.2 SourceSpan

Source spans use Python slicing semantics: start inclusive, end exclusive.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class SourceSpan:
    start: int
    end: int
```

Examples:

```python
SourceSpan(0, 4)   # chars [0:4]
SourceSpan(5, 6)   # one-character span
```

`source_span` may be `None` for implied semantic slots.

### 5.3 ProvenanceEdge

```python
@dataclass(frozen=True)
class ProvenanceEdge:
    relation: str
    slot_id: SlotId
```

Example:

```python
ProvenanceEdge("derived_from", "char:3")
ProvenanceEdge("alternate_to", "token:7")
ProvenanceEdge("evidence_for", "phrase:2")
```

No enum is required initially. Relations should be documented constants later if they stabilize.

### 5.4 Slot

```python
from dataclasses import dataclass, field

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

Field semantics:

```text
id
  Stable slot reference within one parser run.

kind
  Representational role, such as "char", "token", "phrase", "semantic".

stream
  Name of the stream that owns this slot.

order
  Sort key within the stream.

labels
  Weighted label bag.

text
  Optional surface string or rendered text.

source_span
  Optional character span in the original input.

parents
  Provenance edges pointing to earlier slots.
```

### 5.5 Token Compatibility

The existing public name `Token` should remain available.

Implementation options:

```python
Token = Slot
```

or:

```python
def Token(index: int, text: str, labels: LabelBag | None = None) -> Slot:
    ...
```

The preferred approach is to keep a compatibility constructor or factory if existing tests instantiate `Token(index=..., text=...)`.

A compatibility class can be used temporarily:

```python
@dataclass
class Token(Slot):
    def __init__(self, index: int, text: str, labels: LabelBag | None = None):
        super().__init__(
            id=f"token:{index}",
            kind="token",
            stream="token",
            order=float(index),
            text=text,
            labels=labels or LabelBag(),
            source_span=None,
            parents=(),
        )

    @property
    def index(self) -> int:
        return int(self.id.split(":", 1)[1])
```

Long term, prefer one `Slot` type and migrate away from `Token.index`.

## 6. ParserState

### 6.1 New State Shape

```python
@dataclass
class ParserState:
    streams: dict[str, list[Slot]]
    layer: int = 0
    _slots_by_id: dict[SlotId, Slot] = field(default_factory=dict)
    _id_counters: dict[str, int] = field(default_factory=dict)
```

### 6.2 Construction

`ParserState` should build its ID index in `__post_init__`.

```python
def __post_init__(self) -> None:
    self.reindex()
```

### 6.3 Stream Access

```python
def stream(self, name: str) -> list[Slot]:
    return self.streams.setdefault(name, [])
```

### 6.4 Token Compatibility

```python
@property
def tokens(self) -> list[Slot]:
    return self.stream("token")
```

This preserves the current access pattern:

```python
state.tokens
```

### 6.5 Slot Lookup

```python
def get_slot(self, slot_id: SlotId) -> Slot | None:
    return self._slots_by_id.get(slot_id)
```

### 6.6 ID Allocation

```python
def next_id(self, stream: str) -> SlotId:
    n = self._id_counters.get(stream, 0)
    self._id_counters[stream] = n + 1
    return f"{stream}:{n}"
```

When initializing a state from existing slots, `reindex()` must also advance counters past existing IDs if the IDs use the `stream:n` convention.

### 6.7 Adding Slots

```python
def add_slot(self, stream: str, slot: Slot) -> None:
    if slot.id in self._slots_by_id:
        raise ValueError(f"duplicate slot id: {slot.id}")
    self.stream(stream).append(slot)
    self._slots_by_id[slot.id] = slot
```

If `slot.stream != stream`, either:

1. reject it, or
2. normalize `slot.stream = stream`.

Prefer rejecting it. Silent correction hides bugs.

### 6.8 Sorting Streams

Add:

```python
def sort_stream(self, stream: str) -> None:
    self.stream(stream).sort(key=slot_sort_key)
```

Sort key:

```python
def slot_sort_key(slot: Slot) -> tuple:
    span_start = slot.source_span.start if slot.source_span else -1
    span_end = slot.source_span.end if slot.source_span else -1
    return (slot.order, span_start, span_end, slot.id)
```

Sorting can be done after all deltas in a layer are applied.

## 7. Initialization

### 7.1 Token Initialization

`initialize_state(text)` should preserve existing behavior by creating the token stream.

Current behavior:

```text
split text into word/punctuation tokens
add TEXT, LOWER, SHAPE, TOKEN, PUNCT labels
```

New behavior:

```python
def initialize_state(text: str) -> ParserState:
    slots = []
    for i, raw in enumerate(tokenize(text)):
        slot = Slot(
            id=f"token:{i}",
            kind="token",
            stream="token",
            order=float(i),
            text=raw,
            source_span=None,
        )
        slot.labels.add(f"TEXT:{raw}", 1.0)
        slot.labels.add(f"LOWER:{raw.lower()}", 1.0)
        slot.labels.add(f"SHAPE:{_shape(raw)}", 1.0)
        slot.labels.add("TOKEN", 1.0)
        if not raw.isalnum():
            slot.labels.add("PUNCT", 1.0)
        slots.append(slot)
    return ParserState(streams={"token": slots}, layer=0)
```

### 7.2 Character Initialization

Add:

```python
def initialize_char_state(text: str) -> ParserState:
    ...
```

This creates one char slot per character.

```python
slot = Slot(
    id=f"char:{i}",
    kind="char",
    stream="char",
    order=float(i),
    text=ch,
    source_span=SourceSpan(i, i + 1),
)
slot.labels.add(f"CHAR:{ch}", 1.0)
slot.labels.add("CHAR", 1.0)
```

Additional character class labels may be added by a later block rather than initializer. Keep initializer minimal.

## 8. Deltas

### 8.1 AddLabel

Replace `LabelDelta.token_index` with `slot_id`.

```python
@dataclass(frozen=True)
class AddLabel:
    slot_id: SlotId
    label: str
    weight: float
    source: str | None = None
```

### 8.2 Compatibility Name

Keep:

```python
LabelDelta = AddLabel
```

or keep the class name `LabelDelta` but change its primary field to `slot_id`.

A compatibility layer can support integer token indices:

```python
@dataclass(frozen=True)
class LabelDelta:
    slot_id: SlotId | None = None
    label: str = ""
    weight: float = 0.0
    source: str | None = None
    token_index: int | None = None
```

This is uglier but reduces breakage.

Preferred staged approach:

1. Introduce `AddLabel`.
2. Keep `LabelDelta` as an alias or helper.
3. Update internal code to use `AddLabel`.
4. Remove token-index compatibility later.

### 8.3 AddSlot

```python
@dataclass(frozen=True)
class AddSlot:
    stream: str
    slot: Slot
    source: str | None = None
```

### 8.4 Delta Union

```python
RepresentationDelta = AddLabel | AddSlot
```

If supporting older Python versions, use:

```python
RepresentationDelta = Union[AddLabel, AddSlot]
```

## 9. Applying Deltas

### 9.1 New apply_deltas

```python
def apply_deltas(state: ParserState, deltas: list[RepresentationDelta]) -> None:
    touched_streams: set[str] = set()

    for d in deltas:
        if isinstance(d, AddLabel):
            slot = state.get_slot(d.slot_id)
            if slot is not None:
                slot.labels.add(d.label, d.weight)
            continue

        if isinstance(d, AddSlot):
            if d.slot.stream != d.stream:
                raise ValueError(
                    f"AddSlot stream mismatch: delta={d.stream}, slot={d.slot.stream}"
                )
            state.add_slot(d.stream, d.slot)
            touched_streams.add(d.stream)
            continue

        raise TypeError(f"unknown delta type: {type(d).__name__}")

    for stream in touched_streams:
        state.sort_stream(stream)
```

### 9.2 Missing Slot Policy

For `AddLabel` targeting a missing slot, choose one policy:

```text
ignore
raise
warn
```

The existing behavior ignores out-of-range token indices. For compatibility, start by ignoring missing slots. Add optional strict mode later.

## 10. Normalization

### 10.1 Per-Slot Normalization

Normalization remains per-slot.

Existing `normalize(bag, config)` can remain unchanged.

### 10.2 Per-Stream Config

Add:

```python
@dataclass
class ParserConfig:
    decay: float = 1.0
    min_weight: float = 0.001
    max_labels_per_slot: int = 64
    total_mass: float | None = None
    forgotten_label: str = FORGOTTEN
    stream_configs: dict[str, NormalizationConfig] = field(default_factory=dict)
```

Compatibility: existing fields build the default config.

```python
def normalization_for_stream(self, stream: str) -> NormalizationConfig:
    return self.stream_configs.get(stream, self.to_normalization())
```

### 10.3 normalize_state

```python
def normalize_state(state: ParserState, config: ParserConfig) -> None:
    for stream_name, slots in state.streams.items():
        norm_cfg = config.normalization_for_stream(stream_name)
        for slot in slots:
            slot.labels = normalize(slot.labels, norm_cfg)
```

No cross-stream conservation is attempted.

## 11. Parser Pipeline

### 11.1 ParserBlock Protocol

Current:

```python
class ParserBlock(Protocol):
    name: str
    def apply(self, state: ParserState) -> list[LabelDelta]: ...
```

Proposed:

```python
class ParserBlock(Protocol):
    name: str
    consumes: str
    emits_to: str

    def apply(self, state: ParserState) -> list[RepresentationDelta]: ...
```

Because protocols do not require default values, concrete block classes should provide defaults.

### 11.2 Parser.parse

Parser logic remains nearly identical:

```python
for i, blocks in enumerate(self.layers):
    deltas = []
    for block in blocks:
        deltas.extend(block.apply(state))
    apply_deltas(state, deltas)
    normalize_state(state, self.config)
    state.layer = i + 1
```

### 11.3 LayerTrace

Current traces store:

```text
deltas: list[LabelDelta]
state: ParserState
```

Change to:

```text
deltas: list[RepresentationDelta]
state: ParserState
```

Debug rendering must know how to render both `AddLabel` and `AddSlot`.

## 12. Scanner Design

### 12.1 Stream Parameter

Change scanner call from:

```python
scanner.scan(fsm, state)
```

to:

```python
scanner.scan(fsm, state, stream="token", slot_filter=None)
```

Signature:

```python
def scan(
    self,
    fsm: FSM,
    state: ParserState,
    *,
    stream: str = "token",
    slot_filter: Callable[[Slot], bool] | None = None,
) -> list[AddLabel]:
    ...
```

### 12.2 Slot List

```python
slots = state.stream(stream)
if slot_filter is not None:
    slots = [s for s in slots if slot_filter(s)]
```

The scanner should not mutate or sort streams. The pipeline is responsible for keeping streams in scan order.

### 12.3 ScanContext

Current `ScanContext` has:

```text
scan_start
n
pos
last_consumed
captures
```

Keep these, but clarify that:

```text
pos is an index into the scanned stream, not a source character index
```

Add:

```python
stream: str
slots: Sequence[Slot]
```

Optional:

```python
current_slot_id: SlotId | None
```

Proposed:

```python
@dataclass
class ScanContext:
    scan_start: int
    n: int
    stream: str
    slots: Sequence[Slot]
    pos: int | None = None
    last_consumed: int | None = None
    captures: dict[str, CaptureValue] = field(default_factory=dict)
```

### 12.4 Condition Protocol

Current:

```python
def matches(self, frame: Token, ctx: ScanContext | None = None) -> bool
```

Change type annotation only:

```python
def matches(self, frame: Slot, ctx: ScanContext | None = None) -> bool
```

The implementation works unchanged because slots have labels.

### 12.5 CaptureValue

Current capture kind `"index"` records token index.

New primary capture kind:

```text
slot_id
```

Proposed:

```python
@dataclass(frozen=True)
class CaptureValue:
    kind: str
    value: Any
```

Supported kinds:

```text
slot_id
top_label
source_span
```

Compatibility:

```text
index
```

can remain temporarily.

### 12.6 Capture

Current default kind:

```python
Capture(name, kind="index")
```

Change default to:

```python
Capture(name, kind="slot_id")
```

For compatibility, either:

1. leave default as `"index"` until migration is complete, or
2. accept `"index"` but return slot ID.

Preferred staged migration:

- Keep `kind="index"` in public constructor for now.
- Internally treat it as current stream position for old rules.
- Add `kind="slot_id"`.
- Update examples to use `slot_id`.

Long term, captures should use slot IDs.

### 12.7 Capturing From a Slot

```python
def _capture_from_slot(cap: Capture, slot: Slot, pos: int) -> CaptureValue:
    if cap.kind == "slot_id":
        return CaptureValue("slot_id", slot.id)
    if cap.kind == "index":
        return CaptureValue("index", pos)
    if cap.kind == "top_label":
        top = slot.labels.top_k(1)
        return CaptureValue("top_label", top[0][0] if top else "")
    if cap.kind == "source_span":
        return CaptureValue("source_span", slot.source_span)
    raise ValueError(...)
```

Important distinction:

```text
index = position in scanned stream
slot_id = stable identity
```

The old system used token index for both. The new system separates them.

### 12.8 Emission Anchors

Emission anchors must resolve to slot IDs.

Current protocol:

```python
def resolve(captures, firing_pos, scan_start, n) -> int | None
```

Proposed:

```python
def resolve(
    self,
    captures: dict[str, CaptureValue],
    firing_pos: int | None,
    scan_start: int,
    slots: Sequence[Slot],
) -> SlotId | None:
    ...
```

#### FiringOffset

```python
@dataclass(frozen=True)
class FiringOffset:
    offset: int = 0

    def resolve(...):
        if firing_pos is None:
            return None
        idx = firing_pos + self.offset
        if 0 <= idx < len(slots):
            return slots[idx].id
        return None
```

#### CaptureAnchor

Capture anchor has two cases:

1. captured stable slot ID
2. captured stream index

For offset support, the scanner needs the captured stream index. The clean design is to capture both.

Add to `CaptureValue` payload for slot captures:

```python
@dataclass(frozen=True)
class SlotCapture:
    slot_id: SlotId
    pos: int
```

Then:

```python
CaptureValue("slot", SlotCapture(slot.id, pos))
```

Simpler first implementation:

- `Capture("name", kind="index")` captures stream position.
- `Capture("name", kind="slot_id")` captures slot ID but cannot support offset.
- `CaptureAnchor` with offset requires an index capture.

Better implementation:

```python
@dataclass(frozen=True)
class CaptureValue:
    kind: str
    value: Any
    pos: int | None = None
```

For `slot_id` captures:

```python
CaptureValue("slot_id", slot.id, pos=pos)
```

Then `CaptureAnchor` can use `pos` for offsets and `value` for exact target.

```python
def resolve(...):
    cap = captures.get(self.name)
    if cap is None:
        return None

    if self.offset == 0 and cap.kind == "slot_id":
        return cap.value

    if cap.pos is None:
        return None

    idx = cap.pos + self.offset
    if 0 <= idx < len(slots):
        return slots[idx].id
    return None
```

This preserves relative addressing.

#### ScanStart and ScanEnd

```python
ScanStart(offset).resolve(...) -> slots[scan_start + offset].id
ScanEnd(offset).resolve(...) -> slots[firing_pos + offset].id
```

`ScanEnd` remains anchored to most recently consumed position.

### 12.9 Emission Firing

Current `_fire` appends:

```python
LabelDelta(token_index=target, ...)
```

New `_fire` appends:

```python
AddLabel(slot_id=target, ...)
```

If an anchor cannot resolve, no delta is emitted.

## 13. FSMBlock

### 13.1 Current

```python
@dataclass
class FSMBlock:
    name: str
    fsms: list[FSM]
    scanner: FSMScanner = field(default_factory=FSMScanner)
```

### 13.2 Proposed

```python
@dataclass
class FSMBlock:
    name: str
    fsms: list[FSM]
    consumes: str = "token"
    emits_to: str = "token"
    scanner: FSMScanner = field(default_factory=FSMScanner)

    def apply(self, state: ParserState) -> list[RepresentationDelta]:
        deltas: list[RepresentationDelta] = []
        for fsm in self.fsms:
            deltas.extend(
                self.scanner.scan(fsm, state, stream=self.consumes)
            )
        return deltas
```

For now, `emits_to` is metadata. Existing FSM emissions target slots in the consumed stream via anchors. Cross-stream slot creation is done by reducer blocks.

## 14. LexicalBlock

### 14.1 Current Behavior

`LexicalBlock` loops over `state.tokens`.

### 14.2 Proposed

```python
@dataclass
class LexicalBlock:
    name: str
    entries: dict[str, dict[str, float]]
    consumes: str = "token"
    emits_to: str = "token"

    def apply(self, state: ParserState) -> list[RepresentationDelta]:
        deltas = []
        for slot in state.stream(self.consumes):
            key = (slot.text or "").lower()
            for label, weight in self.entries.get(key, {}).items():
                deltas.append(AddLabel(slot.id, label, weight, self.name))
        return deltas
```

This allows lexical blocks over token streams or other text-bearing streams.

## 15. Reducer Blocks

Reducer blocks create slots.

### 15.1 Protocol

A reducer is just a parser block returning `AddSlot`.

```python
class ReducerBlock(Protocol):
    name: str
    consumes: str
    emits_to: str

    def apply(self, state: ParserState) -> list[RepresentationDelta]: ...
```

No separate base class is necessary initially.

### 15.2 CharClassBlock

This can be an annotating block over the char stream.

```python
@dataclass
class CharClassBlock:
    name: str = "char_classes"
    consumes: str = "char"
    emits_to: str = "char"

    def apply(self, state: ParserState) -> list[RepresentationDelta]:
        deltas = []
        for slot in state.stream("char"):
            ch = slot.text or ""
            if ch.isalpha():
                deltas.append(AddLabel(slot.id, "CHAR:LETTER", 1.0, self.name))
            if ch.isdigit():
                deltas.append(AddLabel(slot.id, "CHAR:DIGIT", 1.0, self.name))
            if ch.isspace():
                deltas.append(AddLabel(slot.id, "CHAR:WHITESPACE", 1.0, self.name))
            ...
        return deltas
```

### 15.3 SimpleCharToTokenReducer

This reducer consumes char slots and emits token slots.

Minimum behavior:

```text
letters/digits/underscore runs -> TOKEN:IDENT
digit runs -> TOKEN:NUMBER
operator chars -> TOKEN:OP
whitespace -> optionally skipped or TOKEN:WHITESPACE
```

Pseudo-code:

```python
@dataclass
class SimpleCharToTokenReducer:
    name: str = "char_to_token"
    consumes: str = "char"
    emits_to: str = "token"
    emit_whitespace: bool = False

    def apply(self, state: ParserState) -> list[RepresentationDelta]:
        chars = state.stream(self.consumes)
        deltas = []
        i = 0
        while i < len(chars):
            slot = chars[i]
            ch = slot.text or ""

            if ch.isspace():
                ...
                continue

            if ch.isalpha() or ch == "_":
                start = i
                while i < len(chars) and is_ident_continue(chars[i].text):
                    i += 1
                deltas.append(self._make_token(state, chars[start:i], "TOKEN:IDENT"))
                continue

            if ch.isdigit():
                start = i
                while i < len(chars) and chars[i].text.isdigit():
                    i += 1
                deltas.append(self._make_token(state, chars[start:i], "TOKEN:NUMBER"))
                continue

            deltas.append(self._make_token(state, [slot], f"TOKEN:{operator_label(ch)}"))
            i += 1

        return deltas
```

Slot construction:

```python
def _make_token(self, state, parent_slots, token_label):
    text = "".join(s.text or "" for s in parent_slots)
    start = parent_slots[0].source_span.start
    end = parent_slots[-1].source_span.end
    token = Slot(
        id=state.next_id(self.emits_to),
        kind="token",
        stream=self.emits_to,
        order=parent_slots[0].order,
        text=text,
        source_span=SourceSpan(start, end),
        parents=tuple(ProvenanceEdge("derived_from", s.id) for s in parent_slots),
    )
    token.labels.add(token_label, 1.0)
    token.labels.add(f"TEXT:{text}", 1.0)
    token.labels.add(f"LOWER:{text.lower()}", 1.0)
    return AddSlot(self.emits_to, token, self.name)
```

## 16. Projection

Projection remains separate from parsing.

### 16.1 Best Stream Projection

For overlapping slots, a projection can choose a non-overlapping sequence.

Initial projection:

```python
def project_non_overlapping(
    state: ParserState,
    stream: str,
    score_label_prefix: str | None = None,
) -> list[Slot]:
    ...
```

A simple first version can sort by:

```text
source_span.start
-source_span.length
max label weight
```

and greedily select non-overlapping candidates.

A better later version can use dynamic programming.

### 16.2 Existing Projections

Update existing projection helpers to accept a stream name:

```python
project_spans(state, stream="token", ...)
project_dependency_edges(state, stream="token", ...)
```

## 17. Debug Rendering

### 17.1 render_state

Current renderer assumes one token stream.

Add a stream parameter:

```python
def render_state(state: ParserState, *, stream: str = "token", top_k: int = 5) -> str:
    slots = state.stream(stream)
```

Render:

```text
Layer 2 / stream token
id        order  text     span     labels
token:0   0.0    foo      0..3     TOKEN:IDENT=1.00 TEXT:foo=1.00
```

### 17.2 render_deltas

Support:

```text
AddLabel
AddSlot
```

Example output:

```text
[char_to_token] add_slot stream=token id=token:0 text='foo' labels=TOKEN:IDENT=1.00
[lexicon] add_label slot=token:0 POS:NOUN += 0.55
```

### 17.3 render_trace

Trace rendering should optionally include streams:

```python
render_trace(traces, streams=("token",))
render_trace(traces, streams=("char", "token"))
```

Default remains token stream only for compatibility.

## 18. YAML / Config Support

Initial implementation does not need YAML support for shape-changing reducers.

Small compatibility addition:

```yaml
type: fsm
name: phrase_rules
consumes: token
```

Config loader can default to `"token"` if omitted.

For lexical blocks:

```yaml
type: lexical
name: lexicon
consumes: token
```

Reducer YAML can be deferred.

## 19. Migration Steps

### Step 1: Add slot model

Add `SlotId`, `SourceSpan`, `ProvenanceEdge`, `Slot`.

Keep `Token` compatibility.

### Step 2: Update ParserState

Move to streams while preserving `state.tokens`.

Update `initialize_state`.

### Step 3: Add AddLabel/AddSlot

Introduce new deltas.

Update `apply_deltas`.

Keep `LabelDelta` compatibility.

### Step 4: Update normalization

Normalize all streams with per-stream config fallback.

### Step 5: Update blocks

Update `LexicalBlock` and `FSMBlock` to use streams.

Default to token stream.

### Step 6: Update scanner

Add stream parameter.

Migrate internal frame type from `Token` to `Slot`.

Change anchors and emissions to slot IDs.

### Step 7: Update projections/debug

Add stream parameters and support AddSlot rendering.

### Step 8: Add char initializer and reducer demo

Add `initialize_char_state`, `CharClassBlock`, and `SimpleCharToTokenReducer`.

### Step 9: Add tests

Run old tests.

Add new tests for streams, slots, AddSlot, scanner stream selection, and char-to-token demo.

## 20. Compatibility Shims

### 20.1 Token index compatibility

Old emissions use offsets and token positions. Offsets can continue working because the scanner resolves offsets against the current scanned stream.

Old `LabelDelta(token_index=...)` should be supported briefly.

Implementation helper:

```python
def resolve_delta_slot_id(state: ParserState, d: LabelDelta) -> SlotId | None:
    if d.slot_id is not None:
        return d.slot_id
    if d.token_index is not None:
        tokens = state.tokens
        if 0 <= d.token_index < len(tokens):
            return tokens[d.token_index].id
    return None
```

### 20.2 Token.index compatibility

Existing code may access:

```python
token.index
```

For token-stream slots whose IDs are `token:n`, expose:

```python
@property
def index(self) -> int:
    ...
```

This is a compatibility crutch. New code should use `slot.id` and stream positions.

### 20.3 ParserState constructor compatibility

Existing tests may instantiate:

```python
ParserState(tokens=[...])
```

Options:

1. support an alternate constructor, or
2. allow `tokens` as an optional init field.

Example:

```python
@dataclass(init=False)
class ParserState:
    def __init__(
        self,
        tokens: list[Slot] | None = None,
        streams: dict[str, list[Slot]] | None = None,
        layer: int = 0,
    ):
        if streams is None:
            streams = {}
        if tokens is not None:
            streams["token"] = tokens
        self.streams = streams
        self.layer = layer
        ...
```

## 21. Testing Plan

### 21.1 Existing tests

All existing tests should pass after migration.

If they do not, failures should be categorized:

```text
public API break
token index assumption
scanner offset behavior
debug output change
normalization change
```

### 21.2 Unit tests

#### Slot tests

```text
creates slot
stores labels
stores source_span
stores provenance
exposes token compatibility
```

#### ParserState tests

```text
lazy stream creation
tokens property returns token stream
get_slot works
duplicate slot ID rejected
next_id generates stable IDs
sort_stream orders slots
```

#### Delta tests

```text
AddLabel applies by slot ID
AddSlot adds to stream
AddSlot stream mismatch raises
missing AddLabel target ignored in compatibility mode
```

#### Normalization tests

```text
normalizes all streams
uses stream-specific config
FORGOTTEN is per slot
```

#### Scanner tests

```text
scans token stream by default
scans char stream when requested
emits AddLabel by slot ID
FiringOffset resolves correctly
CaptureAnchor resolves correctly
conditions match Slot
```

#### Block tests

```text
LexicalBlock consumes configured stream
FSMBlock consumes configured stream
existing block defaults are token/token
```

#### Reducer tests

```text
char initializer creates char stream
char class block labels characters
char-to-token reducer creates token slots
token slots have source spans
token slots have derived_from parents
```

### 21.3 Integration tests

#### Existing grammar

Run the default grammar over:

```text
I can book flights.
```

Expected behavior should match previous output modulo slot IDs in traces.

#### Char-to-token demo

Pipeline:

```text
initialize_char_state("foo + 123")
char class block
char-to-token reducer
```

Expected token stream:

```text
foo TOKEN:IDENT
+ TOKEN:PLUS
123 TOKEN:NUMBER
```

#### Ambiguous `>>`

Reducer emits:

```text
SHIFT_RIGHT
GT
GT
```

with overlapping source spans and alternate provenance.

#### Phrase slot

Given token stream:

```text
the cat
```

phrase reducer emits:

```text
PHRASE:NP
```

with parents pointing to token slots.

## 22. Performance Notes

### 22.1 Slot lookup

Use `_slots_by_id` for O(1) label delta application.

### 22.2 Stream sorting

Use dirty flags if sorting becomes expensive.

```python
_dirty_streams: set[str]
```

Sort before scanner access if dirty.

### 22.3 Overlapping slots

Overlapping slots can grow quickly.

Guardrails:

```text
optional slot_filter on scanner
max slots per stream warning
max candidates per source span in reducers
projection checkpoints for expensive downstream grammars
```

Do not add these until a demo exposes the need.

### 22.4 Provenance size

Long spans may create many parent edges.

Initial implementation stores all parents. Optimize later if needed.

Possible future compression:

```text
ProvenanceEdge("derived_from_span", "char:0..char:100")
```

Do not add this now.

## 23. Error Handling

### Duplicate slot ID

Raise `ValueError`.

### AddSlot stream mismatch

Raise `ValueError`.

### AddLabel missing slot

Initially ignore for compatibility, possibly with debug logging.

In strict mode, raise `KeyError`.

### Invalid source span

Do not validate globally. Reducers are responsible for creating sensible spans.

### Scanner empty stream

Return no deltas.

## 24. Documentation Updates

Update these documents or docstrings:

```text
tokens.py
labels.py
normalization.py
pipeline.py
fsm.py
blocks.py
debug.py
projection.py
```

New docs should explain:

```text
Slot
Stream
AddLabel
AddSlot
ProvenanceEdge
shape-changing transducer
```

The README or design notes should include the smallest char-to-token example.

## 25. Example API After Migration

```python
from fsm_parser import (
    initialize_char_state,
    Parser,
    ParserConfig,
    CharClassBlock,
    SimpleCharToTokenReducer,
)

parser = Parser(
    layers=[
        [CharClassBlock()],
        [SimpleCharToTokenReducer()],
    ],
    config=ParserConfig(),
)

state = parser.parse_state(initialize_char_state("foo + 123"))

print(render_state(state, stream="char"))
print(render_state(state, stream="token"))
```

Expected token stream:

```text
token:0  foo  TOKEN:IDENT=1.00 TEXT:foo=1.00
token:1  +    TOKEN:PLUS=1.00 TEXT:+=1.00
token:2  123  TOKEN:NUMBER=1.00 TEXT:123=1.00
```

The exact parser API may remain `parse(text)` for token initialization. For char initialization, add either:

```python
parse_state(state)
```

or:

```python
parse(text, initializer=initialize_char_state)
```

Preferred:

```python
parse_state(state)
```

because it keeps initialization explicit and supports future non-text states.

## 26. API Additions

### Parser.parse_state

Add:

```python
def parse_state(self, state: ParserState) -> ParserState:
    ...
```

Existing:

```python
def parse(self, text: str) -> ParserState:
    return self.parse_state(initialize_state(text))
```

Similarly:

```python
def parse_state_with_trace(self, state: ParserState) -> tuple[ParserState, list[LayerTrace]]:
    ...
```

Existing trace method delegates to token initialization.

This avoids forcing all future inputs through `text -> token`.

## 27. Acceptance Criteria

The feature is complete when:

1. Existing token-based parser examples still work.
2. Existing tests pass with compatibility shims.
3. `ParserState` supports multiple streams.
4. Deltas can add labels by slot ID.
5. Deltas can add new slots.
6. Scanner can scan a selected stream.
7. Normalization works across streams.
8. Debug rendering can render selected streams.
9. A char-to-token reducer creates token slots from character slots.
10. Token slots preserve source spans and provenance.
11. Projection/debug tools can inspect both char and token streams.

## 28. Future Work

### Full token lattice projection

Overlapping slots are enough for storage. Projection may need a dynamic programming selector for best token stream.

### YAML reducer specs

Grammar YAML can grow support for reducer blocks after the Python API stabilizes.

### Phrase and semantic reducers

Add `token -> phrase` and `phrase/token -> semantic` examples.

### Markdown authoring pipeline

Use streams:

```text
char -> line -> block -> section -> semantic
```

to test document-level shape-changing.

### Learned reducers

A future learner can propose `AddSlot` rules from examples, such as character spans that should become token slots or token spans that should become phrase slots.

## 29. Summary

Shape-changing transducers require a small but important generalization of the runtime model.

The implementation should add:

```text
Slot
SourceSpan
ProvenanceEdge
ParserState.streams
AddLabel
AddSlot
scanner stream selection
per-stream normalization
```

It should not add destructive graph mutation.

The core rule remains:

```text
Blocks add evidence.
They do not erase evidence.
Projection decides what structure to read.
```

This design makes tokenization, phrase formation, semantic insertion, and document-level interpretation part of the same accretion architecture instead of special cases outside the parser.

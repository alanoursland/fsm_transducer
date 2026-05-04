# Designing a Better FSM Core

## Motivation

The current FSM core (`src/fsm_parser/fsm.py`) is enough to demonstrate the architecture and run a small grammar, but its limits show up immediately if you try to express anything beyond linear patterns and trivial branches.

1. **No epsilon transitions.** Every transition consumes a token. Alternation, optionality, and repetition all require copy-pasting state subgraphs by hand. The `FSMBuilder` low-level API is too verbose for real authoring, and `compile_linear` only handles a flat sequence with no choice or repetition.

2. **Conditions are flat.** `HasLabel` / `HasAnyLabel` / `HasAllLabels` / `Always` cover common cases, but there is no negation, no logical combinator, no positional guard, no zero-width assertion, and no way to look at where you are in the sentence. Every new condition shape requires a new dataclass.

3. **Emissions cannot reference earlier tokens in the path.** An emission's only anchor is a fixed offset from the transition that fired it. There is no way to say "emit `SUBJECT_OF:k` on this token, where `k` is the token that matched two states ago." Long-distance pointer labels are exactly the kind of thing that motivates a stateful FSM, and the current emission model cannot express them.

4. **Path weight semantics are vague.** The scanner takes a `combine` callable defaulting to multiplication. Path weights, transition weights, and emission weights all flow through the same operator without a stated algebra. Two paths that reach the same state along different routes are not merged; they remain as separate active paths and produce separate deltas, which makes label totals over-count.

5. **No FSM composition.** Two existing FSMs cannot be concatenated, alternated, or repeated to produce a new FSM. Every machine is hand-built end-to-end.

6. **No state-level emissions or guards.** Everything attaches to transitions. State-entry and state-accept hooks would simplify a number of natural patterns where many transitions converge on the same accept and all of them want the same emission.

The point of this document is to design a successor FSM core that fixes these limits without giving up the strengths of the current implementation: an explicit state graph, an NFA-style scanner, emit-as-deltas (no in-block mutation), and a uniform `ParserBlock` interface.

## Design Goals

- **Compositional.** A small set of combinators (concat, alt, star, plus, optional, repeat) over machines, in the spirit of Thompson construction.
- **Semantically explicit.** Weights live in a stated semiring; path merging and emission scaling have algebraic identities you can reason about.
- **Expressive emissions.** Emissions can target captured tokens, scan-relative positions, or computed indices, and label strings can interpolate captured values.
- **Stateful enough.** A per-path register file lets transitions remember tokens they have already seen in the same path.
- **Authorable.** The builder API and the YAML form should make hand-writing real grammars practical, not just toy ones.
- **Backwards-friendly.** Anything the current core can do — linear patterns, single-token conditions, transition emissions — should map onto the new core with no loss of meaning.

## Core Abstractions

### States

States remain opaque (`StateId(value, name)`) but gain optional **state-level emission lists**:

```python
@dataclass(frozen=True)
class StateId:
    value: int
    name: str | None = None

@dataclass(frozen=True)
class StateInfo:
    on_enter: tuple[Emission, ...] = ()
    on_accept: tuple[Emission, ...] = ()
```

`on_enter` fires every time a path enters the state along any transition; `on_accept` fires only when the path goes on to accept (so it is gated like transition emissions are today). State-level emissions are sugar — equivalent to attaching the same emission to every incoming or every accepting transition — but they read better when many transitions converge on the same accept state.

### Transitions

Transitions gain an explicit kind (consuming vs epsilon), a capture list, and an optional priority:

```python
@dataclass(frozen=True)
class Transition:
    target: StateId
    condition: Condition
    weight: float = 1.0
    emissions: tuple[Emission, ...] = ()
    captures: tuple[Capture, ...] = ()
    epsilon: bool = False    # if True, no token is consumed; condition must be Always
    priority: int = 0        # higher = preferred under priority disambiguation
```

Epsilon transitions are the missing primitive; they unlock Thompson-style construction. Priority is optional — the scanner is NFA-default — but lets you express "longest-match wins" or "rule A overrides rule B" without abandoning the NFA model.

### Conditions, composable

Conditions become a small algebra rather than a fixed enum of dataclasses:

```python
class Condition(Protocol):
    def matches(self, frame: Token, ctx: ScanContext) -> bool: ...

@dataclass(frozen=True)
class Not:
    inner: Condition

@dataclass(frozen=True)
class And:
    parts: tuple[Condition, ...]

@dataclass(frozen=True)
class Or:
    parts: tuple[Condition, ...]
```

The existing `HasLabel`, `HasAnyLabel`, and `Always` stay. Positional and weight-threshold conditions cover patterns the current core can't express:

```python
@dataclass(frozen=True)
class AtSentenceStart: ...
@dataclass(frozen=True)
class AtSentenceEnd: ...
@dataclass(frozen=True)
class WeightAbove:
    label: str
    threshold: float
@dataclass(frozen=True)
class WeightBelow:
    label: str
    threshold: float
@dataclass(frozen=True)
class LabelPredicate:
    """Test every label name against a Python predicate (prefix, regex, etc)."""
    predicate: Callable[[str], bool]
```

`ScanContext` exposes everything a condition might need beyond a single token: position relative to scan start, sentence boundaries, and a read-only view of the path's captures.

### Captures

A capture binds a name to information about the token that triggered the transition. Captures live in a per-path register file:

```python
@dataclass(frozen=True)
class Capture:
    name: str
    kind: Literal["index", "top_label", "bag"] = "index"
```

When a transition fires with captures, the resulting path's register file is updated; later captures with the same name shadow earlier ones. The default `kind` is `"index"`, which records the index of the matched token; `"top_label"` records the highest-weighted label name; `"bag"` records the full label bag (expensive, used only when downstream rules need to inspect the captured token's full context, e.g., for agreement).

### Emissions

Emissions gain richer anchors:

```python
class EmissionAnchor(Protocol):
    def resolve(self, path: PathState, ctx: ScanContext) -> int | None: ...

@dataclass(frozen=True)
class FiringOffset:
    offset: int = 0           # current behavior; the default

@dataclass(frozen=True)
class CaptureAnchor:
    name: str                 # token index = path.captures[name] + offset
    offset: int = 0

@dataclass(frozen=True)
class ScanStart:
    offset: int = 0

@dataclass(frozen=True)
class ScanEnd:
    offset: int = 0

@dataclass(frozen=True)
class Emission:
    label: str                # may interpolate captures: "SUBJECT_OF:{head}"
    weight: float
    anchor: EmissionAnchor = field(default_factory=FiringOffset)
```

The label is a template string. At emission time the scanner substitutes capture values from the path's register file, so a rule can produce labels like `SUBJECT_OF:5` where `5` is the recorded index of the head noun. This is the missing piece for pointer-style structural labels.

## Weight Algebra: Semirings

The current scanner takes a single `combine` callable. We replace it with an explicit **semiring**, which makes path arithmetic precise and gives us the missing path-merge operation:

```python
class Semiring(Protocol):
    one: float
    zero: float
    def times(self, a: float, b: float) -> float: ...   # along a path
    def plus(self, a: float, b: float) -> float: ...    # merging paths

class ProductReal:
    one = 1.0; zero = 0.0
    def times(self, a, b): return a * b
    def plus(self, a, b): return a + b

class LogSemiring:                     # weights are negative log-probabilities
    one = 0.0; zero = float("inf")
    def times(self, a, b): return a + b
    def plus(self, a, b):
        return -math.log(math.exp(-a) + math.exp(-b))

class TropicalMin:                     # min-plus, "best path"
    one = 0.0; zero = float("inf")
    def times(self, a, b): return a + b
    def plus(self, a, b): return min(a, b)
```

`times` is what we currently call `combine` — used for conjunctive accumulation along a single path. `plus` is the missing operation: when two active paths reach the same `(state, capture-signature)` configuration, the scanner merges them with `plus`. Without a `plus`, parallel paths produce duplicate deltas and the runtime active-set grows with the input length; with a chosen semiring, the runtime stays bounded and the semantics are stated.

Default: `ProductReal`, matching today's `operator.mul`. Real applications can pick `TropicalMin` for best-path semantics or `LogSemiring` for log-domain probabilities.

## FSM Combinators

Hand-building large machines with `FSMBuilder` is tedious. We add a Thompson-style combinator layer:

```python
def literal(condition: Condition, *,
            emissions: Iterable[Emission] = (),
            captures: Iterable[Capture] = ()) -> FSM: ...

def epsilon(*, emissions: Iterable[Emission] = ()) -> FSM: ...

def concat(*machines: FSM) -> FSM: ...
def alt(*machines: FSM) -> FSM: ...
def star(machine: FSM) -> FSM: ...
def plus(machine: FSM) -> FSM: ...
def optional(machine: FSM) -> FSM: ...
def repeat(machine: FSM, min_n: int, max_n: int | None) -> FSM: ...
```

Each combinator builds a fresh state graph with a single start state and a single accept state, joined to its arguments by epsilon transitions. The result still satisfies the `FSM` protocol the scanner consumes.

A determiner-noun phrase rule, today written as

```python
compile_linear(
    "np_det_noun",
    [HasLabel("POS:DET", 0.3), HasLabel("POS:NOUN", 0.3)],
    [Emission("PHRASE:NP_HEAD", 0.8)],
)
```

becomes, in the combinator layer

```python
np = concat(
    literal(HasLabel("POS:DET", 0.3), captures=[Capture("det")]),
    star(literal(HasLabel("POS:ADJ", 0.3))),
    literal(
        HasLabel("POS:NOUN", 0.3),
        captures=[Capture("head")],
        emissions=[
            Emission("PHRASE:NP_START", 0.7, anchor=CaptureAnchor("det")),
            Emission("PHRASE:NP_HEAD", 0.8),
            Emission("PHRASE:NP_END", 0.7),
            Emission("HEAD_OF:{det}", 0.6, anchor=CaptureAnchor("head")),
        ],
    ),
)
```

That is a real grammar fragment — determiner, optional adjectives, noun head — expressed compositionally and producing pointer-style emissions that name the determiner index in the label.

## Subroutines

Combinators handle most reuse, but invoking a named NP grammar inside a VP grammar is cleaner with explicit subroutines:

```python
def call(machine: FSM, *, captures_prefix: str | None = None) -> FSM: ...
```

`call` is implemented internally as an epsilon edge into the called machine's start, and an epsilon edge from each of its accepts back into a fresh accept state. Captures from the inner machine can be optionally prefixed to avoid name collisions with the caller. This is enough for grammar reuse without introducing a separate non-terminal/terminal distinction.

## Execution Model

The scanner becomes:

```text
PathState = (state, register_file, weight, pending_emissions)

scan_from(start_pos):
    frontier = epsilon_closure({(fsm.start, {}, semiring.one, ())})
    emit_for_accepting_paths(frontier, scan_start=start_pos)

    pos = start_pos
    while frontier and pos < n:
        successors = []
        for path in frontier:
            for tr in fsm.consuming_transitions_from(path.state):
                if tr.matches(tokens[pos], ctx_for(path, pos)):
                    successors.append(advance(path, tr, pos))
        successors = merge_by(state, register_signature)(successors,
                                                         using=semiring.plus)
        successors = epsilon_closure(successors)
        emit_for_accepting_paths(successors, scan_start=start_pos)
        frontier = successors
        pos += 1
```

Two changes from the current scanner:

1. **Epsilon-closure** at every step. Implemented via worklist with visited-state tracking to handle cycles cleanly.
2. **Path merging** by `(state, register signature)`. Merging keeps the active set bounded by `|states| × |reachable register configurations|` rather than letting it grow with input length. For grammars without captures this collapses to `|states|` and matches textbook NFA simulation cost. With captures, it bounds the blowup to "configurations that actually occur," not "every prefix of the input."

The "scan starting at every position" structure is unchanged.

## State-Level Emissions

State-entry and state-accept emissions provide a cleaner home for emissions that should fire regardless of which incoming transition was taken:

```python
fsm.set_state_info(np_head, StateInfo(
    on_accept=(Emission("PHRASE:NP_HEAD", 0.8),),
))
```

Equivalent to attaching the emission to every transition into `np_head`, but expressed once. The scanner fires `on_enter` immediately when a path arrives at the state and `on_accept` when the path's accept-time emissions are realized.

## Migration From The Current Core

The new core is a strict superset of the current one:

| Current | New equivalent |
|---|---|
| `compile_linear(name, conds, ems)` | `concat(*[literal(c) for c in conds[:-1]], literal(conds[-1], emissions=ems))` |
| `Transition(target, cond, weight, ems)` | unchanged |
| `FSMBuilder` low-level API | unchanged (still available; used to implement combinators) |
| `combine=operator.mul` | `semiring=ProductReal()` |
| `Emission(label, weight, offset)` | `Emission(label, weight, anchor=FiringOffset(offset))` |

A compatibility shim can keep the existing `FSMScanner.combine` parameter accepted, mapping it to a semiring whose `plus` is `max` — that semiring matches today's "don't merge, keep the strongest" implicit behaviour, so existing tests continue to pass byte-for-byte.

## Worked Example: Subject-Of Pointer Label

A motivating example the current core cannot express: emit `SUBJECT_OF:k` on the head noun of a noun phrase when that noun phrase is followed by a verb, where `k` is the index of the verb.

```python
np = concat(
    literal(HasLabel("POS:DET", 0.3)),
    star(literal(HasLabel("POS:ADJ", 0.3))),
    literal(HasLabel("POS:NOUN", 0.3), captures=[Capture("head")]),
)

subject_of_verb = concat(
    np,
    literal(
        HasLabel("POS:VERB", 0.3),
        captures=[Capture("verb")],
        emissions=[
            Emission(
                "SUBJECT_OF:{verb}",
                0.6,
                anchor=CaptureAnchor("head"),
            ),
        ],
    ),
)
```

When this runs over `the cat slept`, the path captures `head=1` at the noun and `verb=2` at the verb, then emits `SUBJECT_OF:2` on token 1. A downstream projection step can read those labels into dependency edges with no further parser changes.

## Open Questions

- **Capture types beyond index.** Should captures be able to bind a chunk of label-bag content (the head's full POS distribution, say)? Useful for agreement rules but expensive in memory; default to `"index"` and require explicit opt-in for richer kinds.
- **Emission timing for `on_enter`.** Eager (fire immediately on entry) or accept-gated (buffer like transition emissions)? Two flavours may be worth offering since they encode different intuitions.
- **Determinization.** Worth implementing a subset-construction pass for performance, or is bounded NFA simulation enough given expected grammar sizes? Defer until benchmarks justify it.
- **Anchors for emissions on epsilon transitions.** With no token consumed, `FiringOffset` has no natural anchor. Default to "previous consumed token in this path" or require an explicit anchor like `ScanStart` or `CaptureAnchor`?
- **Priority semantics.** When priorities tie-break, do they prune lower-priority paths immediately (faster) or only at accept time (easier to reason about)?
- **Negative lookahead.** Some patterns ("emit only if the next token is not a verb") want zero-width negative assertions. Build them out of an epsilon transition into a guard state plus a `Not(...)` condition, or add a dedicated `Lookahead` construct?
- **State emissions and the semiring.** Should state-level emissions be weighted by `times(path.weight, em.weight)` like transition emissions? Default yes, but worth stating.
- **Capture-signature granularity for merging.** Two paths with different captures cannot be merged without losing information. Should the scanner offer a "forgetful" mode that drops captures the rest of the FSM no longer references, to enable more merging?

## Summary

The proposed core keeps everything the current implementation gets right — explicit state graph, NFA-style scanner, deltas-not-mutation, scan-from-every-position — and adds:

1. **Epsilon transitions** plus a Thompson-style combinator layer (`concat`, `alt`, `star`, `plus`, `optional`, `repeat`).
2. **Captures** and capture-anchored emissions for pointer-style labels.
3. **Semiring-based weight algebra** with explicit path merging.
4. **Composable conditions** with negation, conjunction, positional and weight-threshold guards.
5. **State-level emissions** for cleaner authoring.
6. **Subroutines** for grammar reuse.

The scanner change is small in spec — add epsilon-closure and merge paths by `(state, register signature)` — but unlocks the expressive power needed for real grammars: alternation, optional modifiers, repetition, long-distance pointer labels, and stated probabilistic semantics when chosen.

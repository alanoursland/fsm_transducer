# Python Software Design Document: Stacked Weighted FSM Parser

## 1. Purpose

This document describes a Python implementation of a non-neural NLP parser based on stacked weighted finite-state machine blocks.

The parser operates over a sequence of tokens. Each token carries a weighted bag of labels. A parser block reads the current token-label sequence and appends new weighted labels to tokens. Blocks are stacked so that later blocks operate on the enriched output of earlier blocks. As processing advances, low-level labels naturally decay while higher-level syntactic and semantic labels emerge.

The parser's core invariant is:

```text
Sequence[TokenWithLabels] -> Sequence[TokenWithLabels]
```

Even if the system later renders a tree, dependency graph, or semantic frame, the parser itself only produces weighted labels attached to tokens.

## 2. Design Goals

The Python version should prioritize clarity, inspectability, and experimentation.

Primary goals:

- Make parser behavior easy to debug.
- Keep the data model simple and serializable.
- Allow multiple FSM blocks to operate over the same input.
- Support weighted labels with decay, normalization, pruning, and a `FORGOTTEN` residue label.
- Allow later layers to create more abstract labels from earlier labels.
- Preserve a uniform input/output shape across all blocks.
- Make the implementation easy to port to Rust later if speed becomes important.

Non-goals for the first implementation:

- Training neural models.
- Producing a mandatory parse tree.
- Perfect linguistic coverage.
- Optimizing for maximum runtime performance.

## 3. Conceptual Model

A token is not special except that it anchors a label bag at a position in the sequence. The token text, token ID, lowercase form, shape, and lexicon entries can all be represented as labels.

Example token-label bag:

```python
{
    "TEXT:book": 1.0,
    "LOWER:book": 1.0,
    "POS:NOUN": 0.62,
    "POS:VERB": 0.38,
    "ROLE:NP_HEAD": 0.41,
}
```

All labels share one bucket. The weights are not strict probabilities over mutually exclusive classes. They are better understood as bounded salience, evidence, or activation scores.

Each parser block is a weighted finite-state transducer-like component:

```text
input labels -> pattern match -> appended label deltas -> normalization
```

Blocks are stacked:

```text
Tokenizer
  -> lexical block
  -> morphology block
  -> local syntax block
  -> phrase pattern block
  -> semantic role block
  -> domain/task block
```

Earlier labels may decay as later labels become more useful.

## 4. Core Data Structures

### 4.1 LabelBag

A `LabelBag` stores weighted labels for one token position.

```python
from dataclasses import dataclass, field

@dataclass
class LabelBag:
    weights: dict[str, float] = field(default_factory=dict)

    def add(self, label: str, weight: float) -> None:
        self.weights[label] = self.weights.get(label, 0.0) + weight

    def get(self, label: str, default: float = 0.0) -> float:
        return self.weights.get(label, default)

    def has(self, label: str, threshold: float = 0.0) -> bool:
        return self.weights.get(label, 0.0) > threshold
```

### 4.2 TokenFrame

A `TokenFrame` represents one token position and its label bag.

```python
@dataclass
class TokenFrame:
    index: int
    text: str
    labels: LabelBag = field(default_factory=LabelBag)
```

The `text` field is retained for convenience, but parser logic should treat token identity as labels such as `TEXT:book`, `LOWER:book`, or `SHAPE:Xxxx`.

### 4.3 ParserState

A `ParserState` is the full sequence at one layer of processing.

```python
@dataclass
class ParserState:
    tokens: list[TokenFrame]
    layer: int = 0
```

Each block receives a `ParserState` and returns a new `ParserState`.

### 4.4 LabelDelta

FSMs should not mutate token labels directly during matching. Instead, they emit deltas. This makes block execution deterministic and easier to debug.

```python
@dataclass
class LabelDelta:
    token_index: int
    label: str
    weight: float
    source: str | None = None
```

The optional `source` field can record which rule or FSM emitted the delta.

## 5. FSM Block Interface

All parser blocks should implement the same interface.

```python
from typing import Protocol

class ParserBlock(Protocol):
    name: str

    def apply(self, state: ParserState) -> list[LabelDelta]:
        ...
```

A block reads the current state and emits deltas. The parser engine applies those deltas after all blocks in a layer have run.

This avoids order-dependent mutation inside a layer.

## 6. Rule Representation

The initial implementation can use a simple pattern/action rule system before introducing a more formal FSM compiler.

### 6.1 Match Condition

A match condition checks whether a token has a label above a threshold.

```python
@dataclass(frozen=True)
class LabelCondition:
    label: str
    min_weight: float = 0.0

    def matches(self, frame: TokenFrame) -> bool:
        return frame.labels.get(self.label) >= self.min_weight
```

### 6.2 Pattern Rule

A pattern rule matches a bounded window of token-label bags and emits labels.

```python
@dataclass
class EmitAction:
    offset: int
    label: str
    weight: float

@dataclass
class PatternRule:
    name: str
    pattern: list[LabelCondition]
    actions: list[EmitAction]
```

Example:

```python
PatternRule(
    name="det_noun_np",
    pattern=[
        LabelCondition("POS:DET", 0.3),
        LabelCondition("POS:NOUN", 0.3),
    ],
    actions=[
        EmitAction(0, "PHRASE:NP_START", 0.6),
        EmitAction(1, "PHRASE:NP_HEAD", 0.8),
        EmitAction(1, "PHRASE:NP_END", 0.6),
    ],
)
```

This is not yet a full FSM, but it provides the first useful version of FSM-like layered recognition.

## 7. FSM Execution Model

A parser block may contain many rules. For each position in the token sequence, the block tries to match each rule. If a rule matches, it emits deltas.

```text
for each block:
    for each position:
        for each rule:
            if pattern matches at position:
                emit label deltas
```

Later, this can be replaced with a compiled FSM representation for efficiency.

## 8. Normalization, Decay, and Pruning

After deltas are applied, each token's label bag is normalized.

The normalization layer should perform four operations:

1. Apply decay to existing labels.
2. Add new deltas.
3. Prune low-weight labels.
4. Move pruned weight into `FORGOTTEN`.
5. Rescale weights so each token has a stable total mass.

Example function signature:

```python
def normalize_label_bag(
    bag: LabelBag,
    *,
    decay: float = 0.95,
    min_weight: float = 0.001,
    max_labels: int = 64,
    forgotten_label: str = "FORGOTTEN",
) -> LabelBag:
    ...
```

The `FORGOTTEN` label is not semantic. It is accounting residue. It keeps the distribution normalized after weak labels are pruned.

## 9. Parser Engine

The parser engine coordinates block execution.

```python
@dataclass
class ParserConfig:
    decay: float = 0.95
    min_weight: float = 0.001
    max_labels_per_token: int = 64
    forgotten_label: str = "FORGOTTEN"

@dataclass
class Parser:
    layers: list[list[ParserBlock]]
    config: ParserConfig

    def parse(self, text: str) -> ParserState:
        state = initialize_state(text)
        for layer_index, blocks in enumerate(self.layers):
            deltas: list[LabelDelta] = []
            for block in blocks:
                deltas.extend(block.apply(state))
            state = apply_deltas_and_normalize(state, deltas, self.config)
            state.layer = layer_index + 1
        return state
```

A layer may contain multiple blocks that operate on the same input state. Their deltas are combined before normalization.

## 10. Tokenization

The first tokenizer can be intentionally simple:

```python
def tokenize(text: str) -> list[str]:
    return text.split()
```

A more capable tokenizer can be added later.

The initializer should attach basic labels:

```python
def initialize_state(text: str) -> ParserState:
    tokens = []
    for i, raw in enumerate(tokenize(text)):
        frame = TokenFrame(index=i, text=raw)
        frame.labels.add(f"TEXT:{raw}", 1.0)
        frame.labels.add(f"LOWER:{raw.lower()}", 1.0)
        frame.labels.add("TOKEN", 1.0)
        tokens.append(frame)
    return ParserState(tokens=tokens, layer=0)
```

## 11. Example Blocks

### 11.1 POS Dictionary Block

A POS dictionary is a one-token FSM.

```python
class POSDictionaryBlock:
    name = "pos_dictionary"

    def __init__(self, entries: dict[str, dict[str, float]]):
        self.entries = entries

    def apply(self, state: ParserState) -> list[LabelDelta]:
        deltas = []
        for token in state.tokens:
            key = token.text.lower()
            for label, weight in self.entries.get(key, {}).items():
                deltas.append(LabelDelta(token.index, label, weight, self.name))
        return deltas
```

Example entries:

```python
{
    "the": {"POS:DET": 1.0},
    "book": {"POS:NOUN": 0.6, "POS:VERB": 0.4},
    "can": {"POS:AUX": 0.7, "POS:NOUN": 0.3, "POS:VERB": 0.2},
}
```

### 11.2 Context Block

A context block can boost or suppress labels using nearby token labels.

Example:

```text
DET + ambiguous token -> boost POS:NOUN on second token
AUX + ambiguous token -> boost POS:VERB on second token
```

### 11.3 Phrase Block

A phrase block can emit labels such as:

```text
PHRASE:NP_START
PHRASE:NP_HEAD
PHRASE:NP_END
ROLE:SUBJECT_CANDIDATE
ROLE:OBJECT_CANDIDATE
```

The output is still only token labels.

## 12. Optional Tree Projection

The parser does not need to build a tree internally.

If a tree is needed, it can be projected from token labels after parsing. For example:

```text
PHRASE:NP_START + PHRASE:NP_END -> NP span
ROLE:SUBJECT_CANDIDATE near VERB_GROUP -> subject edge
ROLE:OBJECT_CANDIDATE after VERB_GROUP -> object edge
```

This projection should live outside the parser core.

Suggested interface:

```python
def project_tree(state: ParserState) -> object:
    ...
```

The projected tree is a rendering, not the native parse representation.

## 13. Debugging and Inspection

Inspectability is one of the main reasons to start in Python.

The implementation should include tools for:

- Printing top labels per token.
- Showing label changes after each layer.
- Tracing which block emitted which label.
- Comparing outputs before and after normalization.
- Rendering a table of tokens and labels.

Example debug output:

```text
Layer 2
0  The      POS:DET=.71 TOKEN=.12 LOWER:the=.09 FORGOTTEN=.01
1  book     POS:NOUN=.48 PHRASE:NP_HEAD=.31 POS:VERB=.16 FORGOTTEN=.01
2  fell     POS:VERB=.62 EVENT=.21 TOKEN=.07 FORGOTTEN=.01
```

## 14. Serialization

Rules, dictionaries, and parser configs should be serializable as JSON or YAML.

Recommended file layout:

```text
parser_project/
  pyproject.toml
  src/
    fsmparser/
      __init__.py
      labels.py
      state.py
      blocks.py
      rules.py
      engine.py
      normalize.py
      tokenize.py
      debug.py
      projection.py
  rules/
    pos_dictionary.yaml
    phrase_rules.yaml
    semantic_rules.yaml
  tests/
    test_labels.py
    test_normalize.py
    test_pos_block.py
    test_engine.py
  examples/
    inspect_sentence.py
```

## 15. Testing Strategy

Start with small deterministic tests.

Important tests:

- Token initialization creates expected labels.
- POS dictionary emits expected weighted labels.
- Pattern rules match expected windows.
- Deltas are applied after block execution, not during matching.
- Normalization preserves total mass.
- Pruned labels contribute to `FORGOTTEN`.
- Earlier labels decay across layers.
- Layer output remains a token-label sequence.

Example test case:

```python
def test_det_noun_rule_emits_np_head():
    state = initialize_state("the book")
    state.tokens[0].labels.add("POS:DET", 1.0)
    state.tokens[1].labels.add("POS:NOUN", 1.0)

    block = RuleBlock([det_noun_np_rule])
    deltas = block.apply(state)

    assert any(d.token_index == 1 and d.label == "PHRASE:NP_HEAD" for d in deltas)
```

## 16. Performance Notes

The initial Python implementation will likely be fast enough for experimentation on short and medium texts.

Potential bottlenecks:

- Matching many rules at every token position.
- Large label bags.
- Repeated string lookups.
- Debug tracing.

Later optimizations:

- Intern labels as integer IDs.
- Compile rules into transition tables.
- Use arrays for label weights.
- Separate debug mode from fast mode.
- Move the core matcher to Rust and expose Python bindings with `pyo3`.

## 17. Implementation Roadmap

### Phase 1: Minimal Working Parser

- Implement `LabelBag`, `TokenFrame`, `ParserState`.
- Implement token initialization.
- Implement POS dictionary block.
- Implement normalization with decay, pruning, and `FORGOTTEN`.
- Implement parser engine.
- Add debug table output.

### Phase 2: Rule Blocks

- Implement label conditions.
- Implement pattern rules.
- Implement rule block execution.
- Add phrase rules.
- Add context-sensitive POS refinement rules.

### Phase 3: Layered Abstraction

- Define lexical, context, phrase, role, and semantic layers.
- Add layer-by-layer inspection.
- Tune decay and pruning.
- Add simple evaluation examples.

### Phase 4: Optional Projection

- Implement span projection from token labels.
- Implement dependency-like edge projection if needed.
- Keep projection separate from parser core.

### Phase 5: Optimization and Portability

- Add label interning.
- Add compiled FSM representation.
- Benchmark rule matching.
- Consider a Rust core only after the Python behavior stabilizes.

## 18. Open Design Questions

The implementation should leave room to explore these questions:

- Should all labels decay at the same rate, or should some labels be stickier?
- Should token identity labels be replenished at every layer?
- Should normalization preserve a fixed total mass per token?
- How should negative evidence be represented?
- Should blocks be allowed to suppress labels, or only add labels?
- What is the best way to express long-distance dependencies while preserving the token-label invariant?
- When projecting a tree, should the parser choose a single best tree or expose a weighted forest?

## 19. Summary

The Python parser should be built around one durable abstraction:

```text
A parser state is a sequence of tokens, and each token has one weighted label bag.
```

Every parser block reads that state and emits weighted label deltas. Layers stack these blocks to transform low-level token evidence into higher-level syntactic and semantic evidence. Weak labels decay and are pruned into `FORGOTTEN`, keeping the system bounded and normalized.

Trees and graphs are optional projections. The native parser output remains weighted labels attached to tokens.

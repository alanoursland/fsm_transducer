# Python Stacked Weighted FSM Parser — Milestone Plan

## Purpose

This document defines implementation milestones for a Python prototype of the stacked weighted FSM parser.

The goal is to build a working parser whose core invariant is:

> A sequence of tokens enters each block, and the output is the same sequence of tokens with updated weighted labels.

The parser does not require neural networks. It uses stacked finite-state-machine-style blocks that read token label bags, emit new labels, decay old labels, normalize weights, and optionally project final labels into higher-level structures such as spans, dependencies, or trees.

## Guiding Principles

Keep the first version simple, inspectable, and deterministic.

Prefer small composable pieces over a clever general engine too early.

Every layer should be debuggable. The system should be able to show what labels existed before a block, what rules fired, what labels were added, and what was pruned or decayed.

The parser's native output remains token-attached weighted labels. Trees or other structures are optional projections.

## Milestone 0 — Repository and Development Skeleton

### Goal

Create the initial project structure, tooling, and conventions.

### Deliverables

- Python package skeleton.
- Basic test setup.
- Formatting and linting configuration.
- Minimal command-line entry point.
- Example input/output fixture directory.

### Suggested Structure

```text
fsm_parser/
  __init__.py
  labels.py
  tokens.py
  fsm.py
  blocks.py
  normalization.py
  pipeline.py
  debug.py
  projection.py
examples/
  simple_pos.py
  simple_np.py
tests/
  test_labels.py
  test_fsm.py
  test_pipeline.py
pyproject.toml
README.md
```

### Acceptance Criteria

- The package imports successfully.
- Tests run with `pytest`.
- A placeholder CLI command accepts text and prints token objects.

## Milestone 1 — Core Data Model

### Goal

Implement the fundamental objects that represent tokens, labels, weights, and label bags.

### Deliverables

- `Token` object with text, index, and label bag.
- `Label` representation, likely as a string initially.
- `LabelBag` object or dictionary wrapper.
- Basic label operations: add, set, decay, normalize, prune, merge.
- Reserved labels such as `FORGOTTEN`, `TEXT:<value>`, `LOWER:<value>`, and optionally `INDEX:<n>`.

### Design Notes

Do not over-engineer labels yet. Plain strings are acceptable for version one.

Example:

```python
Token(
    text="book",
    index=0,
    labels={
        "TEXT:book": 1.0,
        "LOWER:book": 1.0,
    },
)
```

### Acceptance Criteria

- Tokens can be created from raw text.
- Labels can be added with weighted deltas.
- Label bags can be normalized into a bounded total mass.
- Weak labels can be pruned into `FORGOTTEN`.

## Milestone 2 — Tokenization and Initial Labeling

### Goal

Create the first input layer that converts text into tokens with initial identity labels.

### Deliverables

- Basic tokenizer.
- Initial label assignment.
- Configurable token normalization, such as lowercase forms.
- Basic punctuation handling.

### Acceptance Criteria

For input:

```text
The cat slept.
```

The system produces tokens resembling:

```text
0: The   {TEXT:The, LOWER:the}
1: cat   {TEXT:cat, LOWER:cat}
2: slept {TEXT:slept, LOWER:slept}
3: .     {TEXT:., PUNCT}
```

## Milestone 3 — FSM Rule Representation

### Goal

Define a simple, readable way to express rules that inspect token labels and emit new labels.

### Deliverables

- `Rule` object.
- Match predicates over labels.
- Weighted emissions.
- Optional lookback/lookahead window support.
- Rule names for debugging.

### Initial Rule Shape

A first version can be deliberately simple:

```python
Rule(
    name="det_boosts_next_noun",
    pattern=[HasLabel("DET"), HasAnyLabel("NOUN", "NOUN_CANDIDATE")],
    emissions=[Emit(offset=1, label="NOUN", weight=0.3)],
)
```

### Acceptance Criteria

- A rule can match a sequence of token label bags.
- A rule can emit one or more weighted labels onto matched tokens.
- Rule firing events can be recorded for debugging.

## Milestone 4 — FSM Block Execution

### Goal

Implement blocks that run a collection of FSM-style rules over a token sequence.

### Deliverables

- `FSMBlock` class.
- Sequential or parallel rule application mode.
- Block-level decay configuration.
- Block-level normalization configuration.
- Debug trace of fired rules.

### Execution Model

A block should:

1. Read the current token label sequence.
2. Find matching rule patterns.
3. Collect label emissions.
4. Apply emissions.
5. Decay existing labels.
6. Normalize and prune label bags.
7. Return the updated token sequence.

### Acceptance Criteria

- A block can add POS labels from lexical rules.
- A block can add context labels based on neighboring labels.
- Debug output can explain which rules fired and where.

## Milestone 5 — Normalization, Decay, and Pruning

### Goal

Make label weights stable across many stacked blocks.

### Deliverables

- Decay strategy.
- Normalization strategy.
- Top-k pruning.
- Threshold pruning.
- `FORGOTTEN` mass accounting.
- Tests for conservation or boundedness of weight mass.

### Design Notes

The `FORGOTTEN` label should usually remain small. It exists to absorb pruned weight and preserve a normalized distribution, not to carry meaning.

Potential configuration:

```python
NormalizationConfig(
    total_mass=1.0,
    prune_below=0.01,
    keep_top_k=16,
    forgotten_label="FORGOTTEN",
)
```

### Acceptance Criteria

- Labels decay when not refreshed.
- New labels can replace older low-level labels over multiple layers.
- Pruned weights accumulate into `FORGOTTEN`.
- Label bags remain bounded after every block.

## Milestone 6 — Pipeline Composition

### Goal

Stack blocks into a complete parser pipeline.

### Deliverables

- `ParserPipeline` class.
- Ordered block execution.
- Per-layer snapshots.
- Debug rendering for each layer.
- Configurable final output.

### Acceptance Criteria

- A sentence can pass through multiple blocks.
- Each layer operates on the previous layer's output.
- Earlier labels can decay out as more abstract labels emerge.
- The full trace can be printed or serialized.

## Milestone 7 — First Grammar Prototype

### Goal

Build a small working grammar to prove the architecture.

### Deliverables

- Tiny POS dictionary block.
- Morphology/shape block.
- Noun phrase block.
- Verb phrase block.
- Subject/object candidate block.
- Example sentences.

### Example Sentences

```text
The cat slept.
The dog chased the ball.
I can book flights.
The book fell.
```

### Acceptance Criteria

The parser should demonstrate contextual disambiguation:

```text
book
```

In:

```text
I can book flights.
```

`book` should drift toward verb-like labels.

In:

```text
The book fell.
```

`book` should drift toward noun-like labels.

## Milestone 8 — Optional Structure Projection

### Goal

Create optional projections from token labels into spans, dependencies, or trees without changing the parser's native output type.

### Deliverables

- Span projection from labels such as `NP_START`, `NP_INSIDE`, `NP_END`, `NP_HEAD`.
- Dependency projection from labels such as `SUBJECT_OF:<index>` or `OBJECT_OF:<index>`.
- Simple tree rendering if enough labels are present.

### Acceptance Criteria

- The parser can still return only token labels.
- A separate projection function can render phrase-like structures.
- Projection failure does not mean parser failure.

## Milestone 9 — Configuration Format

### Goal

Move rules and blocks out of Python code into data files.

### Deliverables

- YAML or JSON rule format.
- Loader for blocks.
- Validation errors for malformed rules.
- Example grammar files.

### Example YAML Sketch

```yaml
blocks:
  - name: pos_dictionary
    rules:
      - name: book_pos
        pattern:
          - has: LOWER:book
        emit:
          - offset: 0
            label: NOUN
            weight: 0.6
          - offset: 0
            label: VERB
            weight: 0.5
```

### Acceptance Criteria

- A simple parser can be defined without writing Python code.
- Rule loading errors are understandable.
- Existing grammar prototype can be represented in config.

## Milestone 10 — Debugging and Visualization

### Goal

Make parser behavior easy to inspect.

### Deliverables

- Text table showing labels per token per layer.
- Rule firing trace.
- Weight changes by label.
- Optional Graphviz or HTML view.

### Acceptance Criteria

Given a sentence, a developer can answer:

- Which labels were present at each layer?
- Which rules fired?
- Which labels decayed?
- Which labels were pruned into `FORGOTTEN`?
- Why did a token receive a particular abstract label?

## Milestone 11 — Test Suite and Golden Fixtures

### Goal

Protect the design as the grammar and engine evolve.

### Deliverables

- Unit tests for data structures.
- Unit tests for rule matching.
- Unit tests for normalization and pruning.
- Golden output tests for example sentences.
- Regression tests for ambiguity cases.

### Acceptance Criteria

- Core behavior is deterministic.
- Expected labels appear with expected relative weights.
- Changes to rules or normalization do not silently break examples.

## Milestone 12 — Performance Pass

### Goal

Identify whether Python is sufficient or whether the core matcher should eventually move to Rust.

### Deliverables

- Benchmark harness.
- Rule matching profiling.
- Token count scaling tests.
- Block count scaling tests.
- Memory usage notes.

### Acceptance Criteria

- Parser can process small documents acceptably for experimentation.
- Hot paths are identified.
- There is enough evidence to decide whether a Rust core is worthwhile.

## Milestone 13 — Package and CLI

### Goal

Make the prototype usable as a local tool.

### Deliverables

- CLI command for parsing text.
- CLI command for showing layer traces.
- CLI command for loading grammar config.
- Basic package metadata.
- README examples.

### Example Commands

```bash
fsm-parser parse "The book fell."
fsm-parser trace "I can book flights."
fsm-parser parse --grammar examples/grammar.yaml input.txt
```

### Acceptance Criteria

- The parser can be installed locally.
- Example grammars run from the command line.
- Output can be emitted as plain text or JSON.

## Milestone 14 — Documentation

### Goal

Document the architecture and implementation well enough for future work.

### Deliverables

- Architecture overview.
- Rule authoring guide.
- Normalization and pruning explanation.
- Debugging guide.
- Projection guide.
- Examples.

### Acceptance Criteria

A new developer can understand:

- What a token label bag is.
- How blocks are stacked.
- How rules fire.
- How labels decay and normalize.
- Why trees are optional projections.

## Suggested Build Order

The most practical order is:

1. Data model.
2. Tokenization.
3. Rule matching.
4. Block execution.
5. Normalization.
6. Pipeline.
7. Tiny grammar.
8. Debug trace.
9. Config format.
10. Projection.
11. Packaging.
12. Performance.

## First Vertical Slice

The first complete slice should be small but end-to-end.

Input:

```text
The book fell.
```

Pipeline:

1. Tokenize.
2. Add lexical labels.
3. Add POS labels.
4. Use context to boost noun interpretation.
5. Add noun phrase labels.
6. Normalize and decay after each block.
7. Print final token labels and layer trace.

Expected final behavior:

```text
The:
  DET
  NP_START

book:
  NOUN
  NP_HEAD

fell:
  VERB
  PREDICATE
```

The exact weights are less important than the fact that the architecture demonstrates stacked abstraction and decaying early labels.

## Open Design Questions

These should remain flexible during the prototype phase:

- Are labels always strings, or do they become structured objects?
- Do blocks apply rules in parallel, sequentially, or both?
- Should emissions be additive, multiplicative, or replacement-based?
- How aggressive should decay be?
- Should identity labels be refreshed every layer or allowed to decay?
- How much lookback/lookahead should rules support?
- Should span-like labels live only on tokens, or should virtual span tokens eventually exist?

## Risks

### Label Explosion

Too many labels may accumulate across blocks.

Mitigation: top-k pruning, threshold pruning, decay, and good debug views.

### Weight Semantics Drift

Weights may become hard to interpret.

Mitigation: avoid calling them probabilities initially. Treat them as salience or activation unless a stricter mathematical interpretation is introduced.

### Rule Interaction Complexity

Rules may reinforce or suppress each other in surprising ways.

Mitigation: rule firing traces and golden tests.

### Premature Generalization

A fully general FSM language could slow implementation.

Mitigation: begin with a small rule model and expand only when examples demand it.

## Definition of Prototype Complete

The prototype is complete when it can:

- Tokenize text.
- Attach initial identity labels.
- Run stacked FSM blocks.
- Add increasingly abstract weighted labels.
- Decay and prune old labels.
- Preserve bounded label distributions with `FORGOTTEN` accounting.
- Demonstrate contextual disambiguation on simple examples.
- Produce readable debug traces.
- Optionally project labels into a simple phrase structure.

At that point, the design is ready for larger grammars, better tooling, and possible Rust acceleration.

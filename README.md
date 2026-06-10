# fsm_transducer

A non-neural, fully inspectable symbolic language parser built on stacked
weighted finite-state machines.

## The idea: parsing as accretion

Most parsers are decision machines: given input, they commit to one structure
(a tree, a dependency graph). This parser is an **accretion machine**. Every
token carries a weighted bag of labels; each FSM block reads labels and adds
more; old labels decay when nothing refreshes them. The parser never picks a
structure — it produces a weighted annotation field, and any tree, span set,
or frame is *projected* downstream by whoever needs one.

```text
Token 3 "book":
  TEXT:book       0.30
  POS:NOUN        0.24
  POS:VERB        0.14
  PHRASE:NP_HEAD  0.18
  ROLE:OBJECT     0.07
```

Why build it this way:

- **Auditability.** Every label is traceable to a named rule and a weighted
  path. The debug renderer answers "which rule contributed how much to which
  label on which token."
- **Provable bounds.** FSM scanning has computable state-space and time
  bounds; `fsm_parser.analysis.analyze()` prints a complexity certificate for
  any machine.
- **Graceful degradation.** There is no "no parse." Ungrammatical input gets
  a weaker label field, not a failure.
- **Deferred commitment.** Inference (label propagation) is separated from
  decision (argmax / threshold / projection), as in Bayesian practice.

The longer argument is in [`notes/parsing_as_accretion.md`](notes/parsing_as_accretion.md).

## Install

```bash
pip install -e .[dev]
pytest
```

## Quickstart

```bash
fsm-parser --grammar src/examples/grammar.yaml "the cat sat on the mat"
```

Or in Python:

```python
from fsm_parser.config import load_grammar
from fsm_parser.pipeline import Parser

grammar = load_grammar("src/examples/grammar.yaml")
state = Parser(grammar.layers).parse("the old book")
for slot in state.tokens:
    print(slot.text, slot.labels.top_k(3))
```

Machines can be written three ways: linear patterns (YAML `pattern:`),
combinators (`concat` / `alt` / `star` / ...), or the regex front-end:

```python
from fsm_parser.regex_compile import compile_regex

np = compile_regex("<POS:DET> <POS:ADJ>* (?P<NP> <POS:NOUN>+)")
```

Named groups emit `NP_START` / `NP_END` / membership labels onto the matched
tokens — states stay anonymous; emissions carry the names.

## Layout

- `src/fsm_parser/` — the library (engine: `fsm.py`; algebra: `semirings.py`;
  regex front-end: `regex_compile.py`; bounds/DFA tools: `analysis.py`)
- `src/tests/` — test suite
- `src/examples/` — example grammars
- `planning/` — design documents, including the
  [improvement plan](planning/improvement_plan.md)
- `notes/` — conceptual notes

## Related project

[`regex_transformer`](https://github.com/alanoursland/regex_transformer)
studies the same question from the opposite direction: what FSM structure a
small transformer internalizes when trained on regular languages. This repo
supplies glass-box machines; that repo probes black-box ones.

# The Codex

The reusable inventory of FSM components. The triad:

- `src/fsm_parser/` — the **engine** (scanner, semirings, analysis)
- `codex/` — the **inventory** (this directory: catalogued components)
- `languages/` — **assembled products** (compositions over the codex)

Languages are not where reusable knowledge lives; languages are
compositions over the codex.

## What a component is

A component is a **factory**, not a file of states: a Python builder
(possibly parameterized — per-identifier checkers, per-depth emitter
schemas) plus a manifest. Kinds: `tracker` (anchored story machines),
`story` (expectation machines), `checker` (per-entity validators),
`emitter_set` (pattern-emitter layers), `vocabulary` (lexicons),
`bundle` (curated import sets).

Every component directory contains `component.yaml`:

```yaml
id: story.minus            # dotted, stable, boring
kind: story
status: gold               # gold = oracle-tested | silver = hand-checked
factory: fsm_parser.imp_lang:build_minus_story
params: {}                 # factory keyword args (schema parameters)
search_terms: [unary binary minus, expectation, operand]
used_by: [imp, pysub, jssub, cpp, mcguffey_primer]
notes: one-line purpose
```

## The catalog (three search surfaces)

`python codex/build_catalog.py` regenerates:

- `CATALOG.md` — for humans
- `catalog.jsonl` — for tools (one component per line)

The generator LOADS each factory, builds the machine, and extracts
its I/O alphabets with `fsm_parser.analysis.signature()` — the
catalog's alphabets are **measured, never declared**, and a component
that does not build cannot be catalogued. It also dumps every machine
component's full built form to `machine.yaml` beside its manifest
(states, transitions, conditions, emissions), provenance-tagged with
the generating factory and params. The dumps are write-only artifacts
— the builders remain the source of truth; freshness is test-enforced
— but the machines themselves are now greppable: four search
surfaces (manifests, jsonl, markdown, and the machines).

## Loading

```python
from fsm_parser import codex
machine  = codex.load("story.minus")
checker  = codex.load("checker.scope.let", name="x")   # schema params
lexicon  = codex.load("lexicon.mcguffey.tier1")
bundle   = codex.load("bundle.english_tier1")          # dict of id -> loaded
hits     = codex.search("operand")                     # manifest search
```

Behaviorally identical to direct imports — the loader resolves to the
same factories the languages already use. Strictness: no component
enters without a manifest; physical relocation of factory code into
codex-owned modules is a later phase (manifests make the move a
one-line edit per component).

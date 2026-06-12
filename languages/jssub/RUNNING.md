# Running the JavaScript subset

Status: **implemented**, runner `fsm_parser.jssub_lang`, golden suite
`src/tests/test_jssub_lang.py`, differential against **imp itself** on
the shared regex-free fragment (same source, both pipelines, equal
outputs/env — jssub restricted to that fragment IS imp).

```python
from fsm_parser.jssub_lang import compile_program, run_program, execute

src = "let r = /ab+/; let x = 10 / 2; print(x); print(r);"
res = execute(src)
res.outputs        # [5.0, RegexVal(pattern='ab+')]

r = compile_program(src)
[s for s in r.state.tokens if "REGEX" in s.labels]
# one synthesized slot: id 'regex:0', text '/ab+/', VAL:ab+,
# provenance edges to the four raw tokens it replaced
```

Reading the field: a `/` that survives to the final stream is always
division (`DIV_OP` + `MULTIPLICATIVE`); regex slashes and their
mis-lexed interiors are gone, merged into `regex:n` slots. The raw
pre-merge tokens are recoverable via the merged slot's `parents`
(provenance edges) — the retokenization is auditable, not destructive.

## Spec-to-code map

| spec feature | implementation |
|---|---|
| naive lexer + OPERAND_END events | `initialize()` |
| slash story machine (3 states) | `build_slash_story()` — keys on the OPERAND_END event label |
| retokenization | `retokenize()` — merges spans, exact pattern from source spans, provenance edges |
| everything downstream | **imported from imp**: bracket tracker, minus story, scope checkers, expression + statement emitters, and `run_program` itself |
| regex values | `RegexVal` in operand resolution; one `push_regex` emitter |

Pipeline order is the load-bearing fact: slash story and retokenize
run BEFORE the bracket tracker, so parens inside regex literals never
reach it (test: `/((a+)b)*/` produces no bracket errors).

Known leak (test-pinned): imp's imported minus story keys on token
classes, not OPERAND_END, so it can't learn that a REGEX completes an
operand — `/a/ - 2` mislabels the minus and the run goes invalid.
Recorded refactor: migrate minus_story to the event label.

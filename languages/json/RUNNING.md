# Running the JSON language

Status: **implemented**, runner `fsm_parser.json_lang`, golden suite
`src/tests/test_json_lang.py` (examples.md transcribed) plus a
200-document differential test against `json.loads`.

```python
from fsm_parser.json_lang import compile_document, run_program, loads

r = compile_document('{"a": 1, "b": [2, 3]}')
[str(i) for i in r.program]
# ['NEW_OBJ', "PUSH 'a'", 'PUSH 1', 'SETK', "PUSH 'b'",
#  'NEW_ARR', 'PUSH 2', 'APPEND', 'PUSH 3', 'APPEND', 'SETK']
run_program(r.program).document   # {'a': 1, 'b': [2, 3]}
loads('{"a": 1')                  # None (field carries ERROR:UNBALANCED_OPEN)
```

Interpretation conventions are the same as `languages/arithmetic/RUNNING.md`
(field + program; errors are located labels, never exceptions; partial
documents on an invalid stack are correctly built fragments). JSON-specific
label families:

| family | meaning |
|---|---|
| `CTX:OBJ:d` / `CTX:ARR:d` | innermost container of an interior token |
| `ENCL:OBJ:d` / `ENCL:ARR:d` | on a closing bracket: the container *around* the one it closes — the label that completes a finished container as a value in its parent |
| `ERROR:MISMATCHED_CLOSE` | `[1}` — bracket-type error, with recovery (pop anyway) |

## Spec-to-code map

| spec feature | implementation |
|---|---|
| shape tracker (15 states + overflow, K=3) | `build_shape_tracker()` — generated over all container stacks, anchored `transduce` |
| emitters | `_emitters()`: three global single-token machines + four tiny per-depth machines; no guards or sentinels needed (the ENCL label replaces them) |
| `!{VAL}` typed resolution | `_resolve_operand()` — argmax-with-margin, typed by the slot's class label |
| builder VM | `run_program()` — five ops, shape-checked (validity condition 3) |

Notable vs arithmetic: JSON needed **no new engine features and no
sentinel tricks** — the shape tracker's context labels carry all the
information the emitters need, so every emitter is one or two tokens
long. The second language was *simpler* than the first, which is
evidence the label-mediated factoring scales the right way.

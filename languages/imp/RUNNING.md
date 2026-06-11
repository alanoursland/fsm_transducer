# Running the tiny imperative language

Status: **implemented**, runner `fsm_parser.imp_lang`, golden suite
`src/tests/test_imp_lang.py` (examples.md transcribed) plus a
150-program differential against transpiled Python.

```python
from fsm_parser.imp_lang import compile_program, run_program, execute

r = compile_program("let x = 3; if x > 1 { print(x); }")
[str(i) for i in r.program]
# ['PUSH 3', 'DECL x', 'LOAD x', 'PUSH 1', 'GT',
#  'BRF', 'ENTER', 'LOAD x', 'PRINT', 'EXIT']
res = run_program(r.program)
res.outputs                # [3]
res.env                    # {'x': 3}
execute("print(y);")       # None — field carries ERROR:UNDECLARED on y
```

Conventions inherited. New label families and behaviors:

| family | meaning |
|---|---|
| `ERROR:UNDECLARED` / `ERROR:REDECLARE` | on the offending identifier token, from that identifier's own scope-checker machine |
| `EXEC.4:DECL(!{VAL@token:k})` | cross-slot operand: the instruction at `;` names the variable token |

Reading failures: a `LOAD`/`STORE` runtime failure should always be
*predicted* by an `ERROR:UNDECLARED` label on the corresponding token —
the static checker and the VM are independent implementations of the
same scope rule, and their agreement is validity condition 3. If they
ever disagree, one of them has a bug; that redundancy is deliberate.

## Spec-to-code map

| spec feature | implementation |
|---|---|
| bracket tracker {P, B}, K=5 | `build_bracket_tracker()` (63 states + overflow) |
| per-identifier scope checkers | `build_scope_checker(name)` — built per input at compile time (input-indexed instantiation), ~252 states each |
| expression emitters | arithmetic's operand/chain/guard construction + IDENT operands + cmp precedence level |
| statement emitters | guard-token patterns (`<not LET> <IDENT> <not ASSIGN>` for LOAD etc.); DECL/STORE name their variable via slot-id capture + template interpolation |
| structured control flow | BRF/ENTER/EXIT matched markers; the VM's BRF scans forward counting ENTER/EXIT |

Notable: this is the first language whose checkers are instantiated
from the *input* (one machine per identifier) rather than from the
spec (one per depth). Compile time grows with vocabulary size; each
machine is independently certifiable, like everything else.

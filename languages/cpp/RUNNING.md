# Running the C++ subset

Status: **implemented**, runner `fsm_parser.cpp_lang`, golden suite
`src/tests/test_cpp_lang.py`, 120-program differential against
transpiled Python (shifts are Python-native; transpilation is
line-local).

```python
from fsm_parser.cpp_lang import compile_program, run_program, execute

r = compile_program("vector<vector<int>> v; print(1);")
[s.id for s in r.state.tokens if s.id.startswith("angle:")]
# ['angle:0', 'angle:1'] — the '>>' split into two closers,
# provenance edges back to the original token
execute("int x = 16 >> 2; print(x);").outputs   # [4]
```

Reading the field: a surviving `>>` token is always a shift
(`SHR_OP`); template closers appear as `>` slots (original or
synthesized `angle:n`) carrying `TPL_CLOSE`; comparison angles carry
`GT_OP`/`LT_OP` + `CMP_OP`. The split is auditable via `parents`.

## Spec-to-code map

| spec feature | implementation |
|---|---|
| angle story machine (8 states: depth x template-bit) | `build_angle_story()` |
| retokenization by splitting | `retokenize()` — the dual of jssub's merge |
| type expressions / declaration sites | `_type_expr(k)` recursive combinator; `build_decl_site_marker()` |
| scope checkers | `build_scope_checker()` — imp's bit-stack keyed on DECL_SITE (type-before-name; third adapter for one checker shape) |
| expression emitters | REBUILT from imp's chain helpers: shift layer at rank 4, comparisons over shift chains at rank 5 — imp's cmp emitters were wrong for C++ precedence |
| imported unchanged | bracket tracker, minus story |
| VM | imp's plus SHL/SHR/DECLD |

The global rank renumbering (shift inserted at 4) was committed FIRST
as its own shared-machinery change, gated by all languages' suites —
the process imp's PERSPECTIVE prescribed after the NEG incident.

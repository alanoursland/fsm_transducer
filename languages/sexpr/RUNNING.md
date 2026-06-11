# Running the S-expression language

Status: **implemented**, runner `fsm_parser.sexpr_lang`, golden suite
`src/tests/test_sexpr_lang.py` plus a 200-case round-trip differential
(random structures rendered and re-parsed must equal themselves — the
oracle is identity, no reference parser needed).

```python
from fsm_parser.sexpr_lang import compile_forms, run_program, parse

parse("(define (sq x) (* x x))")
# [['define', ['sq', 'x'], ['*', 'x', 'x']]]
parse("(a) 42 (b c)")          # [['a'], 42, ['b', 'c']]  — a file is a sequence
parse("(a (b")                 # None (ERROR:UNBALANCED_OPEN in the field)

r = compile_forms("(+ 1 2)")
[str(i) for i in r.program]    # ['NEW_LIST', 'PUSH +', 'APPEND', 'PUSH 1', ...]
```

Conventions as in the other two languages. New label family:

| family | meaning |
|---|---|
| `ROLE:HEAD:d` / `ROLE:ARG:d` | positional grammatical relation of an element within its list (on atoms, and on the opening paren of sublists) |

The build instructions ignore roles entirely (everything APPENDs);
they exist for downstream consumers — arity checking, special-form
recognition, evaluation — none of which this language includes. The
parser of `(+ 1 2)` does not add: `+` is a symbol in head position.

## Spec-to-code map

| spec feature | implementation |
|---|---|
| shape/role tracker (15 states + overflow) | `build_shape_role_tracker()` — expectation stacks over {F, R}; the F→R flip on consuming an element is what produces HEAD vs ARG |
| emitters | three global + two tiny per-depth single-token machines |
| sequence-of-forms contract | `RunResult.forms` (stack = top-level forms in order; validity is "stack nonempty", not "exactly one") |

Notable: degradation on `(a (b` leaves **two** correctly built
fragments `[['a'], ['b']]` — the splice that never happened is visible
as stack depth, which is a more informative failure shape than either
arithmetic's or JSON's.

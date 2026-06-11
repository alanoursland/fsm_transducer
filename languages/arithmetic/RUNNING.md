# Running the arithmetic language, and reading what comes out

Status: **implemented.** The runner is `fsm_parser.arithmetic`; the YAML
files in this folder are the contract it implements, and `examples.md`
is its golden acceptance suite (`src/tests/test_arithmetic_lang.py`),
alongside a 300-expression differential test against Python `eval`.

```python
from fsm_parser.arithmetic import compile_expression, run_program, evaluate

result = compile_expression("(1+2)*5")
for ins in result.program:
    print(ins)                      # PUSH 1; PUSH 2; ADD; PUSH 5; MUL
print(result.errors)                # [] — or named, located ERROR:* labels
print(run_program(result.program))  # stack=[15.0], valid=True
evaluate("3+4*2")                   # 11.0 (None if the field has errors)
```

`result.state` is the full label field; inspect any slot's bag with
`result.state.get_slot("token:4").labels.top_k(10)`.

This document explains (1) how to run the same procedure by hand — still
the way to settle contract disputes; (2) how the runner maps onto the
spec; (3) how to interpret the outputs; and (4) what this folder is for.

## 1. Running it by hand

This is the procedure used to validate `examples.md`. For an input like
`( 1 + 2 ) * 5`:

1. **Tokenize** — one slot per number/symbol. Write the slots in a row.
2. **Lexicon pass** (`lexicon.yaml`) — under each slot, write its class
   labels (`NUM`+`VAL:n`, `OP:*`, `LPAREN`, ...).
3. **Depth pass** (`layers.yaml`, `depth_tracker`) — walk left to right
   once, tracking depth on your fingers. Write `DEPTH:d` under every
   slot, `GROUP_START:d` / `GROUP_END:d` on parens. If you end above
   depth 0, write `ERROR:UNBALANCED_OPEN` on the last slot and keep
   going.
4. **Term pass** (one sweep per depth, deepest first) — bracket each
   maximal `* /` chain at that depth; write `TERM_START:d` /
   `TERM_END:d` at its edges. A parenthesized group counts as a single
   operand at the depth *outside* it.
5. **Emission pass** — write `EXEC.0:PUSH(!{VAL})` under every `NUM`.
   For each `* /` operator, write `EXEC.1:MUL|DIV` under the last slot
   of its right operand. For each `+ -`, write `EXEC.2:ADD|SUB` under
   the `TERM_END` slot of its right term.
6. **Projection** — read the `EXEC` labels left to right, and within a
   slot by rank (0, 1, 2; ties: deeper depth first, then leftmost
   operator first). That sequence is the program.

Validation: run the program on a paper stack. One value should remain,
equal to evaluating the expression normally. If an `ERROR:*` label was
written anywhere, expect the validity conditions in `instructions.yaml`
to fail in a diagnosable way instead.

## 2. How the runner maps onto the spec

| spec feature | implementation |
|---|---|
| lexicon classes | `arithmetic.initialize()` (code, not `LexicalBlock` — numbers aren't enumerable entries) |
| anchored depth tracker | `build_depth_tracker()` + the engine's `transduce(..., anchored=True)` (added for this) |
| per-depth machine schemas | `build_term_marker(d)` / emitter builders called for `d` in 3..0 — schema instantiation as a plain loop |
| term/group span tagging | the regex front-end's group decoration (`TERM_{d}` labels; spec family `TERM_START:d` ≡ label `TERM_{d}_START`) |
| `EXEC` rank projection | `compile_expression()` tail: sort by (token order, rank), resolve `!{VAL}` per the argmax-with-margin policy |
| stack VM | `run_program()` |

Two implementation techniques worth knowing because they differ from a
naive reading of `layers.yaml` (the spec's emission anchors are prose;
these are how they're realized):

* **Guard tokens instead of lookahead.** Maximal-munch ("the additive
  operator fires after its *entire* right term") is enforced by
  requiring the pattern to consume one following token that is not a
  depth-d `* /` operator. BOF/EOF sentinel slots (kind `meta`, excluded
  from projection) guarantee the guard token exists at the edges.
* **Capture-anchored emissions.** Each operand's final consuming
  transition writes an `end` register; instructions anchor on it
  (`CaptureAnchor`) — the same tagged-NFA mechanism regex groups use —
  so "last token of the right operand" is exact even when the operand
  is a parenthesized group.

## 3. Interpreting the outputs

A run produces two things — read them together (`instructions.yaml`,
"Output contract"):

**The label field** — every input token with its accumulated labels.
Reading guide by family:

| family | meaning | read it as |
|---|---|---|
| `NUM`, `OP:*`, `LPAREN`/`RPAREN` | token class | "what this token is" |
| `VAL:n` | the literal | where operand references resolve |
| `DEPTH:d` | nesting level | the unrolled pushdown stack |
| `GROUP_START/END:d` | paren span edges | bracket structure, depth d |
| `TERM_START/END:d` | multiplicative span edges | precedence structure |
| `EXEC.r:OP` | an instruction completing here | the program, in place |
| `ERROR:*` | a named, located failure | diagnosis, not a crash |

The field is the parse: spans-with-depth are a bracket serialization of
the expression tree, so if you want a tree, read `GROUP`/`TERM` spans
off as nested brackets. The `EXEC` labels are the same structure
re-expressed as a schedule ("which operation completes at which token").

**The projected program** — the `EXEC` labels in (token order, rank
order). Interpret against the four validity conditions in
`instructions.yaml`:

* all four hold -> a correct compilation; executing it equals
  evaluating the expression;
* stack ends with k > 1 values -> incomplete input (matches an
  `ERROR:UNBALANCED_OPEN`); the k values are the correctly compiled
  fragments;
* instruction/token counts mismatch -> some operator never completed
  (its operand pattern never closed) — find the operator slot with no
  corresponding `EXEC` label downstream; the label field shows exactly
  where the pattern stopped matching.

That last move is the point of the whole design: **every failure is
localized in the field.** There is no "syntax error" exit code; there
is a token carrying the reason.

## 4. What this folder is for

Four uses, in order of immediacy:

1. **A contract.** It fixes the semantics a runner must implement,
   before any implementation exists — the same role an RFC plays.
   Disagreements about behavior get settled by editing YAML and
   re-validating examples by hand, which is much cheaper than editing
   code.
2. **Golden tests in waiting.** The hand-validated tables in
   `examples.md` are the acceptance suite for the future runner,
   already written.
3. **A template.** The folder layout (lexicon / layers / instructions /
   examples, schemas with `forall`, declared exclusions) is the format
   for every future `languages/<name>/` definition. The second language
   will tell us what the format got wrong.
4. **A comparison target.** Train `regex_transformer`-style models on
   these expressions and probe whether their hidden states recover
   `DEPTH:d` and the pending-operator structure this spec makes
   explicit — the glass-box/black-box experiment the two projects exist
   to run.

Items #1 and #2 are done: the runner exists and `examples.md` is its
passing acceptance suite. The live next steps are #3 (a second language,
to stress the folder format) and #4 (the probing experiment against
`regex_transformer`).

# Running the arithmetic language, and reading what comes out

Honest status first: **this folder is a specification, not a program.**
Nothing in it executes today. This document explains (1) what "running"
this language means right now, by hand; (2) what would have to be built
for it to run mechanically, and how much of that already exists; (3) how
to interpret the outputs either way; and (4) what this folder is *for*,
since that can be unclear when nothing in it is executable.

## 1. Running it by hand (works today)

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

## 2. What it would take to run mechanically

Most of the machinery exists in `fsm_parser`; the spec was written
against it deliberately. Gap analysis:

| spec feature | engine status |
|---|---|
| lexicon classes | exists (`LexicalBlock`; `VAL:{TEXT}` needs a capture-template rule, small) |
| term/group span tagging | exists (regex front-end named groups: `TERM` is `(?P<TERM_d> ...)`) |
| per-depth machine schemas | missing, small: a loader loop instantiating one machine per `d` with `DEPTH:d` substituted into conditions |
| anchored depth tracker | **missing, the real gap**: `scan()`/`transduce()` start at every offset; the depth tracker must run exactly once from token 0. Needs `anchored=True` on the scanner (or an `AtSentenceStart`-guarded design) |
| `EXEC` rank projection | missing, trivial: ~30 lines reading the final label field |
| stack VM for validation | missing, trivial: ~15 lines |

So "make it run" is one engine feature (anchored scanning), one loader
(language-folder -> pipeline, including schema instantiation), and two
small scripts. When that lands, `examples.md` stops being documentation
and becomes the **golden test file**: the runner's output on the five
inputs must reproduce those tables exactly.

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

The recommended next step, when ready, is #2: implement anchored
scanning + the language loader + the projection script, and turn
`examples.md` into passing tests.

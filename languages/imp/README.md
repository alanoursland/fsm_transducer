# Language definition: tiny imperative language ("imp")

Fourth language; conventions inherited from `languages/arithmetic/`
(expressions, sentinels, guards), `languages/json/` (two-kind bracket
tracking, ENCL principle), and `languages/sexpr/` (tracker carries
expectation/role state).

```text
let x = 3;
if x > 1 { print(x); }
```

Scope: `let` declarations, assignment, `print(expr);`,
`if expr { ... }` (no else), expressions over `+ - * / > < ==` with
parentheses and **unary minus**, unsigned integer literals,
identifiers. Combined
paren+block nesting to **K = 5** (blocks and parens share the budget;
three block levels plus `print((x))` already needs 5).
Exclusions at the end.

## What this language tests

* **Statements and blocks.** Two bracket kinds with different
  semantics: `( )` groups expressions, `{ }` delimits scoped blocks.
  The tracker's stack alphabet is {P, B} (JSON's {O, A} pattern), but
  unlike JSON the two kinds drive *different downstream machinery*.
* **Structured control flow in the instruction stream.** `if` compiles
  to `BRF` at `{` (pop condition; if false, skip to the matched
  `EXIT`) — matched markers, not address jumps, because emissions
  cannot point forward. Address resolution as a second projection pass
  is the noted v2.
* **Cross-slot operands.** `let x = 3;` must execute `DECL` *after*
  the expression (at the `;`) but name the variable token — the
  emission is `EXEC.4:DECL(!{VAL@{var}})` where `{var}` interpolates a
  slot-id capture of the `x` token. First use of both template
  interpolation and the `!{FAMILY@id}` reference form.
* **Scope, the headline.** Declared-before-use is *not* a regular
  property over unbounded identifiers — but it is regular **per
  identifier**: a stack of one bit ("declared at this block level")
  per nesting level. So the language instantiates one small anchored
  checker per identifier appearing in the input: **input-indexed
  schema instantiation**, a new dimension alongside per-depth
  (`forall d`) instantiation. Each checker emits located
  `ERROR:UNDECLARED` / `ERROR:REDECLARE` labels. Lexical scoping,
  shadowing included, for the price of ~252 states per name.

## Instruction set (instructions.yaml)

`PUSH LOAD DECL STORE ADD SUB MUL DIV GT LT EQ PRINT BRF ENTER EXIT` —
a statement VM with a scope-stack of environments. Validity: the value
stack ends *empty* (statements consume everything); program output is
the print sequence plus the final global environment.

Rank discipline:

| rank | ops | on token |
|---|---|---|
| 0 | PUSH, LOAD, BRF, EXIT | literal / identifier / `{` / `}` |
| 1 | NEG; ENTER | operand end; `{` |
| 2 | MUL, DIV | expression end |
| 3 | ADD, SUB | expression end |
| 4 | GT, LT, EQ | expression end |
| 5 | DECL, STORE, PRINT | `;` |

NEG outranks MUL because `2 * -3` lands NEG and MUL on the same slot
(the `3`); rank 1 < 2 applies the negation first.

## Files

Standard set: `lexicon.yaml`, `layers.yaml`, `instructions.yaml`,
`examples.md`, `RUNNING.md`, `PERSPECTIVE.md`. Runner:
`fsm_parser.imp_lang`. Tests: `src/tests/test_imp_lang.py` (golden +
differential against transpiled Python).

## Deliberate exclusions

* `else`, `while`, bare blocks — `while` needs backward jumps
  (markers can express it; the VM loop is the work); every `{` in v1
  is an if-body;
* ~~unary minus~~ — added in v1.1 via a two-state **story machine**
  (expect-operand / expect-operator) labeling each `-` as
  `MINUS:UNARY` / `MINUS:BINARY`; see notes/story_machines.md. Known
  limitation: consecutive unary minuses without parens (`- -x`)
  collapse to one NEG, because identical `EXEC.1:NEG` labels on one
  slot merge — a label field is a bag, not a multiset. `-(-x)` works
  (different slots). Pinned by a test as documented behavior;
* chained comparisons (`a > b > c` emits per-pair, left-assoc — noted,
  not endorsed);
* booleans as values — comparisons yield 1/0;
* the differential generator avoids shadowing and block-escaping
  variables, because the Python oracle has function scope, not block
  scope; shadowing is covered by golden tests instead.

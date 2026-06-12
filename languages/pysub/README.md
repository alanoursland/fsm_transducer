# Language definition: Python subset ("pysub")

Fifth language. Conventions inherited; the canonical program:

```python
x = 3
if x > 1:
    print(x)
```

Scope: assignment (which declares — no `let`), `print(expr)`,
`if expr:` with indented blocks, expressions over `+ - * / > < ==`
with parens and unary minus, unsigned int literals, identifiers.
Indent stack depth to **K_layout = 4**; paren depth shares imp's K=5
budget (blocks no longer consume expression depth — an improvement
over imp, where braces and parens shared one budget).

## What this language tests

* **Layout-sensitive tokenization.** INDENT/DEDENT/NEWLINE do not
  exist in the text — they are **synthesized slots** (kind `layout`),
  the first language to use the architecture's slots-are-not-text
  principle. The layout pass is the classic indent-stack algorithm
  (CPython's tokenizer), run at layer 0; a dedent to a level not on
  the stack is `ERROR:DEDENT_MISMATCH`, an indented first line is
  `ERROR:UNEXPECTED_INDENT`.
* **One DEDENT per pop, one slot per DEDENT.** A line that closes two
  blocks gets two DEDENT slots. This deliberately routes around the
  bag-not-multiset limitation documented in imp (identical labels on
  one slot merge): layout events get their own slots, so EXIT markers
  never collide.
* **Cross-language machine reuse (the interlingua claim, first
  test).** The runner imports, from `imp_lang`, with zero changes:
  the **minus story machine**, the **entire expression-emitter
  layer**, and the **paren tracker**. Only the adapter differs:
  pysub's lexicon emits the same class labels (NUM, IDENT, ADDITIVE,
  LPAREN, ...) and its statements end at NEWLINE instead of `;`.
  Block structure arrives as INDENT/DEDENT slots instead of braces —
  and the shared machines do not care, because they never looked at
  braces, only at labels.
* **Binding marked after the name.** imp's `let x` announces a
  binding *before* the name; Python's `x =` announces it *after*. The
  per-identifier scope checkers can't look ahead, so a one-line reflex
  marks assignment targets first (`<IDENT> <ASSIGN>` → `TARGET` on the
  identifier), and the checkers key on `TARGET`. The adapter
  normalizes word order so the story-level machinery stays shared —
  the interlingua principle applied to a real word-order difference.

## Instruction set

imp's, minus `DECL` (assignment binds): `PUSH LOAD STORE NEG ADD SUB
MUL DIV GT LT EQ PRINT BRF ENTER EXIT`. Same rank table. BRF lands on
the `:`; ENTER on the INDENT slot; EXIT on each DEDENT slot. ENTER and
EXIT are pure control markers here — Python blocks do not scope, so
the VM keeps a single environment.

Scope semantics caveat (documented, test-pinned): the static checker
marks a name assigned at its *target token*, so `x = x + 1` with x
unbound is not flagged statically (Python raises NameError at
runtime; our VM also fails — runtime and Python agree, the static
label is a may-analysis approximation).

## Files

Standard set. Runner: `fsm_parser.pysub_lang` (mostly imports from
`imp_lang`). Tests: `src/tests/test_pysub_lang.py` — golden suite plus
a differential where the oracle is **real Python**: the generated
source is executed directly with `exec(src, {"print": out.append})`.
No transpilation; same text, two engines.

## Deliberate exclusions

`else`/`elif`/`while`/`def` (while/def need the address-resolving
projection pass), tabs (spaces only), comments, blank-line edge cases
inside blocks (blank lines are skipped), chained assignment
(`y = x = 3`), printing/storing comparison results in the
differential (Python prints `True`, our VM pushes 1; golden tests
cover the 1/0 semantics).

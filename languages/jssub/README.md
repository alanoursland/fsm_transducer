# Language definition: JavaScript subset ("jssub")

Sixth language. Statement syntax is deliberately imp's (`let`,
assignment, `print(expr);`, `if expr { ... }`, same expressions and
unary minus), because the point of this language is the one place
JavaScript is famously *not* like imp:

```js
let x = 10 / 2;      // '/' is division
let r = /ab+c/;      // '/' opens a regex literal
```

## What this language tests: context-sensitive tokenization

The extent of a token depends on parse context: after a completed
operand, `/` is an operator; in operand position, `/` opens a literal
that runs to the next `/`. A context-free lexer cannot decide this —
real JS engines thread parser state into the tokenizer. Here the
decision is the **same story state that resolved unary minus** (*did
an operand just complete?*), one level down the stack: minus needed
the story to classify a token, slash needs it to decide **where
tokens end**.

Pipeline (the new stage is #3):

1. **Naive tokenize**: every `/` is a SLASH token of ambiguous class;
   regex interiors come out as ordinary (wrong) tokens. The lexer also
   marks `OPERAND_END` on NUM/IDENT/RPAREN — the first explicit
   *story-event* label (the tier-1 adapter vocabulary from
   notes/story_machines.md, used by name).
2. **Slash story machine** (3 states: expect-operand, expect-operator,
   in-regex): SLASH in operand position → `REGEX_START`, then consume
   to the closing SLASH → `REGEX_END`; SLASH after an operand →
   `DIV_OP` + `MULTIPLICATIVE` (the classes imp's imported emitters
   key on). Deterministic — this is the JS lexer's actual algorithm,
   stated as a story machine.
3. **Retokenization**: merge each `REGEX_START..REGEX_END` span into
   one synthesized REGEX slot (text recovered exactly from source
   spans; `VAL:<pattern>`; provenance edges to the raw tokens it
   replaced). The wrongly-lexed interior tokens — including any
   parens, which would otherwise corrupt the bracket tracker — vanish
   into the merged slot.
4. Everything downstream **imports from imp unchanged**: bracket
   tracker, minus story, per-identifier scope checkers, expression
   emitters, statement emitters, and the VM. New downstream code is
   one single-token emitter (PUSH for REGEX slots) and regex values
   in operand resolution.

Regexes are inert first-class values (storable, printable); their
matching semantics are out of scope — the test target is the
tokenizer, not the regex engine.

## A leak worth advertising

imp's *minus* story machine hardcodes operand-done as NUM/IDENT/RPAREN
and cannot be told that a REGEX slot also completes an operand — so
`/a/ - 2` mislabels the minus as unary (caught at runtime: the VM run
goes invalid; test-pinned). The *slash* story machine, being new, keys
on the `OPERAND_END` event label instead and doesn't have this
problem. That asymmetry is the interlingua lesson made concrete:
shared story machines should consume **story-event labels emitted by
adapters**, not token classes. Migrating the minus story to
`OPERAND_END` is the recorded next refactor.

## Files

Standard set. Runner: `fsm_parser.jssub_lang`. Tests:
`src/tests/test_jssub_lang.py` — regex-tokenization goldens (the
classic nasties) plus a differential against **imp itself** on the
shared regex-free fragment: the same program through jssub's
naive-lex + slash-story + retokenize path and imp's direct lexer must
produce identical outputs.

## Deliberate exclusions

Regex flags (`/a/g`), escapes and character classes containing `/`,
regex operands inside arithmetic (inert values only), strings,
`function`/`while` (as imp), automatic semicolon insertion (statements
require `;`).

# Language definition: C++ subset ("cpp")

Seventh and final pre-planned language. The boss monster:

```cpp
vector<vector<int>> v;     // '>>' is TWO template closers
int x = 16 >> 2;           // '>>' is ONE right-shift operator
```

Scope: typed declarations (`int x = expr;`, template-typed
`vector<vector<int>> v;` with default initialization), assignment,
`print(expr);`, `if (expr) { ... }` (block-scoped, like imp),
expressions over `+ - * / << >> > < ==` with parens and unary minus.
Template nesting to **K_tpl = 3**; paren/brace depth is imp's K=5.

## What this language tests

* **Token splitting — the dual of jssub.** jssub's story machine
  merged many tokens into one (regex literals); cpp's must split one
  token into two. The naive lexer max-munches `>>` into a single
  ANGLE2 token; the angle story machine decides, by template-nesting
  depth, whether it is one shift operator or two closers; the
  retokenizer **splits** flagged tokens into two synthesized `>` slots
  (split source spans, provenance edges to the original). This is the
  C++11 standard's own rule (within template arguments, `>>` closes
  twice), stated as story machine + retokenization.
* **`<` needs symbol knowledge.** Less-than vs template-open is
  decided by whether the *preceding identifier names a template* —
  the lexer-hack problem (cousin of C's typedef ambiguity). The
  subset models the symbol table with lexicon-known template names
  (`vector`, `pair`) and one bit of story state ("last token was a
  template name"); real C++ populates that knowledge from
  declarations, which is exactly the per-identifier machinery imp
  already demonstrated — the honest gap and its closing move are both
  on the shelf. (Full C++ is sometimes *genuinely* ambiguous here,
  requiring the `template` keyword; that fact is recorded, not
  modeled.)
* **A precedence level that forced shared-machinery change.** C++
  puts shifts between additive and comparison (`a < b >> c` parses as
  `a < (b >> c)`, completing on the same slot), so shift could not be
  wedged into the existing rank table — the table was renumbered
  globally FIRST, as its own change with all languages' suites as the
  gate: 0 PUSH/LOAD/BRF/EXIT, 1 NEG/ENTER, 2 MUL/DIV, 3 ADD/SUB,
  **4 SHL/SHR**, 5 comparisons, 6 statements. imp's PERSPECTIVE
  predicted this error species; this is the prediction paying out as
  process instead of bug.
* **Comparison emitters could NOT be imported.** imp's cmp emitters
  take an additive chain as right operand; with shifts in the
  language, the right operand is a shift chain. Precedence tables are
  language-specific even when the chain machinery is shared — the
  first measured limit of cross-language reuse (helpers shared,
  emitters rebuilt).

## The angle story machine

States: (template depth 0..3) x (last-token-was-template-name bit).

| event | action |
|---|---|
| TEMPLATE name | set bit |
| `<` with bit | depth+1, emit TPL_OPEN |
| `<` without bit | emit LT_OP + CMP_OP (comparison) |
| `>` at depth>0 | depth-1, emit TPL_CLOSE |
| `>` at depth 0 | emit GT_OP + CMP_OP |
| `>>` at depth>=2 | depth-2, emit TPLSPLIT_CC (split: two closers) |
| `>>` at depth 1 | depth 0, emit TPLSPLIT_CG (split: closer + GT) |
| `>>` at depth 0 | emit SHR_OP + SHIFT (one shift token) |
| anything else | clear bit |

`vector<vector<vector<int>>>` works through maximal munch: the lexer
produces `>>` `>`, the story sees depth 3 -> CC split -> depth 1 ->
close -> 0.

## Files

Standard set. Runner: `fsm_parser.cpp_lang`. Tests:
`src/tests/test_cpp_lang.py` — goldens (both `>>` readings in one
program, deep nesting, tracker protection, unterminated template,
scope/shadowing) plus a 150-program differential against transpiled
Python (shifts are Python-native, so transpilation is line-local).

## Deliberate exclusions

User-defined templates / `template` declarations (the symbol table is
lexicon-fixed; populating it from declarations is imp's per-identifier
pattern, recorded as the extension), `<<` as stream insertion (only
shift), functions, `while`/`else`, references/pointers, the genuinely
ambiguous dependent-name cases (`a.template f<b>()` territory — noted
as where real C++ stops being resolvable by story state at all and
becomes the weighted two-stories problem this project still owes).

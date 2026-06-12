# Worked examples (hand-validated)

## A. The boss: `vector<vector<int>> v; print(1);`

Maximal munch lexes `>>` as one ANGLE2 token. The angle story walks:
`vector`(bit) `<`(depth 1) `vector`(bit) `<`(depth 2) `int` `>>`(depth
2 → TPLSPLIT_CC → depth 0). The retokenizer replaces the ANGLE2 slot
with two synthesized `>` slots (`angle:0`, `angle:1`), each TPL_CLOSE,
split source spans, provenance to the original token.

Program: `DECLD v; PUSH 1; PRINT` → `[1]`, env `{v: 0}`. ✓

## B. Shift stays one token: `int x = 16 >> 2; print(x);`

`>>` follows a NUM at template depth 0 → `SHR_OP` + `SHIFT`, one
token. Program: `PUSH 16; PUSH 2; SHR; DECL x; LOAD x; PRINT` → `[4]`. ✓

## C. Both readings in one program:
`pair<int, vector<int>> p; int x = 1 << 3; print(x >> 2);` → `[2]`. ✓

## D. `>` as comparison at depth 0:
`int a = 5; int b = 3; if (a > b) { print(a >> 1); }` → `[2]`. ✓

## E. Shift precedence (the reason for the global rank renumbering)

`print(1 + 2 >> 1);` → `(1+2)>>1` = `[1]` (shift below additive).
`print(7 >> 1 < 4);` → `(7>>1)<4` = `[1]` (comparison below shift —
SHR rank 4 precedes LT rank 5 where they meet). ✓

## F. Triple nesting through maximal munch:
`vector<vector<vector<int>>> w;`

`>>>` lexes as `>>` + `>`; the story: depth 3 → CC split → depth 1 →
single close → depth 0. No errors. ✓

## G. Unterminated template: `vector<int v;` →
`ERROR:UNTERMINATED_TEMPLATE`. ✓

## H. Block scope (imp semantics, C++ syntax):
`int x = 1; if (x > 0) { int x = 2; print(x); } print(x);` → `[2, 1]`;
`int x = 1; int x = 2;` → `ERROR:REDECLARE`; `print(q);` →
`ERROR:UNDECLARED`. ✓

# Worked examples (hand-validated)

Symbols render as bare strings in traces; identity labels omitted.

## A. Flat call: `(+ 1 2)`

| slot | text | shape/role labels | exec |
|---|---|---|---|
| token:0 | `(` | DEPTH:1, GROUP_START:1 | EXEC.0:NEW_LIST |
| token:1 | `+` | DEPTH:1, CTX:LIST:1, ROLE:HEAD:1 | EXEC.0:PUSH, EXEC.1:APPEND |
| token:2 | `1` | DEPTH:1, CTX:LIST:1, ROLE:ARG:1 | EXEC.0:PUSH, EXEC.1:APPEND |
| token:3 | `2` | DEPTH:1, CTX:LIST:1, ROLE:ARG:1 | EXEC.0:PUSH, EXEC.1:APPEND |
| token:4 | `)` | DEPTH:1, GROUP_END:1 | |

Program: `NEW_LIST; PUSH +; APPEND; PUSH 1; APPEND; PUSH 2; APPEND`
Trace: `[[]]` → `[[+]]` → `[[+,1]]` → `[[+,1,2]]`. Forms: `[(+ 1 2)]`. ✓
The parser builds the list; it does **not** add 1 and 2 — `+` is just
the symbol in head position. Evaluation is a downstream consumer.

## B. Nesting + roles on sublists: `(define (sq x) (* x x))`

tokens: 0:`(` 1:`define` 2:`(` 3:`sq` 4:`x` 5:`)` 6:`(` 7:`*` 8:`x` 9:`x` 10:`)` 11:`)`

Key labels:
* token:1 `define` — ROLE:HEAD:1
* token:2 `(` — ROLE:ARG:1 (the sublist-as-element's role, on its
  opening paren), GROUP_START:2
* token:3 `sq` — ROLE:HEAD:2; token:4 `x` — ROLE:ARG:2
* token:5 `)` — GROUP_END:2, ENCL:LIST:1 → EXEC.1:APPEND
* token:6 `(` — ROLE:ARG:1, GROUP_START:2; token:7 `*` — ROLE:HEAD:2
* token:10 `)` — GROUP_END:2, ENCL:LIST:1 → EXEC.1:APPEND

Program: `NEW_LIST; PUSH define; APPEND; NEW_LIST; PUSH sq; APPEND;
PUSH x; APPEND; APPEND; NEW_LIST; PUSH *; APPEND; PUSH x; APPEND;
PUSH x; APPEND; APPEND`
Result: `(define (sq x) (* x x))` as nested lists. ✓

## C. Multiple top-level forms: `(a) 42 (b c)`

Top-level atoms get PUSH but no APPEND (no CTX). Stack ends with three
entries: `[[a], 42, [b, c]]` — valid; the document is the sequence. ✓

## D. Empty list: `()`

`NEW_LIST` only. Forms: `[[]]`. No ROLE labels exist (head never
arrived); downstream consumers see an arity-0 list, not an error. ✓

## E. Graceful degradation: `(a (b`

`ERROR:UNBALANCED_OPEN` on the last token. Program:
`NEW_LIST; PUSH a; APPEND; NEW_LIST; PUSH b; APPEND`
Stack: `[[a], [b]]` — **two** fragments: the inner list was never
closed, so it was never appended into the outer one. Both fragments
are correctly built as far as the input went; the splice that never
happened is visible as the stack depth. ✓

## F. Stray close: `)`

`ERROR:UNBALANCED_CLOSE` on token:0; empty program; empty stack —
invalid by condition 1, diagnosed by the label. ✓

## G. Head-position sublist: `((f) x)`

token:1 `(` gets ROLE:HEAD:1 — a list in head position (Lisp's
"computed function" form) is labeled exactly like an atom head. The
role family doesn't care what kind of element fills the position;
that's what makes it a *positional* role. ✓

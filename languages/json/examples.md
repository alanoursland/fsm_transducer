# Worked examples (hand-validated)

Identity labels omitted. Stack traces use Python literals.

## A. Object with nested array: `{"a": 1, "b": [2, 3]}`

| slot | text | shape labels | exec |
|---|---|---|---|
| token:0 | `{` | DEPTH:1, GROUP_START:1 | EXEC.0:NEW_OBJ |
| token:1 | `"a"` | DEPTH:1, CTX:OBJ:1 | EXEC.0:PUSH(!{VAL}) |
| token:2 | `:` | DEPTH:1, CTX:OBJ:1 | |
| token:3 | `1` | DEPTH:1, CTX:OBJ:1 | EXEC.0:PUSH(!{VAL}), EXEC.1:SETK |
| token:4 | `,` | DEPTH:1, CTX:OBJ:1 | |
| token:5 | `"b"` | DEPTH:1, CTX:OBJ:1 | EXEC.0:PUSH(!{VAL}) |
| token:6 | `:` | DEPTH:1, CTX:OBJ:1 | |
| token:7 | `[` | DEPTH:2, GROUP_START:2 | EXEC.0:NEW_ARR |
| token:8 | `2` | DEPTH:2, CTX:ARR:2 | EXEC.0:PUSH(!{VAL}), EXEC.1:APPEND |
| token:9 | `,` | DEPTH:2, CTX:ARR:2 | |
| token:10 | `3` | DEPTH:2, CTX:ARR:2 | EXEC.0:PUSH(!{VAL}), EXEC.1:APPEND |
| token:11 | `]` | DEPTH:2, GROUP_END:2, ENCL:OBJ:1 | EXEC.1:SETK |
| token:12 | `}` | DEPTH:1, GROUP_END:1 | |

Program: `NEW_OBJ; PUSH "a"; PUSH 1; SETK; PUSH "b"; NEW_ARR; PUSH 2;
APPEND; PUSH 3; APPEND; SETK`

Trace: `[{}]` `[{},"a"]` `[{},"a",1]` →SETK→ `[{"a":1}]` `[...,"b"]`
`[...,"b",[]]` `[...,2]` →APPEND→ `[...,"b",[2]]` `[...,3]` →APPEND→
`[...,"b",[2,3]]` →SETK→ `[{"a":1,"b":[2,3]}]`. ✓ equals `json.loads`.

Note token:11: the closing `]` carries the *array's* inner depth
(GROUP_END:2) and the *object's* context (ENCL:OBJ:1) — that single
ENCL label is what turns the finished array into a value of `"b"`.

## B. Array of literals: `[true, null, "x"]`

`[`→NEW_ARR; each element gets PUSH + APPEND (CTX:ARR:1); `]` at top
level emits nothing.

Program: `NEW_ARR; PUSH true; APPEND; PUSH null; APPEND; PUSH "x";
APPEND` → `[true, null, "x"]`. ✓

## C. Nested objects: `{"a": {"b": 2}}`

tokens: 0:`{` 1:`"a"` 2:`:` 3:`{` 4:`"b"` 5:`:` 6:`2` 7:`}` 8:`}`

token:3 `{` — DEPTH:2, GROUP_START:2 → NEW_OBJ.
token:6 `2` — CTX:OBJ:2 → PUSH, SETK (inner).
token:7 `}` — DEPTH:2, GROUP_END:2, ENCL:OBJ:1 → SETK (outer).
token:8 `}` — top level, no ENCL → nothing.

Program: `NEW_OBJ; PUSH "a"; NEW_OBJ; PUSH "b"; PUSH 2; SETK; SETK`
Trace: `[{}]` `[{},"a"]` `[{},"a",{}]` `[...,"b"]` `[...,"b",2]` →SETK→
`[{},"a",{"b":2}]` →SETK→ `[{"a":{"b":2}}]`. ✓

## D. Top-level scalar: `42`

Program: `PUSH 42` → `42`. A document need not be a container. ✓

## E. Graceful degradation: `{"a": 1` (unclosed)

Shape tracker ends in state `(O)` → `ERROR:UNBALANCED_OPEN` on the last
token. Everything well-formed still fires: program
`NEW_OBJ; PUSH "a"; PUSH 1; SETK` leaves `[{"a": 1}]` — the fragment is
a *correctly built* partial document; the error label (validity
condition 4) is what disqualifies it, not a malformed stack.

## F. Mismatched brackets: `[1}`

token:2 `}` closes an array context: pop anyway (error recovery), emit
`GROUP_END:1` plus `ERROR:MISMATCHED_CLOSE`. Program:
`NEW_ARR; PUSH 1; APPEND` → stack `[[1]]`, error label present. ✓

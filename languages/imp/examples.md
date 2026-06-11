# Worked examples (hand-validated)

## A. The canonical program: `let x = 3; if x > 1 { print(x); }`

tokens: 0:`let` 1:`x` 2:`=` 3:`3` 4:`;` 5:`if` 6:`x` 7:`>` 8:`1`
9:`{` 10:`print` 11:`(` 12:`x` 13:`)` 14:`;` 15:`}`

| slot | text | key labels | exec |
|---|---|---|---|
| token:1 | x | IDENT, VAL:x, DEPTH:0 (decl site) | |
| token:3 | 3 | NUM, DEPTH:0 | EXEC.0:PUSH(!{VAL}) |
| token:4 | ; | | EXEC.4:DECL(!{VAL@token:1}) |
| token:6 | x | DEPTH:0, use, declared ✓ | EXEC.0:LOAD(!{VAL}) |
| token:8 | 1 | DEPTH:0 | EXEC.0:PUSH, EXEC.3:GT |
| token:9 | { | DEPTH:1, GROUP_START:1 | EXEC.0:BRF, EXEC.1:ENTER |
| token:12 | x | DEPTH:2 (inside print's parens) | EXEC.0:LOAD |
| token:14 | ; | | EXEC.4:PRINT |
| token:15 | } | DEPTH:1, GROUP_END:1 | EXEC.0:EXIT |

Program: `PUSH 3; DECL x; LOAD x; PUSH 1; GT; BRF; ENTER; LOAD x;
PRINT; EXIT`

Trace: x:=3 · 3>1→1 · BRF(true)→continue · ENTER · print 3 · EXIT.
Output: `[3]`, env `{x: 3}`, stack empty. ✓
With `let x = 1;` instead: GT yields 0, BRF skips to past EXIT,
output `[]`. ✓

## B. Precedence and parens: `let y = (1 + 2) * 3; print(y + 1);`

`(1+2)*3`: ADD fires at `2` (depth 1), MUL at `3` (pair emitter, rhs =
paren group). Program prefix: `PUSH 1; PUSH 2; ADD; PUSH 3; MUL;
DECL y` → y = 9. Then `LOAD y; PUSH 1; ADD; PRINT` → output `[10]`. ✓

## C. Shadowing (golden only; the Python oracle has no block scope):

```text
let x = 1; if x > 0 { let x = 2; print(x); } print(x);
```

Inner `let` DECLs into the block scope pushed by ENTER; inner LOAD
finds the inner binding; EXIT drops it; the final LOAD finds the
global. Output: `[2, 1]`, final env `{x: 1}`. ✓

## D. Scope error: `print(y); let y = 1;`

The scope checker for `y` sees the use before the declaration:
`ERROR:UNDECLARED` on token:2 (`y`). The program still projects
(`LOAD y; PRINT; PUSH 1; DECL y`) and the VM run fails on the LOAD —
static label and runtime check agree, as validity condition 3 demands. ✓

## E. Redeclaration: `let x = 1; let x = 2;`

Second `let x` finds the global bit already set:
`ERROR:REDECLARE` on token:6. (Shadowing in an inner block is NOT a
redeclaration — different bit. C above carries no error.) ✓

## F. Mismatched brackets: `if x > 1 ( print(x); }`

The tracker pops a P-frame on `}`: `ERROR:MISMATCHED_CLOSE`. ✓

## G. Assignment vs declaration: `let x = 1; x = x + 2; print(x);`

token:5 `x` is an assignment target (guard: previous token `;` is not
LET, next is `=`) → STORE at token:9 `;`, naming token:5. The `x` at
token:7 is expression position → LOAD. Output: `[3]`. ✓

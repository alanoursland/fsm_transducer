# Worked examples (hand-validated)

Identity labels (`TEXT:`, `TOKEN`) omitted. `EXEC.r` = rank-r instruction.
Validation: execute the projected program on a stack VM by hand and
compare with ordinary evaluation.

## 1. Precedence: `3 + 4 * 2`

| slot | text | layer 0 | layer 1 | layer 3 (terms) | layer 4 (exec) |
|---|---|---|---|---|---|
| token:0 | 3 | NUM, VAL:3 | DEPTH:0 | TERM_START:0, TERM_END:0 | EXEC.0:PUSH(!{VAL}) |
| token:1 | + | OP:ADD, ADDITIVE | DEPTH:0 | | |
| token:2 | 4 | NUM, VAL:4 | DEPTH:0 | TERM_START:0 | EXEC.0:PUSH(!{VAL}) |
| token:3 | * | OP:MUL, MULTIPLICATIVE | DEPTH:0 | | |
| token:4 | 2 | NUM, VAL:2 | DEPTH:0 | TERM_END:0 | EXEC.0:PUSH(!{VAL}), EXEC.1:MUL, EXEC.2:ADD |

Projected program: `PUSH 3; PUSH 4; PUSH 2; MUL; ADD`
Stack trace: [3] [3,4] [3,4,2] [3,8] [11]. Expected 3+4·2 = **11**. ✓
(Both MUL and ADD complete at token:4; rank ordering 1 < 2 resolves them.)

## 2. Parentheses: `( 1 + 2 ) * 5`

| slot | text | layer 0 | layer 1 | layer 3 | layer 4 |
|---|---|---|---|---|---|
| token:0 | ( | LPAREN | DEPTH:1, GROUP_START:1 | TERM_START:0 | |
| token:1 | 1 | NUM, VAL:1 | DEPTH:1 | TERM_START:1, TERM_END:1 | EXEC.0:PUSH(!{VAL}) |
| token:2 | + | OP:ADD | DEPTH:1 | | |
| token:3 | 2 | NUM, VAL:2 | DEPTH:1 | TERM_START:1, TERM_END:1 | EXEC.0:PUSH(!{VAL}), EXEC.2:ADD |
| token:4 | ) | RPAREN | DEPTH:1, GROUP_END:1 | | |
| token:5 | * | OP:MUL | DEPTH:0 | | |
| token:6 | 5 | NUM, VAL:5 | DEPTH:0 | TERM_END:0 | EXEC.0:PUSH(!{VAL}), EXEC.1:MUL |

The depth-0 term spans token:0..token:6 (group-as-operand, then `* 5`).
The inner ADD completes at token:3 (last token of its right operand at
depth 1); the MUL completes at token:6.

Program: `PUSH 1; PUSH 2; ADD; PUSH 5; MUL`
Trace: [1] [1,2] [3] [3,5] [15]. Expected (1+2)·5 = **15**. ✓

## 3. Left associativity: `8 - 2 - 1`

All tokens DEPTH:0; terms are the single numbers. Each SUB completes at
the last token of its immediate right term:

| slot | text | layer 4 |
|---|---|---|
| token:0 | 8 | EXEC.0:PUSH |
| token:2 | 2 | EXEC.0:PUSH, EXEC.2:SUB |
| token:4 | 1 | EXEC.0:PUSH, EXEC.2:SUB |

Program: `PUSH 8; PUSH 2; SUB; PUSH 1; SUB`
Trace: [8] [8,2] [6] [6,1] [5]. Expected (8−2)−1 = **5**, not 8−(2−1)=7. ✓

## 4. Same slot, different depths: `1 + ( 2 + 3 )`

| slot | text | layer 1 | layer 4 |
|---|---|---|---|
| token:0 | 1 | DEPTH:0 | EXEC.0:PUSH |
| token:1 | + | DEPTH:0 | |
| token:2 | ( | DEPTH:1, GROUP_START:1 | |
| token:3 | 2 | DEPTH:1 | EXEC.0:PUSH |
| token:4 | + | DEPTH:1 | |
| token:5 | 3 | DEPTH:1 | EXEC.0:PUSH, EXEC.2:ADD   (depth 1) |
| token:6 | ) | DEPTH:1, GROUP_END:1 | EXEC.2:ADD   (depth 0) |

The inner ADD completes at token:5; the outer ADD's right operand is the
whole group, whose last token is the `)` — so the outer ADD lands on
token:6. Token order alone sequences them correctly.

Program: `PUSH 1; PUSH 2; PUSH 3; ADD; ADD`
Trace: [1] [1,2] [1,2,3] [1,5] [6]. Expected 1+(2+3) = **6**. ✓

## 5. Graceful degradation: `2 * ( 3 + 4` (unclosed paren)

The depth tracker ends in state d1, so `ERROR:UNBALANCED_OPEN` is
emitted on the final token. Inside the group everything is well-formed,
so depth-1 labeling proceeds: PUSHes fire, the inner ADD fires at
token:5. The depth-0 MUL's right operand pattern requires
`GROUP_END:1`, which never arrives — the MUL instruction is never
emitted.

Program (best-effort): `PUSH 2; PUSH 3; PUSH 4; ADD`
Trace: [2] [2,3] [2,3,4] [2,7] — stack ends with **two** values, which
is itself a detectable signal of incompleteness (validity condition 1
fails, consistent with the ERROR label). No crash, no garbage
arithmetic: the well-formed fragment was compiled correctly. ✓

# Worked examples (hand-validated)

## A. The two slashes: `let r = /ab+/; let x = 10 / 2; print(x); print(r);`

The first `/` follows `=` (operand position) → `REGEX_START`; its
closer → `REGEX_END`; the span `/ ab + /` merges to one REGEX slot,
pattern `ab+`. The `/` in `10 / 2` follows a NUM (`OPERAND_END`) →
`DIV_OP` + `MULTIPLICATIVE`, and imp's imported division emitter
handles it.

Program: `PUSH /ab+/; DECL r; PUSH 10; PUSH 2; DIV; DECL x; LOAD x;
PRINT; LOAD r; PRINT` → outputs `[5.0, /ab+/]`. ✓

## B. Chained division (the boundary case lexers get wrong):
`let a = 2; let b = (a + 6) / a / 2; print(b);`

Both slashes follow operand-completers (`)` and IDENT) → both
division. (2+6)/2/2 → output `[2.0]`. ✓

## C. Parens inside a regex don't corrupt the tracker:
`let r = /((a+)b)*/; print(1);`

Naively lexed, the regex interior contains three unbalanced-looking
parens — but they merge into the REGEX slot before the bracket
tracker runs, so the tracker sees balanced code and emits no errors.
Output `[1]`. ✓ (This ordering — story machine, then retokenize, THEN
structure tracking — is the whole point of the language.)

## D. Regex in expression-operand position after an operator:
`let x = 4; print(x * 2 / 2);` vs `print(/x*2/);`

In the first, `/` follows `2` → division → `[4.0]`. In the second,
`/` follows `(` → regex literal with pattern `x*2` → `[/x*2/]`. Same
character sequence `x * 2 /` inside, opposite tokenizations, decided
entirely by one bit of story state at the opening slash. ✓

## E. Unterminated regex: `let r = /ab; print(1);`

The story machine enters in_regex and never finds a closer:
`ERROR:UNTERMINATED_REGEX`. No merge happens; downstream output is
best-effort. ✓

## F. The documented minus-story leak (pinned): `let x = /a/ - 2;`

imp's imported minus story doesn't know REGEX completes an operand,
so the `-` is mislabeled unary; the program leaves a stranded value
and the run is invalid — detectable, documented, and the motivation
for migrating minus_story to the OPERAND_END event label. ✓

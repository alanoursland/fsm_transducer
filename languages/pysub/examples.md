# Worked examples (hand-validated)

Layout slots shown as `«NEWLINE»`, `«INDENT»`, `«DEDENT»`.

## A. The canonical program

```python
x = 3
if x > 1:
    print(x)
```

Slot stream: `x = 3 «NEWLINE» if x > 1 : «NEWLINE» «INDENT» print ( x )
«NEWLINE» «DEDENT»`

| slot | key labels | exec |
|---|---|---|
| token:0 `x` | IDENT, TARGET | |
| token:2 `3` | NUM | EXEC.0:PUSH |
| layout NEWLINE₁ | | EXEC.5:STORE(!{VAL@token:0}) |
| token:4 `x` | use, assigned ✓ | EXEC.0:LOAD |
| token:6 `1` | | EXEC.0:PUSH, EXEC.4:GT |
| token:7 `:` | | EXEC.0:BRF |
| layout INDENT | | EXEC.1:ENTER |
| token:10 `x` | DEPTH:1 (inside print parens) | EXEC.0:LOAD |
| layout NEWLINE₃ | | EXEC.5:PRINT |
| layout DEDENT | | EXEC.0:EXIT |

Program: `PUSH 3; STORE x; LOAD x; PUSH 1; GT; BRF; ENTER; LOAD x;
PRINT; EXIT` — **identical in shape to imp's canonical program** for
`let x = 3; if x > 1 { print(x); }`. Same story, different layout
syntax; only the slots carrying the markers changed (`;`→NEWLINE,
`{`→`:`+INDENT, `}`→DEDENT). Output `[3]`. ✓

## B. Multi-level dedent

```python
x = 5
if x > 1:
    if x > 3:
        print(x)
    print(0)
print(1)
```

The line `print(0)` closes one block (one DEDENT slot before it);
`print(1)` closes another. Each DEDENT is its own slot carrying one
EXIT — never two EXITs on one slot, so the bag-not-multiset
limitation cannot bite. Output `[5, 0, 1]`; with `x = 2` instead:
`[0, 1]`; with `x = 0`: `[1]`. ✓

## C. Use before assignment

```python
print(y)
y = 1
```

`ERROR:UNDECLARED` on the `y` inside print (no TARGET-marked
occurrence precedes it). Runtime LOAD fails; real Python raises
NameError. All three agree. ✓

## D. Dedent to a level not on the stack

```python
if x > 1:
        print(x)
    print(0)
```

(8 spaces, then 4 — but 4 was never pushed.) `ERROR:DEDENT_MISMATCH`
on the line's first token; layout recovers by popping to the nearest
level and continues labeling. ✓

## E. Unary minus, shared story machine

```python
x = 5
print(x - 3)
print(-3)
```

The minus story machine is **imported from imp** — same FSM object,
zero changes. First `-` → MINUS:BINARY, second → MINUS:UNARY; output
`[2, -3]`. The interlingua claim's first running instance. ✓

## F. May-analysis gap (pinned)

```python
x = x + 1
```

No static error (the TARGET-marked `x` precedes the use in token
order), but the VM fails on LOAD and real Python raises NameError —
the two runtimes agree; the static label is documented as
approximate. ✓

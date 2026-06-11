# Language definition: JSON

The second language in the declarative-definition format established by
`languages/arithmetic/` (read that folder's README first; conventions —
parameterized families, machine schemas, anchored machines, operand
references, the field+program output contract — carry over unchanged).

Scope: objects, arrays, strings (no escape sequences), integers and
simple decimals, `true` / `false` / `null`, nesting to **K = 3**.
Commas and colons are consumed as separators but not *enforced* —
accretion tolerance means `[1 2]` builds the same document as `[1, 2]`
without an error label. See "Deliberate exclusions".

## What JSON stresses that arithmetic didn't

* **A shape tracker, not a depth tracker.** Two bracket types means the
  anchored global machine's states are *stacks of container types*
  (`()`, `(O)`, `(O,A)`, ...), not depth counts: 2^0+2^1+2^2+2^3 = 15
  states for K = 3, plus overflow. Bracket-type mismatch (`[1}`)
  becomes a detectable, located error (`ERROR:MISMATCHED_CLOSE`).
* **Context labels.** Every token gets `CTX:OBJ:d` or `CTX:ARR:d` (its
  innermost container), and every *closing bracket* gets
  `ENCL:OBJ:d` / `ENCL:ARR:d` (the container *around* the one it
  closes) — that one label is what lets a closed container complete as
  a value in its parent without any lookahead.
* **A document, not a number.** The stack VM builds a JSON value; the
  differential oracle is `json.loads` equality, not arithmetic.

## The instruction set has no END instructions

`instructions.yaml` defines five ops: `PUSH`, `NEW_OBJ`, `NEW_ARR`,
`APPEND`, `SETK`. Completion ops fire at value ends (a scalar token, or
the closing bracket of a nested container), in the parent's context:
`APPEND` (pop value, append to the array on top) in arrays, `SETK` (pop
value, pop key, store) in objects. Keys are just `PUSH`ed strings; the
pending key lives *on the VM stack* under its value, so no per-object
key register is needed. Closing brackets emit nothing for themselves —
a container is complete the moment its last element completed.

## Files

| file | contents |
|---|---|
| `lexicon.yaml` | token classes |
| `layers.yaml` | shape tracker + per-depth emitter schemas |
| `instructions.yaml` | builder instruction set, VM semantics |
| `examples.md` | hand-validated worked examples |
| `RUNNING.md` | runner usage and output interpretation |

Runner: `fsm_parser.json_lang`. Golden tests:
`src/tests/test_json_lang.py`.

## Deliberate exclusions

* string escapes (`\"`, `\n`, `\uXXXX`) and scientific notation —
  lexical detail, nothing architectural; add when the char-level
  layer 0 lands;
* separator enforcement — missing/extra commas and colons produce no
  error label in v1; the shape tracker only polices brackets. A
  well-formedness schema (like arithmetic's `expr_shape`) is the
  obvious v2 addition;
* duplicate keys — last write wins, as in most parsers;
* 8-bit parameterized labels — same rationale as arithmetic.

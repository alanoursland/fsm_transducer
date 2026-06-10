# Language definition: arithmetic

A declarative specification of an arithmetic parser in the accretion
architecture. Nothing in this folder is executable — it defines the
language, the label families each layer develops, and the instruction
stream the final projection reads off. Validation is by the hand-worked
examples in `examples.md`.

Scope: integers, `+ - * /`, parentheses to a declared maximum nesting
depth **K = 3**. Standard precedence (`* /` over `+ -`), left
associativity.

## The claim being specified

The parser **generates instructions for** a stack machine; it does not
implement one. The input is a token sequence; the output is the same
token sequence, where each token carries (among its other labels) zero
or more `EXEC` labels. Concatenating the `EXEC` labels in token order
(and, within a token, in rank order) yields a correct RPN program for
the expression.

Bounded depth is what makes this a regular transduction: the
shunting-yard stack over K nesting levels has finitely many
configurations, and the architecture factors that product space into
one small machine instance per depth (see `layers.yaml`), stacked as
layers. The stack of FSM blocks plays the role of the pushdown stack,
unrolled. Inputs nested deeper than K are not crashes; they produce
`ERROR:DEPTH_EXCEEDED` labels and a best-effort prefix program.

## Files

| file | contents |
|---|---|
| `lexicon.yaml` | token classes (layer 0 labels) |
| `layers.yaml` | the machine specs, layer by layer, including per-depth schema instances |
| `instructions.yaml` | the target instruction set and operand-reference syntax |
| `examples.md` | hand-validated worked examples: full label field and emitted program |

## Conventions used throughout

* **Parameterized label families.** Labels like `DEPTH:2` are members of
  a family (`DEPTH`) with an integer parameter. The current
  implementation encodes parameters in the label string; this spec
  treats the family as the unit of meaning. Families used here:
  `DEPTH:d` (0..K), `GROUP_START:d` / `GROUP_END:d` (1..K), `TERM_START:d` /
  `TERM_END:d`, `EXEC.r:OP` (rank r), `VAL:n`, `ERROR:kind`.
* **Machine schemas.** A spec marked `forall d in 1..K` (or `0..K`)
  defines one small machine per depth value. Instances are independent;
  they communicate only through the label bag. This is the declarative
  form of "multiple small independent FSMs on the same level".
* **Anchored machines.** Machines marked `anchored: true` run exactly
  once from token 0 (they are global transducers, e.g. depth tracking).
  Unanchored machines are pattern matchers that may begin at any token.
* **Label references in operands.** `!{FAMILY}` in an instruction
  operand means "the parameter of this slot's strongest FAMILY label,
  resolved when the instruction is read off". Instructions stay
  symbolic; binding is explicit. See `instructions.yaml`.
* **Determinism note.** Every machine in this language is deterministic
  on well-formed input, so the engine's eager-emission semantics
  produce no spurious labels except where the spec says so (errors).
* **Output contract.** Instruction operands are references into the
  label field, so the parser's output is *field + program*, not a
  self-contained stream. Resolution policy in `instructions.yaml`.

## Deliberate exclusions

Two ideas from `notes/labels_as_universal_representation.md` are
intentionally **not** used here, to keep the first validated language
small:

* fixed-width (8-bit) label parameters with carry-chained families —
  K = 3 with explicit depth states is the right size for hand
  validation; and
* char-level tokenization-as-parsing — sketched as a future layer 0 at
  the bottom of `lexicon.yaml`, but this language assumes pre-tokenized
  input.

# LLM Perspective: how the tiny imperative language was designed

Fourth in the series; epistemic ground rules in
`languages/arithmetic/PERSPECTIVE.md`.

## The scope problem, and the moment the design hinged

Everything else in this language is recombination of validated
precedent: expressions are arithmetic's machinery plus one precedence
level; the bracket tracker is JSON's with kinds {P, B}; statement
patterns are guard-token constructions. The design hinge was scope.

Declared-before-use over unbounded identifier names is not a regular
property — a finite tracker cannot remember an unbounded set of names.
The first design impulse (recorded honestly) was to bound the variable
namespace, the same move that bounds nesting depth. That would have
worked and would have been ugly: depth is a structural resource a
language can reasonably budget; "your program may use at most N
variable names, fixed at design time" is not a budget, it is a wall.

The move that resolved it: the property is regular *per name*. Track
"is x declared, and at which block levels" for one fixed x, and the
machine is tiny — a stack of bits plus an expect-a-declaration flag.
Instantiate that machine once per identifier *actually occurring in
the input*, and the unbounded namespace costs nothing until used. This
is the third factoring of the same kind in the project:

| language | non-regular whole | regular factor |
|---|---|---|
| arithmetic | unbounded nesting | per-depth machines |
| imp | unbounded namespace | per-identifier machines |
| (predicted) NL | unbounded lexicon | per-lexeme machines |

The pattern now has a name in the specs — input-indexed schema
instantiation — and the prediction in the third row is the reason to
believe it matters: a natural-language grammar cannot enumerate its
lexicon at design time either, and "machines instantiated per word
occurring in the sentence" is precisely how lexicalized grammar
formalisms (LTAG, CCG categories per word) are organized. The training
data contains that parallel; whether it was operative in producing the
design or only available for this retrospective is exactly the kind of
question this document cannot answer about its own author.

## Cross-slot operands: a mechanism finally earns its keep

`let x = 3;` must run DECL after the expression (at `;`) while naming
the `x` token. The mechanisms this needed — slot-id captures, template
interpolation into emission labels, the `!{FAMILY@id}` operand form —
were all built sessions ago and used zero times since. The honest
observation: they were built on spec-plausibility ("labels should
support interpolation") rather than demand, and it was luck rather
than foresight that they composed into exactly what statements needed.
The lesson cuts both ways: speculative generality usually rots, but
mechanisms that mirror a sound theory (tagged NFAs, register
automata) tend to find their use case eventually because the theory
already proved they were the right shape.

## Structured control flow: designing around a real limitation

`if` wants "jump to after the block," and emissions cannot point
forward — an honest architectural limitation, not a style choice. The
options considered: (a) a second projection pass resolving markers to
addresses (deferred, required for `while`); (b) BRF as a structured
skip over matched ENTER/EXIT markers (chosen); (c) placing the jump
target via the bracket tracker's knowledge at the closing brace
(rejected: the *condition* is popped at the opening brace; the
decision point is fixed). Choosing (b) means the VM does a forward
scan on a false condition — O(block length) instead of O(1) — which is
the cost of keeping the projection a pure sort. For a language with
`while`, option (a) becomes mandatory; that boundary is now documented
rather than discovered.

## Two checkers for one rule, on purpose

The scope rule is implemented twice: statically (per-identifier
machines emitting ERROR labels) and dynamically (the VM failing on
unbound LOAD/STORE). The redundancy is deliberate and the golden tests
assert their *agreement*. This came from the project's own validity
discipline rather than from compiler tradition — though it lands on
the same place compiler engineering did (verifiers check what
compilers assume). When the two disagree someday, one of them is
wrong, and the disagreement will be a located, diagnosable artifact.

## What went wrong

One class of error, twice, at the same place: the depth budget. K=3
was inherited from three languages whose nesting was the *subject* of
the bound; imp composes nesting from two different constructs (blocks
and expression parens share the budget), and the generated programs
exceeded K=3, then K=4, before settling at K=5 (three block levels +
`print((x))` = 5). Both failures were caught by the differential
generator within seconds, not by the designer — and not by the golden
examples either, which were all written comfortably inside the budget.

Ledger update: still no conceptual errors, but this one is a new
species — neither positional nor quantificational, but a *resource
estimate* defaulted from precedent instead of derived from the
language's own composition. Precedent inheritance, which JSON's
PERSPECTIVE praised for collapsing the design space, here carried a
stale constant across a boundary where it no longer held. The fix for
next time is mechanical: derive K from the worst case the generator
can emit, before running it.

## The skeptic's ledger

Still no ambiguity — imp is deterministic and LL(1)-ish like
everything before it. What imp did add: the first language where the
*input* determines part of the machine inventory, the first
dual-implementation validity condition, and the first time an honest
architectural limitation (no forward references) visibly shaped a
design rather than being worked around invisibly. The weighted
machinery remains idle at four languages. The unary-vs-binary minus
exclusion in this very language is the cheapest possible entry point
for ambiguity — `x - 3` versus `print(-3)` — and was excluded *because*
it deserves the weighted treatment rather than a lexer hack. That is
either discipline or procrastination; the next language decides which.

## Addendum (v1.1): unary minus as a story machine

The exclusion this document called "either discipline or
procrastination" resolved as neither: the author's story-machine
framing (notes/story_machines.md) dissolved the problem before the
weighted machinery was needed. One bit of narrative state — *did an
operand just complete?* — classifies every `-` deterministically. The
implementation is a 2-state anchored machine emitting MINUS:UNARY /
MINUS:BINARY; the binary SUB emitter gates on MINUS:BINARY, operands
admit leading MINUS:UNARY tokens, and a NEG emitter fires at the
operand's end.

Two findings worth the ledger:

1. **A real architectural limitation surfaced: the label field is a
   bag, not a multiset.** `- -3` emits two identical EXEC.1:NEG labels
   on one slot; they merge, one NEG survives, and `- -3` evaluates to
   -3. `-(-3)` is fine (different slots). The behavior is documented
   and pinned by a test rather than patched, because the right fix is
   a design decision (sequence-numbered EXEC labels? multiset bags?)
   that deserves more than a workaround. This is the first limitation
   discovered that is about the *representation* rather than about
   regularity.
2. **The rank table needed a derivation, not an inheritance.** NEG
   binds tighter than MUL, and `2 * -3` lands both on one slot — so
   NEG forced a global rank renumbering (everything from MUL up
   shifted by one). Same error species as the K-budget: a constant
   table carried by precedent until a new construct broke it. The
   pattern ledger now reads: positional errors, then resource-budget
   errors, now ordering-budget errors — all of them constants that
   precedent froze and composition thawed.

The story machine itself is the smallest anchored machine in the
project (2 states), and it resolves what looked like the entry point
for weighted ambiguity. The control condition now exists; the
two-stories experiment remains open, and the next step recorded in
notes/story_machines.md (the same story machine shared between imp and
sexpr via syntax adapters) is unblocked.

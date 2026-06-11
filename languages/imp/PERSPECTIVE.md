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

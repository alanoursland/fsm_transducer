# LLM Perspective: how the Python subset was designed

Fifth in the series; ground rules in
`languages/arithmetic/PERSPECTIVE.md`.

## This language was designed backwards

The previous four started from "what does this language need?" Pysub
started from "what can it inherit?" — because the author's interlingua
claim (notes/story_machines.md addendum) was on the table, and pysub
was the chance to test it cheaply. The design question became: what is
the *smallest adapter* that lets imp's machines run on indentation
syntax? The answer turned out to be: a layout-synthesizing tokenizer,
a two-token target-marking reflex, and NEWLINE-terminated statement
patterns. Everything else — paren tracker, minus story machine, the
entire expression-emitter layer — imports from imp unchanged, and the
canonical programs of the two languages compile to the same
instruction sequence (asserted by a test, not just claimed).

That result should be read carefully rather than triumphantly: imp and
pysub were *designed by the same process under the same conventions*,
so shared machinery was likely. The honest statement is that the
interlingua claim survived its first, easiest test. A language designed
by someone else, or a language with genuinely different semantics,
would be a real test.

## Synthesized slots: the representation finally stretched

INDENT and DEDENT do not exist in the text. Every previous language
had slots in 1:1 correspondence with source spans; pysub is the first
to use the architecture's actual slot model (slots are
representational units, text optional). Two design points:

* **One slot per DEDENT pop.** A line closing two blocks gets two
  DEDENT slots. This was a *deliberate* application of the lesson from
  imp's bag-not-multiset limitation: two EXIT markers on one slot
  would have merged. Where imp discovered the limitation, pysub
  routed around it by representation — the first time a documented
  limitation changed a subsequent design rather than just sitting in
  a ledger.
* **Layout is code, not an FSM,** and the spec says so plainly. The
  indent-stack algorithm adds slots, which emitters cannot do (they
  emit labels). It is a story machine in code form — its state is the
  indent stack, its narration is the layout slots. When the
  shape-changing block machinery matures, this is the obvious first
  candidate to migrate.

## Word order and the adapter layer

imp announces a binding before the name (`let x`); Python announces it
after (`x =`). The per-identifier checkers cannot look ahead, so a
two-token reflex marks TARGET on assignment targets first, and the
checkers key on the label. This is small but conceptually load-bearing:
it is the adapter normalizing a *word-order* difference so the
story-level machinery stays shared — precisely the role syntax
adapters play in the three-tier factoring, demonstrated on the
simplest possible case. Natural language will need the same move at
every turn (head-initial vs head-final, etc.).

## What went wrong

One generator bug, caught by the differential within seconds: names
first bound inside an if-block were treated as available afterwards,
but conditional execution means conditionally bound — real Python
raised NameError on a generated program. Notably this exact logic
existed correctly in imp's generator (for block *scope* reasons) and
was dropped in translation because pysub "has no block scope" — true,
but the *reason* changed (scope -> conditional execution) while the
*rule* (don't use block-introduced names afterwards) should have
survived. Ledger species: rationale-coupling — a rule was deleted
because its stated reason no longer applied, though a different reason
still did. New species again; still zero conceptual errors in the
machines themselves.

## The skeptic's ledger

The weighted machinery is now idle at five languages, and this
PERSPECTIVE will not pretend otherwise: pysub is deterministic,
LL(1)-ish, and chosen from the author's long-standing plan rather than
from the ambiguity roadmap. What it contributed instead: the first
cross-language machine reuse (interlingua tier-2 and tier-3, soft
test passed), the first synthesized slots, the first
limitation-driven design decision, and the cleanest oracle yet (the
same source text run by real Python). The formal-language series now
covers expressions, data, symbols, statements, and layout. The two
remaining experiments are unchanged and both now have all their
prerequisites: competing stories (weights, finally), and the
regex_transformer probe. Nothing on the formal side blocks either.

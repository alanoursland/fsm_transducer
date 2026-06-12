# LLM Perspective: how the C++ subset was designed

Seventh and last of the pre-planned series; ground rules in
`languages/arithmetic/PERSPECTIVE.md`.

## The boss monster decomposed into known parts

The author named this the boss, and the honest finding is that it
decomposed completely: `>>` splitting is jssub's retokenization run in
reverse (split instead of merge — the dual was implemented in an
afternoon because merge had already forced the hard design); the `<`
decision is one bit of who-just-went-by story state; template depth is
the same bounded counter as every tracker since arithmetic. The
celebrated hardness of C++ parsing, at this subset's scale, is three
shelf parts composed in the right order. What did NOT decompose is
recorded below, and matters more.

## Where the subset is honest about cheating

Real C++ decides template-ness from declarations (and sometimes cannot
decide at all — dependent names need the `template` keyword because
the grammar is genuinely ambiguous there). This subset's symbol table
is the lexicon: `vector` and `pair` are template names by fiat. The
defensible reading: a compiler's parser ALSO consults a symbol table
it didn't compute from first principles at that moment; the
lexicon-vs-declaration difference is who populated the table, and
imp's per-identifier machinery is exactly the mechanism for
declaration-populated tables (the extension is specified, not built).
The indefensible reading would be claiming the dependent-name problem
is solved; it is not — it is the first construction met in seven
languages where the story machine CANNOT determine the answer and two
parses are genuinely live. The boss monster's final room is the
weighted two-stories experiment, and this language walked up to its
door and stopped.

## The rank renumbering: a prediction paying out as process

imp's PERSPECTIVE, after NEG forced an ad-hoc renumbering, prescribed:
derive ordering budgets, don't inherit them, and change shared
machinery in its own commit gated by every suite. C++ shift precedence
(between additive and comparison; `a < b >> c` completes both on one
slot) triggered exactly that case, and the prescription was followed:
the global table was renumbered FIRST (0 PUSH/LOAD/BRF/EXIT, 1
NEG/ENTER, 2 MUL/DIV, 3 ADD/SUB, 4 shifts, 5 comparisons, 6
statements), all 245 pre-existing tests passing before any cpp code
existed. The error-species ledger's value is precisely this: the
second occurrence of a species is process, not surprise.

## The first measured limit of emitter reuse

pysub and jssub imported imp's expression emitters wholesale; cpp
could not, because precedence TABLES are language-specific even when
chain MACHINERY is shared: imp's comparison emitters take an additive
right operand, C++'s take a shift chain. The import boundary settled
one level down — operand/chain helpers shared, emitter layer rebuilt
(~40 lines). This calibrates the interlingua claim usefully: story
machines and structural trackers transfer across languages; reflex
layers transfer exactly as far as the languages' algebra agrees.

## What went wrong

Nothing during implementation — all eight goldens and the differential
passed on the first run. Per the established discipline this earns
suspicion, but a better explanation is available this time: every
mechanism in cpp was the second-or-later use of a pattern whose first
use had already paid its error tax (splitting after merging, checkers
after two prior keying variants, ranks after the renumbering was done
properly). The series' error ledger reads as front-loaded learning:
five species, all on first encounters, none repeated.

## Closing the series: the skeptic's ledger, final form

Seven languages: expressions, data, symbols, statements/scopes,
layout, context-sensitive merging, context-sensitive splitting. The
reuse curve ended with the trackers and story machines fully portable
and the emitter layer portable modulo precedence. Every apparent
ambiguity met in seven languages dissolved under story state — and the
one that would not (dependent names) was explicitly fenced off. The
weighted machinery has now been idle through the entire pre-planned
series, which converts a suspicion into a finding: **for formal
languages designed to be parsed, story-state poverty explains
essentially all local ambiguity.** Natural language is the domain
where that finding is expected to fail, which is what makes the
two-stories experiment the necessary next step rather than one option
among several. The apparatus is finished; the question it was built
for is still open.

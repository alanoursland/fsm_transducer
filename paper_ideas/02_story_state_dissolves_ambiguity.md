# Most Apparent Ambiguity Is Story-State Poverty: A Seven-Language Study of Context-Sensitivity in Finite State

**Target venue:** SLE (Software Language Engineering) or Onward!; arXiv
(cs.PL). Empirical-engineering paper with a quotable thesis.

## Core claim

Across seven formal languages implemented in one finite-state
architecture — including the classically "hard" tokenization problems
(JavaScript's `/` as division vs regex literal; C++'s `>>` as shift vs
two template closers; Python's INDENT/DEDENT; unary vs binary minus) —
every local ambiguity dissolved under a small amount of explicitly
maintained narrative state ("story state": where are we, what are we
inside, what just happened, who has been introduced). No weights, no
backtracking, no lookahead machinery: one anchored state machine
narrates; local pattern machines consult the narration. We name the
design principle (the narrating tracker), provide the recurring
factorings (per-depth, per-identifier, per-lexeme instantiation that
makes non-regular wholes regular per factor), and characterize the
single construction in seven languages that resisted (C++ dependent
names — where the grammar is genuinely ambiguous and the standard
itself requires a disambiguation keyword).

## What exists

All seven languages, runnable, with differential tests against real
oracles; the splitting/merging retokenization duals (JS merges tokens
into regex literals; C++ splits `>>`); the per-identifier scope
checkers; a documented error ledger across the series.

## Experiments needed

Mostly packaging: state-count/complexity tables per language (the
analyze() certificates), a comparison against the standard treatments
(lexer hacks, GLR, parser feedback), and a precise statement of the
boundary (which context-sensitivity classes admit story-state
solutions; bounded-nesting limits as declared resource budgets).

## Related work

Lexer-parser feedback (the C typedef hack); scannerless and GLR
parsing; PEGs; Turnstile/indentation-sensitive grammars; visibly
pushdown languages (Alur & Madhusudan) — the closest formal cousin,
and a useful frame: story state generalizes the visibly-pushdown idea
from bracket-driven to narration-driven.

## Risks

Reviewers may read "we restricted to bounded depth" as evasion; the
paper must present the bound as the contribution (resource-budgeted
parsing with certificates), not a workaround.

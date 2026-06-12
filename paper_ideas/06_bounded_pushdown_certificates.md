# Resource-Budgeted Parsing: Unrolling Bounded Pushdown into Certified Finite State

**Target venue:** CIAA (Implementation and Application of Automata) or
FSMNLP; arXiv (cs.FL). The engine/theory paper.

## Core claim

For nesting bounded by K, classic pushdown transductions (shunting-yard
to RPN; bracket languages; indentation; template-angle disambiguation)
become regular, and an architecture that factors the product state
space into one small machine per resource value (per depth, per
identifier, per lexeme — "input-indexed schema instantiation") keeps
each factor independently *certifiable*: our analyze() emits, per
machine, state counts, determinizability (via minterm subset
construction over predicate alphabets — symbolic automata, Veanes et
al.), frontier bounds for the weighted scanner, and capture-register
bounds. The stack of transducer layers is the pushdown stack, unrolled;
the bound K is not a workaround but a declared budget with a
certificate — and matches how human parsing degrades (center-embedding
limits), which we note without overclaiming.

## What exists

The engine (tagged weighted NFA: captures, anchors, epsilon closure,
semiring merging, single-pass transduce with proven-and-tested frontier
bounds); determinization/minimization over predicate minterms;
analyze() certificates; seven formal languages as the evaluation suite
with differential oracles; property tests against Python's re engine.

## Experiments needed

Mostly formalization: theorem statements for the frontier bounds and
the factoring construction; benchmark tables (states, time, certificate
contents) across the seven languages; comparison with visibly pushdown
automata (Alur & Madhusudan) — our bracket trackers are VPAs with
narration, and the story-state generalization beyond brackets is the
delta worth stating precisely.

## Risks

CIAA will want theorems tighter than the engineering currently states;
the writing effort is in lifting tested invariants to proved ones.

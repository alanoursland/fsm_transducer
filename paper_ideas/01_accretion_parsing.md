# Parsing as Accretion: Deferred Commitment in a Stack of Weighted Finite-State Transducers

**Target venue:** arXiv (cs.CL); workshop versions at *SEM or a parsing
workshop. The architecture statement paper — the one the others cite.

## Core claim

Parsing need not be a decision procedure. We present an architecture in
which parsing is *accretion*: every token carries a weighted bag of
labels; each layer of small finite-state transducers reads labels and
adds more; old labels decay; the parser never commits to a structure.
Trees, spans, frames, or programs are *projections* computed downstream
by consumers with their own loss functions — the inference/decision
separation of Bayesian practice, applied to syntax.

## What exists (in this repository)

- The engine: weighted NFA scanner with epsilon transitions, capture
  registers (tagged-NFA style; Laurikari 2000), capture-anchored
  emissions, semiring path algebra (Mohri 1997), complexity
  certificates per machine (`analysis.py`).
- Eight implemented languages (arithmetic, JSON, S-expressions, an
  imperative language, a Python subset, a JavaScript subset, a C++
  subset, early-reader English), each with a declarative definition,
  hand-validated worked examples, and a runner; 270+ tests including
  differential tests against external oracles (eval, json.loads, real
  Python, real-engine round trips).
- The eager/confirmed emission distinction: every live analysis
  narrates with its path weight as it consumes (superposition record,
  never retracted); only analyses surviving to an accept point emit
  conclusions. Demonstrated on genuine lexical ambiguity in English.

## Experiments needed

1. Coverage and graceful-degradation curves on the early-reader corpus
   (public-domain primers, included in the repo): performance vs
   fraction of out-of-grammar input, against an all-or-nothing
   baseline parser.
2. Label-field quality metrics (per-label precision/recall against
   annotation) to complement the projection-level metrics.

## Related work

Weighted FST toolkits (Mohri et al., OpenFST); chart parsing keeps all
analyses but commits at decode; supertagging and CCG parsing as
label-first pipelines; "easy-first" and incremental parsing. The
distinguishing claims: (a) no decode step inside the parser at all;
(b) the annotation field, including dead analyses at fork weight, is
the output; (c) every label is provenance-traced to a named rule.

## Risks / honest limits

The weighted layer has only been exercised at small scale; rule
authoring does not yet scale (the companion proposal 07 addresses
this). The architecture trades structural guarantees (e.g.,
non-crossing brackets) for robustness — some applications want the
guarantees.

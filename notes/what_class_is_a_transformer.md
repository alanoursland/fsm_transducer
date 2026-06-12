# What Class Is a Transformer? (Grounding the Mirror)

The author's conjecture: the mirror will prove transformers are stacks
of finite-state machines — a transformer block is "technically" in the
regular class, with the weighted labels making it fuzzy; the practical
classification is unclear. This note records what is known, where the
literal claim fails, and the precise form in which the instinct is
right. It is the theoretical spine of paper_ideas/03.

## The literal claim fails in both directions

* **Transformers cannot do all of regular.** Fixed-depth,
  log-precision transformers lie in uniform TC0 (Merrill & Sabharwal).
  Regular contains NC1-complete word problems of non-solvable groups
  (Barrington / S5), believed outside TC0. Empirically the gap shows
  at the bottom: PARITY — a two-state automaton — is notoriously hard
  for transformers (Hahn 2020; Bhattamishra et al. 2020).
* **Transformers exceed regular elsewhere.** Soft attention averages,
  so MAJORITY and counting (Dyck-1-style balance) are easy — and no
  finite automaton computes them. Deletang et al. 2022 ("Neural
  Networks and the Chomsky Hierarchy") observed the scrambling
  empirically: the Chomsky hierarchy is the wrong axis.
* **One exact boundary result:** masked unique-hard-attention
  transformers recognize exactly the STAR-FREE regular languages
  (Angluin, Hahn et al.) — regular minus modular counting. Parity
  fails precisely because it is regular but not star-free.

## The rigorous home for the instinct: Krohn-Rhodes

Every finite automaton decomposes into a cascade of simple machines
(Krohn-Rhodes). Liu et al. 2023 ("Transformers Learn Shortcuts to
Automata") show trained transformers implement such cascades,
flattened to O(log n) or O(1) depth when the automaton's monoid is
SOLVABLE, and obstructed exactly at non-solvable structure. The
defensible form of the conjecture:

> Transformers are shallow, weighted, counting-augmented Krohn-Rhodes
> cascades: stacks of small finite machines composed through a shared
> additive medium, with soft attention supplying counting that pure
> FSMs lack, and lacking the modular counting that pure FSMs have.

That sentence describes this architecture clause for clause: stacks of
small machines (layers); shared additive medium (label field ~
residual stream); weighted (label weights = weighted automata
computing rational series — the "fuzzy" exactly named); counting as an
explicit budget (K-bounded trackers pay in states what attention pays
in averaging). The accretion architecture is the cascade built in
glass, with the counting explicit instead of smuggled through softmax.

Observation worth flagging: every story machine built in this project
so far is aperiodic (star-free) — depth tracking, container kind,
expectation bits, declared-flags. The architecture may feel natural
precisely because it lives in the transformer-friendly fragment.

## Three testable predictions for the mirror (paper 03)

1. Probes recover story-machine states cleanly where the underlying
   monoid is solvable/aperiodic — i.e., for every tracker this project
   has built.
2. Transformers fail, or learn brittle shortcuts, exactly where a
   machine would need modular counting; the glass box names the
   obstruction algebraically (the syntactic monoid).
3. Where the architecture uses label weights (primer's story forks),
   models show graded superposition rather than discrete state —
   weighted automaton mirrored as soft attention.

## Classification "in practice"

The least-wrong answer in the current literature: first-order logic
with counting / majority (FO(M), threshold circuits) for soft
attention; star-free regular for masked hard attention; with empirical
behavior that respects neither boundary reliably at trained scale. The
project's own stance transfers: stop asking which Chomsky level, start
issuing resource-budgeted certificates — which is what analyze() does
for the glass box and what paper 03's probes would do for the black
one.

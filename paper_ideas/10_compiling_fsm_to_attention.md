# Compiling Weighted Finite-State Cascades into Transformer Attention

**Target venue:** mechanistic-interpretability venues (BlackboxNLP,
NeurIPS interp workshops), main track with strong capacity results.
Companion and prerequisite to proposal 03; based on the author's
delta->QKV research (references/prior_work_transformers_fsm.md, with
review notes).

## Core claim

We construct a compiler from finite-state transition tables — and,
beyond prior work, from *weighted, label-emitting FSM cascades* of the
fsm_transducer architecture — into transformer attention parameters
(delta(q, a) -> QKV), producing networks that execute the machines
exactly. The compiled models serve three purposes: (1) constructive
lower bounds on what attention can represent, at known parameter
budgets (states vs embedding dimension — the capacity curve);
(2) ground-truth reference models for interpretability and automata-
extraction methods; (3) the *theoretical attractor* against which a
trained twin (same data, same architecture; the regex_transformer
project) is measured in weight and activation space.

## Differentiation from Tracr/RASP (the question reviewers will ask)

Tracr (Lindner et al. 2023) compiles RASP programs to weights. We
compile a different and complementary source language: weighted
automaton cascades with semiring path algebra, capture registers, and
label emission — the substrate of a working parser for eight
languages, including an English fragment. The deltas: (a) weights —
compiled soft superposition, not boolean routing; (b) cascades —
Krohn-Rhodes-structured stacks, aligning compiled depth with Liu et
al.'s shortcut theory; (c) a trained twin and a behavioral label spec
exist for every compiled machine, enabling attractor-distance
measurements no Tracr-style pipeline currently has.

## What exists

The source machines (fsm_transducer: every machine carries a
complexity certificate); the trained-twin harness (regex_transformer:
deterministic training, state-classification head); the author's
draft delta->QKV construction notes.

## Experiments

1. Capacity: states encodable vs d_model; where compilation needs
   superposition (cf. Toy Models of Superposition).
2. Exactness: compiled model vs symbolic machine, exhaustive on
   bounded lengths (the project's standard differential discipline).
3. Attractor distance: train the twin, measure convergence toward /
   divergence from the compiled reference across monoid classes
   (aperiodic vs solvable vs non-solvable) — Liu et al. predicts the
   ordering.
4. Extraction calibration: run automata-extraction methods on both
   compiled and trained models; the compiled ones have known ground
   truth.

## Risks

Compiled and learned solutions may be far apart in weight space even
when behaviorally identical (many implementations of one machine);
mitigate by comparing in activation/representation space and via
interventions rather than raw weights.

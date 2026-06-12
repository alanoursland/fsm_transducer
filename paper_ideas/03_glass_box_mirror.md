# A Glass-Box Mirror for Transformer Interpretability: Probing Trained Models Against an Explicit Story-Machine Parser

**Target venue:** BlackboxNLP, then NeurIPS/ICLR main track if results
are strong. The flagship scientific paper; highest risk, highest value.

## Core claim

Mechanistic interpretability seeks structure inside trained
transformers; we provide the matched control: a fully explicit symbolic
parser (weighted label field ~ residual stream; transducer layers ~
blocks writing additively; anchored "story machines" ~ global state
carried and consulted; decay ~ subspace reuse) that emits, for every
token, the exact latent variables a competent parser of the same input
must maintain — depth, container kind, expectation state, story fork
weights. We train small transformers on the same corpora (the companion
regex_transformer project) and ask: do linear probes recover the
glass-box labels at the positions the symbolic parser asserts them? Do
fork tokens (genuinely ambiguous prefixes) show superposed
representations that collapse where the symbolic machine's losing path
dies?

## What exists

Both instruments: the parser emits per-token story-state labels for
eight languages including an English fragment with a true lexical fork
("Play." vs "Play is fun."); regex_transformer trains single-layer
transformers with a state-classification head on regex languages, with
coverage-balanced data generation and deterministic training.

## Experiments needed

1. Train models on (a) regex languages, (b) the arithmetic/JSON
   languages, (c) the early-reader corpus.
2. Probe hidden states for: DEPTH:d, container kind, expectation
   state, MINUS:UNARY/BINARY, STORY:IMP/STORY:DECL at fork tokens.
3. The headline measurement: representation of ambiguity — compare the
   model's fork-token geometry against the symbolic machine's weighted
   superposition, and track both through the disambiguating token.
4. Negative-result protocol: where probes fail, characterize what the
   model maintains instead (this is a result, not a failure — it
   locates where transformers are NOT story machines).

## Theoretical grounding

See notes/what_class_is_a_transformer.md: the precise form of the
mirror hypothesis is Krohn-Rhodes — transformers as shallow, weighted,
counting-augmented cascades of simple machines (Liu et al. 2023), with
the star-free boundary (Angluin/Hahn) explaining both why every story
machine in this project probes as transformer-friendly (all aperiodic)
and where failures should localize (modular counting / non-solvable
monoids). The probing predictions in that note are this paper's
hypothesis section.

## Related work

Residual stream framing (Elhage et al. 2021); transformers and formal
languages (Liu et al. 2023 "Shortcuts to Automata"; Bhattamishra et
al.; Merrill's expressivity line); probing classifiers and their
pitfalls (Hewitt & Liang control tasks — we have unusually good
controls, since the glass box defines exactly the predictive label).

## Risks

Probing positives are weak evidence (correlation, not mechanism);
mitigate with causal interventions (activation patching toward the
other story's state). Small models may shortcut (per Liu et al.) —
which is itself a finding the glass box can name precisely.

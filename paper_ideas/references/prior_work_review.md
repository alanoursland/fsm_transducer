# Review notes on prior_work_transformers_fsm.md

The author's prior-work survey for the delta->QKV compiler direction.
Substance is right; some attributions need correction before anything
is submitted, and several 2021-2024 results are missing that are now
load-bearing. (See also notes/what_class_is_a_transformer.md.)

## Corrections

1. **Hahn (2020)** shows *limitations* — PARITY and 2-Dyck are not
   robustly recognizable under his assumptions. It does NOT establish
   "transformers recognize regular languages only," and that claim is
   false in both directions: parity is regular and hard; majority is
   non-regular and easy. The compiler's goal survives unchanged: a
   delta->QKV construction witnesses containment of *specific*
   machines, which needs no equivalence claim.
2. **Weiss, Goldberg & Yahav (2018)** concerns finite-precision RNNs
   (correctly placed in the bibliography, wrongly used for transformer
   claims in section 2). The transformer-side work from that group is
   **RASP: "Thinking Like Transformers" (ICML 2021)** — and it is the
   direct ancestor of the compiler idea, not background.
3. **"Merrill & Sabharwal (2021), finite-state dimension"** — no such
   paper under that framing; likely a misremembering of the saturated
   transformers -> TC0 line (correct in the bibliography as Merrill,
   Sabharwal & Smith 2022) plus the log-precision TC0 result (Merrill
   & Sabharwal 2023). The "embedding dimension ~ encodable states"
   intuition is fine as OUR capacity hypothesis; do not attribute it.
4. **"Rabinowitz et al. 2020+, Differentiable Automata"** — could not
   be matched to a real publication; the solid citation already in the
   bibliography is Hannun et al. 2020 (Differentiable WFSTs), which
   deserves promotion: it is the gradient-trainable version of this
   project's exact engine (weighted transducers over semirings) and is
   the natural weight-learning path for fsm_transducer.

## Missing must-cites (the "check 2023-2025 work" item, resolved)

- **Tracr** (Lindner et al. 2023): compiles RASP programs into actual
  transformer weights as interpretability ground truth. The nearest
  neighbor to delta->QKV; cite it first and differentiate: Tracr
  compiles RASP programs, we compile *weighted FSM cascades* — and we
  uniquely pair the compiled attractor with a trained twin
  (regex_transformer) and a full symbolic system (fsm_transducer).
- **Liu et al. 2023** ("Transformers Learn Shortcuts to Automata"):
  trained transformers implement Krohn-Rhodes-style cascades, flat for
  solvable monoids, obstructed at non-solvable ones. This is the
  theorem-shaped version of "the attractor" and predicts WHERE learned
  weights should approximate the compiled reference.
- **Angluin/Hahn et al.** exact characterization: masked unique-hard-
  attention transformers = star-free regular. Defines the fragment
  where compilation should be clean. (Every story machine built in
  fsm_transducer to date is star-free.)
- **Barrington (1989)** for why all-of-regular is out of reach at
  constant depth (S5 word problems, NC1-completeness).
- **Deletang et al. 2022** (Neural Networks and the Chomsky Hierarchy)
  for the empirical scrambling of the hierarchy.
- **Bhattamishra et al. 2020** for empirical parity/counter results.
- **Zhou et al. 2023 (RASP-L)** for the learnability-of-compilable-
  programs angle (what compiles short, generalizes).
- Automata *extraction* (Weiss et al. 2018, L*-based, RNNs; successors
  for transformers) — the compiler provides their ground truth.

## The three-leg program (how this slots in)

1. **fsm_transducer** — the symbolic cascade (behavioral spec; emits
   the latent labels).
2. **regex_transformer (training side)** — the trained twin (the
   learned point in weight space).
3. **regex_transformer (construction side)** — the delta->QKV compiler,
   already implemented as an existence proof: hand-built transformers
   executing simple regexes exactly via one-hot embeddings. Legs 2 and
   3 share a codebase, which makes compiled-vs-trained comparison a
   within-harness measurement rather than a cross-project one.

The mirror experiment (paper_ideas/03) gains a second measurement
axis: not only "do probes recover the glass box's labels?" but "how
far, in weight/activation space, is the trained model from the
compiled reference?" — with Liu et al. predicting the answer varies
with the monoid's algebra. That comparison is the mechanistic version
of the whole conjecture.

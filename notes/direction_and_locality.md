# Direction and Locality: RTL, Mid-Text Starts, and Parallel Parsing

Three author questions, one theme: relaxing the left-to-right
anchored assumption. The theory says yes to all three, with shared
machinery.

## 1. Running machines backwards (RTL)

Regular languages are closed under reversal: flip transitions, swap
start/accept (multi-accept -> fresh start + epsilons), run on
reversed input. Difficulty grades by machine kind:

* acceptors: trivial (a reverse() builder is an afternoon);
* trackers: elegant — the reversed bracket tracker is the same
  machine with bracket roles swapped;
* emission/capture machines: hard — anchors and captures are
  forward-temporal (the same blocker as bidirectional generation;
  same eventual fix: the two-tape discipline).

The payoff beyond editors: forward pass = what the prefix implies;
backward pass = what the suffix implies; for weighted machines,
forward x backward per position = the POSTERIOR — the
forward-backward algorithm, native to the semiring engine. This
bears directly on story-coherent projection: suffix evidence kills
doomed forks at every position, not just at the period. An editor
token color IS this posterior.

## 2. Starting mid-text

* The reflex layer (unanchored pattern emitters) does not care —
  mid-text is its native mode; most of the label field survives
  starting anywhere.
* Story machines: start in the WEIGHTED SUPERPOSITION of all states
  (universal frontier, weights = priors) and let evidence collapse
  it — the primer fork generalized to ignorance-of-prefix. Collapse
  is fast because languages are full of synchronizing events
  (sentence-final punctuation resets the clause machine to S0 from
  ANY state; the synchronizing-words literature, in work clothes).
  Editors already live this way: incremental lexers rescan from a
  checkpoint until running state matches cached state (tree-sitter).
* Engine gap: transduce(start_states="all") — frontier
  initialization, ~20 lines; superposed weighted frontiers are
  already the engine's home turf.

## 3. Parallel chunked parsing

A chunk induces a transition function on states; for weighted NFAs, a
matrix over the semiring (transfer matrix). Composition is
associative -> parallel reduction: per-chunk matrices in parallel,
log-depth combine. Emissions: two-pass (parallel entry-frontier
discovery, then parallel replay with known entries) or speculative
per-entry-state (Mytkowicz et al., data-parallel FSMs) — cheap here
because state counts and alphabets are tiny (21 input labels for the
whole tier-1 clause machine). Note question 3 contains question 2:
every chunk after the first starts mid-text.

Practical tiers: sentence-level parallelism is free TODAY
(per-sentence anchoring made sentences independent; thread-pool the
corpus — though pure-Python wants multiprocessing or a compiled
engine to win). Sub-sentence parallelism = the transfer-matrix build.

## The mirror punchline

Parallel-prefix composition of transition functions in log depth is
LITERALLY how transformers implement automata (Liu et al. 2023's
shortcut constructions). Question 3 asks: can we do explicitly what
attention does implicitly? Yes, by the same associative algebra —
one more pane in the glass box. The editor use case (partial,
incremental, bidirectional parsing) and the transformer mirror turn
out to be the same math: posteriors from two directions,
synchronization after uncertainty, and associative state
composition.

## Recorded next steps (when wanted)

1. transduce(start_states="all") + a synchronization demo (clause
   machine recovers mid-sentence; measure tokens-to-collapse).
2. reverse() for acceptors/trackers; forward-backward posterior over
   the McGuffey corpus as the projection-coherence aid.
3. Sentence-level multiprocessing for corpus runs (free speedup).
4. Transfer-matrix chunk composition (the real build; also the
   cleanest possible artifact for paper 03/10, since it IS the
   shortcut construction in symbolic form).

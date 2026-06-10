# Improvement Plan: fsm_transducer

## Mission framing

The goal of this project is a *fully understandable* symbolic language model:

- **Auditability.** Every label on every token traceable to a named rule and a
  weighted path. (Largely achieved already via the debug renderer.)
- **Provable bounds.** Time, space, and state-space complexity of every pass
  stated and tested, not just observed.
- **Ethical by construction.** No learned self-representations; nothing in the
  architecture even resembles the substrate such representations would need.
  Weights come from explicit rules or transparent fitting, never end-to-end
  gradient descent over opaque parameters.

A sibling project, `regex_transformer` (same author), contains regex→DFA
machinery and an experimental harness whose discipline is worth importing.
Both codebases are owned by the same author; code may be copied freely.

## Honest assessment of the current state

The NFA engine in `fsm.py` is real: epsilon closure, cycles via `star`,
captures, semiring path merging. The shortcuts relative to the design docs:

1. **The scanner is a matcher, not a transducer.** `FSMScanner.scan` restarts
   the machine at every start position (O(n) independent scans of up to O(n)
   each) instead of one pass carrying a frontier. The design docs describe FSM
   *blocks transforming sequences*; the implementation runs a weighted regex
   search at every offset.
2. **No determinization, minimization, or composition.** Machines run
   independently and communicate only through the label bag. (Partly a design
   choice — accretion replaces composition — but minimization matters for
   bounds and for the regex front-end.)
3. **The demo grammar barely exercises the engine.** Mostly `compile_linear`
   chains; one `star` rule. The general machinery is nearly untested by
   realistic grammars.
4. **No packaging, no CI, no eval.** No `pyproject.toml`, no root README, no
   pinned deps, no corpus run, no benchmark.

### What regex_transformer actually offers

Its `src/fsm/` compiler is **not** a Thompson construction: it does BFS over
string prefixes (depth ≤ 10), classifies each prefix with Python `re`, then
minimizes. Good for generating bounded training data; not portable as a
general regex front-end, and it discards group structure (no state-name hook).

Portable as-is:
- the `FSM` dataclass shape (dense int states, `delta: dict[(state, sym), state]`,
  explicit reject state, state→class mapping) — a good *compiled target* format;
- `_minimize_dfa` partition refinement;
- `serialize.py`;
- the testing/determinism discipline (fixed seeds, coverage-aware generation).

Not portable: the prefix-BFS compile path. A proper construction (workstream 3)
will eventually serve regex_transformer too, removing its depth-10 limit.

## Workstreams

Ordered so each lands independently; 1–3 are the core, 4–6 build on them.

### 1. Packaging, CI, and hygiene (small, do first)

- Root `README.md`: the accretion thesis (condense `notes/parsing_as_accretion.md`),
  quickstart, pointer to planning docs.
- `pyproject.toml`: package `fsm_parser` properly (`src/` layout is already
  right), declare pytest, add `pip install -e .`.
- GitHub Actions: pytest on 3.11/3.12, plus `ruff` lint.
- Move `src/tests` → `tests/` (or configure pytest rootdir explicitly).

Exit criterion: fresh clone → `pip install -e .[dev] && pytest` passes in CI.

### 2. True single-pass transducer scan

Add `FSMScanner.transduce()` alongside (not replacing) `scan()`:

- One left-to-right pass; at each position, inject a fresh start-state path
  into the live frontier (so all start offsets are still covered) and advance
  every path one step. This is the standard "all-matches" NFA simulation:
  worst-case O(n · |Q| · |captures-sig space|) total instead of O(n²·|Q|).
- `scan()` becomes a thin compatibility wrapper; tests assert both produce
  identical deltas on the existing suite (they should — same path semantics,
  different scheduling).
- Document and *test* the bound: a property test (hypothesis) generating
  random machines and inputs, asserting frontier size never exceeds the
  computed merge-key bound |Q| × |capture signature space|.

This is the "provable bounds" workstream's anchor: the bound goes in a
docstring with its argument, and the test enforces it.

### 3. Regex front-end (the borrowing workstream)

New module `fsm_parser/regex_compile.py`:

- **Tagged Thompson construction** over *label conditions*, not characters:
  atoms are `HasLabel("POS:DET")`-style conditions, so the same compiler
  serves token streams and (via `char_blocks`) character streams.
- **Named groups carry emissions.** `(?P<np> ...)` compiles to epsilon
  entry/exit transitions emitting `NP_START` / `NP_END` (Laurikari tagged-NFA
  style). This sidesteps the state-naming problem: states stay anonymous;
  *emissions* are named. Group names may also be attached as `StateId.name`
  prefixes for debug output — provenance, not semantics.
- Syntax: concatenation, `|`, `*`, `+`, `?`, `(?P<name>...)`, atom syntax
  `<LABEL>` or `<LABEL@0.3>` (label with weight threshold). Parser is ~150
  lines of recursive descent; do not reach for a parser generator.
- Output is a plain `FSM` via the existing `FSMBuilder` — the engine is
  untouched.
- YAML grammar config gains a `regex:` rule type next to the existing
  combinator type.

Ported from regex_transformer (with attribution comments pointing at origin):
- partition-refinement minimization, adapted to condition-labeled transitions
  (two transitions are "same symbol" iff their conditions are equal; require
  conditions to be hashable/frozen — they already are dataclasses, audit for
  `frozen=True`);
- the dense `FSM` dataclass as an optional *compiled/minimized* representation
  with `serialize.py`-style round-tripping, for grammars that are pure
  acceptors (no captures). Captureful machines stay in NFA form.

Back-port (separate task, in regex_transformer's repo): replace its prefix-BFS
compiler with this construction, removing the depth-10 limit.

### 4. Determinization + bounds for acceptor machines

For emission-free, capture-free sub-machines (conditions over a finite label
set): subset construction → minimize → O(n) scan guarantee. Machines with
captures/emissions are left nondeterministic but get the workstream-2 bound.
Add a `fsm.analyze()` report: state count, determinizable?, frontier bound,
capture-space bound. This is the user-facing "provable bounds" artifact —
every grammar can print its own complexity certificate.

### 5. Exercise the engine: a real grammar

The engine outgrew its grammars. Write one mid-sized grammar (POS dictionary
block + NP/PP/VP regex rules + role rules, ~30–50 rules) using the new regex
front-end, against a small real corpus (e.g. a few hundred UD English
sentences, gold POS stripped or kept per experiment).

- Projection step: label field → spans (threshold + non-crossing greedy).
- Metric: span-level precision/recall vs. UD bracketings, plus the metric the
  architecture actually argues for: graceful-degradation curve (performance
  vs. fraction of OOV/ungrammatical input) compared against an all-or-nothing
  baseline.
- This is the first *experiment*; everything above is apparatus.

### 6. Stress and property testing

- Hypothesis-based property tests: random regexes → compile both through the
  new front-end and Python `re`; on random strings, acceptance must agree
  (the oracle trick regex_transformer already uses — keep it, it's good).
- Pathological cases: nested stars, large alternations, capture blow-up;
  assert the workstream-4 bounds hold and document where the cliff is.

## Sequencing and effort

| # | Workstream | Size | Depends on | Status |
|---|-----------|------|------------|--------|
| 1 | Packaging/CI | S | — | done |
| 2 | Single-pass transduce | M | 1 | done |
| 3 | Regex front-end + minimizer port | L | 1 | done |
| 4 | Determinization + analyze() | M | 3 | done |
| 5 | Real grammar + eval | L | 3 | example grammar done; corpus eval open |
| 6 | Property/stress tests | M | 2, 3 | oracle + bound tests done; hypothesis fuzzing open |

Implementation notes (deviations from the plan as written):

* Group START/END marking is implemented with hidden capture registers
  (``Capture(mode="first")`` was added to the engine) plus an exit-state
  ``on_enter`` emission, not with static first/last transition sets — the
  static sets mislabel loop iterations (``<ADJ>* <NOUN>`` would mark every
  adjective as a possible start). The capture approach gives exact span
  endpoints through loops and emits nothing for zero-width matches.
* ``transduce()`` keeps ``scan_start`` in the path merge key so its delta
  multiset is exactly ``scan()``'s; the practical win is one input pass and
  immediate death of failed paths, verified by a frontier-bound test.
* Minimal-DFA sizes are measured over the *minterm* alphabet, which is
  larger than the textbook exclusive alphabet (a slot can satisfy several
  conditions at once); tests document this.

Workstreams 2 and 3 are independent and can proceed in parallel. Workstream 5
is the payoff and should not slip behind further engine work: after 1–3, the
next thing this project needs is a result, not a feature.

## Explicit non-goals

- No learned weights beyond transparent fitting (e.g. grid/least-squares over
  rule weights against annotated data, if ever) — no gradient descent over
  opaque parameters.
- No transducer composition (Mohri-style). Accretion through the shared label
  bag *is* the composition mechanism; revisit only if workstream 5 shows it
  failing.
- No neural components in this repo. Cross-pollination with regex_transformer
  flows the other way: this repo supplies compiled FSMs as ground truth for
  that repo's interpretability probes.

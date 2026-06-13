### Guide: Extending the Symbolic Transformer Language

This document serves as the formal guide for extending the language architecture. It defines the constraints and patterns required to ensure that new components remain compatible with the `codex/` and the overarching "glass-box" cognitive architecture.

---

### 1. The Core Constraint: Determinism

Every machine must be a **deterministic transducer**.

* **Input:** A sequence of tokens/labels.
* **Output:** A deterministic sequence of state transitions and emissions.
* **Prohibition:** Do not implement probabilistic logic (e.g., `random.choice`) inside an FSM. All "choice" must be represented as a **weighted fork** where paths persist in superposition until projection.

### 2. Lexical Rules (The `lexicon.yaml` Protocol)

When adding new entries, follow the weighted paradigm:

* **Weighted Labels:** Every entry must map to a label-weight dictionary (e.g., `play: {V: 0.55, N: 0.45}`).
* **Ambiguity Class:** If a word has multiple parts of speech, it MUST be defined with weighted priors mirroring the ambiguity class.
* **Fallback:** All unknown words must map to the `ERROR:UNKNOWN_WORD` fallback to ensure graceful degradation.

### 3. FSM Component Rules

New machines added to the `codex/` must adhere to the **Clause Story Machine** signature:

* **Anchored:** Machines should be anchored to sentence-final punctuation (`.`, `!`, `?`).
* **Eager vs. Confirmed:** * Use **Eager Emissions** for the "label bag" (superposition record). These fire on every consuming transition.
* Use **Confirmed Emissions** (CaptureAnchors) only on the final punctuation transition. These record the "survivor" frame.


* **No Side-Effects:** FSMs must not modify global state outside of the designated label field and stack operations.

### 4. Semantic Frame Standards

To maintain round-trip verification (the 90% identity goal), all semantic frame extensions must use the established **Stack Instruction Set**:

* **ENT / IMPYOU:** Push referents.
* **EVT:** Push a new frame `{pred: v}`.
* **AGENT / THEME / ATTR:** Pop/Push operators to link values to frames.
* **END:** Finalize the frame and pop to output.
* **Constraint:** Any extension must allow SVO-order serialization via dual-direction completion (Agent from below, Theme from above).

### 5. Semantic "Brakes" (Levin Class Integration)

To solve the "Syntactic Soup" problem (the Semantic Gap), all new `EVT` machines must define:

* **Thematic Roles:** Define the required `AGENT` and `THEME` types (e.g., `+animate`, `+physical`).
* **Selectional Check:** Before emitting an `AGENT` or `THEME` label, the machine must query the `ENTITY` referent's metadata. If the check fails, the transition must be aborted, forcing the FSM to backtrack.

### 6. Integration Protocol

To add a machine to the `codex/`:

1. **Manifest:** Create a `.yaml` manifest containing the description, alphabet, K-depth, and dependencies.
2. **Registration:** Register the machine in the `codex/catalog.md`.
3. **Ratchet Test:** A new golden test case MUST be added to `src/tests/` that proves the new component maintains the 90% identity round-trip threshold.

---

**Rule of Thumb:** If an extension requires you to add a new `Instruction` to the builder, it is likely too specific. Try to compose the logic using existing `EVT/AGENT/THEME` instructions first. If the current set is insufficient, submit a proposal to expand the `instruction_set` globally.
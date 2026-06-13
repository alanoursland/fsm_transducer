# CORRECTIONS_REQUESTED.md

## Linguistic & Grammatical Audit: Generated Text

This document tracks identified linguistic anomalies, grammatical inconsistencies, and semantic failures observed in the current generation pass of the Small Language Model (SLM) parser. These corrections are mandatory for the next iteration of the generator FSMs.

### 1. Case-Matching / Nominative-Accusative Errors
* **Observed:** `Ran at he?`
* **Correction:** The grammar must distinguish between subject pronouns (Nominative: *he, she, they*) and object pronouns (Accusative: *him, her, them*). The parser/generator FSM state for `AGENT` must enforce nominative case, while `PATIENT`/`THEME` slots must enforce accusative.

### 2. Semantic Selectional Preference Failures
* **Observed:** `Fish noise from me.` / `Drown eyes for hands.`
* **Correction:** Predicates (`Fish`, `Drown`) must be tagged with Levin-class-derived selectional restrictions (e.g., `+animate`, `+physical`). The generator's emission logic must abort any path where the candidate referent (e.g., `noise`, `eyes`) fails the semantic type check.

### 3. Argument-Structure Incompleteness (Valency)
* **Observed:** `Made Dick have?`
* **Correction:** The generator must enforce "Frame Closure." If an `EVT` (event/predicate) is pushed onto the stack, the FSM state must be blocked from transitioning to `PUNCT` (sentence end) until the required thematic roles (`AGENT`/`THEME`/`ATTR`) are filled according to the verb's subcategorization frame.

### 4. Semantic Coherence & "Syntactic Soup"
* **Observed:** `Kill noise walks.` / `Sat cut got.`
* **Correction:** The generator is current treating POS tags as a "bag of words." It must be constrained to only select verbs that form semantically valid chains within the current `STORY` context. Future iterations must implement the `Selectional Filter` as defined in the `codex/` extension guide.

### 5. Animacy/Referent Mismatch
* **Observed:** `Runs lighthouse shut.`
* **Correction:** The Agent-Referent binding must ensure that `+animate` agents are only linked to `+animate` predicates. `Lighthouse` ([-animate]) cannot be bound to self-motion predicates (Walks/Runs) unless the narrative FSM explicitly allows for personification.

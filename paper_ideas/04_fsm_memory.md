# State as Memory: Finite-State Machines as a Bounded, Auditable Memory Substrate for Game Agents

**Target venue:** AIIDE or FDG (full paper); arXiv (cs.AI). Strong fit:
these venues value playable ideas with formal teeth.

## Core claim

An agent's memory can be a population of small state machines — one per
relationship, belief, or arc — where the current state IS the memory.
The theory is Myhill–Nerode: a state of a minimal machine is an
equivalence class of histories that imply the same future, i.e., memory
with behaviorally irrelevant detail provably removed. The construction
yields, by construction rather than by engineering effort: O(1)
retrieval (state is always loaded); provable memory bounds (sum of
state counts); auditable psychology (why does the NPC distrust the
player? — replay the transitions); reconstructive rather than archival
recall (the agent remembers RESENTMENT, not the inventory of slights);
consolidation as automaton minimization; forgetting as weight decay;
grudges as absorbing states; uncertain memory as weighted superposed
states. A two-store design (provenance-carrying event log as episodic
trace; machine states as consolidated store; minimization as the
consolidation process) matches the standard model from memory science.

## What exists

The machine substrate (weighted NFAs with per-entity instantiation,
minimization, decay) is implemented and tested in the parser project;
the game-side design documents (narrative arcs, social state,
trust-modulated beliefs) specify the consumer.

## Experiments needed

1. A playable or simulated scenario: agents ingest an event stream;
   per-entity memory machines update; behavior diverges by memory
   state; the audit trail explains every divergence.
2. Consolidation study: minimize periodically, show what was forgotten
   and prove it was behaviorally safe to forget.
3. Comparison axes vs vector-store/LLM memories: retrieval cost,
   bound-ability, auditability, believability (user study optional).

## Related work

Schank's scripts and dynamic memory; Sims-style need/relationship
models; Versu/Praxis and social-physics engines (Evans & Short);
Façade's drama management; recent LLM-agent memory papers (generative
agents) as the contrast class: unbounded, unauditable, post-hoc
explanations vs provenance.

# FSMs as Agent Memory

The author's idea, four words: **FSMs as agent memory.** Not FSMs
*having* memory — FSMs *as* the memory substrate. An agent's memory is
a collection of small state machines, each currently in a state (or a
weighted superposition of states). This note unpacks why that is the
theoretically right answer rather than a clever economy, and how it
completes the system the two projects have been building.

## The core argument: a state is a compressed history

Myhill–Nerode (already load-bearing in this repo for label
vocabularies): a state of a minimal machine is an equivalence class of
all pasts that imply the same future. That is what memory is FOR. An
agent does not need to remember what happened; it needs to remember
what what-happened implies for future behavior. FSM-as-memory stores
exactly the distinctions that change future action — memory with the
irrelevant detail *provably* removed, relative to the behaviors the
machine's transitions encode.

## Already built, three times, unnamed

| existing machine | what it remembers |
|---|---|
| imp scope checkers (bit-stacks) | the entire token-stream past, compressed to "is x declared, at which levels" |
| story machines (clause/depth/shape) | working memory of the discourse |
| the game's relationship/arc states | relationship history, compressed to a beat |

The scaling pattern is also already validated: **per-entity
instantiation** (one relationship machine per acquaintance, one belief
machine per proposition) is imp's input-indexed schema — the factoring
that makes unbounded entity spaces regular, paid per entity actually
encountered.

## Memory phenomenology, mapped to existing machinery

* **Uncertain memory = superposed states.** "I think we're friends but
  he may resent me" is an NFA frontier with two weighted live states —
  primer's fork at relationship timescale. Evidence reweights;
  resolution collapses; the eager/confirmed split records what was
  considered vs what was committed.
* **Reconstructive memory = state, not log.** Humans store gist and
  confabulate detail; an FSM-memory agent recalls "RESENTMENT," not
  the inventory of slights. Emotionally realistic NPC memory falls out
  of the representation.
* **Consolidation = minimization.** Sleep, for an FSM-memory agent, is
  partition refinement: merge states whose distinctions no longer
  matter for any future behavior. `fsm_parser.analysis.minimize()` is
  the consolidation operator, already implemented and tested.
* **Forgetting = decay + merging.** The normalization machinery
  (decay, FORGOTTEN) — the one major component still unexercised —
  finds its natural home here: weights on memory states fade unless
  transitions refresh them.
* **Trauma/grudges = absorbing states.** No transition out except a
  specific key (the apology transition). Unforgettable-unless —
  mechanically expressed, narratively legible.

## What it inherits from the mission statement

* **O(1) retrieval**: the state is always loaded; queries are label
  conditions; no episodic search.
* **Provable memory bounds**: each machine has a state count; total
  memory = sum over instantiated machines. "Provable bounds" extends
  from parse time to memory capacity — something no neural memory
  offers.
* **Auditable psychology**: why does the NPC distrust the player?
  Replay the transitions. Provenance for mental state.
* **No self-representation risk**: memory as distributed small
  machines over world/relationship state has no global self-model
  substrate — consistent with the project's ethics-by-construction
  stance.

## It completes the system

Parsing = story recognition. The narrative layer = story generation.
Memory = **story state**: an arc in progress IS the memory of
everything that happened in it, compressed to a beat. The narrative
layer doesn't consult memory; it is memory. Two agents sharing a story
= one machine running in two heads; misunderstanding = state
divergence; reconciliation = a protocol that re-synchronizes joint
state. The agent is a bag of story machines mid-story.

## The honest limit, and the two-store answer

Pure state serves semantic / procedural / relational memory; it does
not serve episodic recall (replaying specific scenes), and should not
pretend to. The architecture already holds the complement: the **label
field with provenance is the episodic trace** (the game docs' "memory
snippets"); FSM states are the consolidated store. Episodic log +
semantic state + a consolidation process moving information between
them (minimization, decay) is the mainstream two-store model from
memory science — implementable here with mechanisms that all exist.

## Recorded next steps

* a `memory machine` schema in the language-definition format: states,
  refresh transitions, decay rates, absorbing states, per-entity
  instantiation rule;
* primer v2 anaphora as the first memory consumer: "See Spot. He
  runs." — the referent store is a per-entity memory machine at
  discourse timescale (and the miniature of the game's social graph);
* consolidation experiment: run an agent's event stream into per-
  entity machines, minimize periodically, and show the audit trail of
  what was forgotten and why it was safe to forget;
* the game integration: relationship arcs as memory machines shared
  (in state) between NPC pairs; trust as a weight the semiring
  propagates through them.

## Addendum: memories are executable (the belief stream)

The author's elaboration, which makes memory generative rather than
archival:

> The player tells an NPC "Jack is angry at Mary." The parser converts
> that into semantic representation and the agent remembers that chain
> of labels. Later, that chain of labels is an FSM that modifies the
> labels of the system. If the NPC learns "Mary kissed Mark", a
> jealousy script connects the two and the NPC can tell the player
> "Jack is angry at Mary because she kissed Mark." It doesn't even
> have to be true.

Four design consequences:

**1. Inference is parsing the belief stream.** Beliefs are slots in a
second stream, ordered by acquisition time; inference scripts
(jealousy, contradiction, generalization) are pattern emitters over
that stream; the social story machines are its anchored trackers. The
engine already supports this literally — ParserState is multi-stream
and AddSlot exists. Parse -> frames -> AddSlot("belief") -> script
machines transduce the belief stream -> inferred beliefs with
provenance. The same engine, second stream, zero new mechanisms.

**2. Explanation is provenance traversal.** An inferred belief carries
derived_from edges to its source beliefs and the script that fired.
"...because she kissed Mark" is not generated prose; it is a read of
the CAUSE label's provenance. NPCs can answer "why do you think that?"
truthfully about their own inference, by construction — auditability
as a gameplay feature.

**3. Truth was never claimed; salience was.** The accretion stance
(weights as evidence/salience, not probability of truth) scales to
social knowledge unchanged: belief weight = source confidence x trust
x script strength along the inference chain (semiring). Player lies
are adversarial input to the same pipeline; contradictions produce
superposed beliefs (primer's fork at knowledge timescale);
unrefreshed beliefs decay. Misinformation, gossip, and being wrong
for legible reasons are all emergent — and the audit trail shows
which trusted source poisoned which inference.

**4. The loop closes through generation and becomes testable.**
Say "Jack is angry at Mary" and "Mary kissed Mark" to an NPC; ask
why Jack is angry; the answer is mechanically checkable end-to-end
(parse -> believe -> infer -> explain -> generate). The round-trip
oracle extended through inference: testable NPC cognition.

**Lineage note:** the inference scripts are Schank scripts (1977) —
memory structures that drive inference and explanation — whose
program stalled on hand-authoring brittleness and all-or-nothing
matching. The two missing prerequisites were weighted accretion
(scripts emit evidence, not brittle conclusions) and a scalable
annotation source (LLM-as-annotator). Both now exist.

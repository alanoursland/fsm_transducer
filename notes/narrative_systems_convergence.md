# Convergence: the game's narrative system and this parser

The author imported brainstorming documents from a separate game
project (`brainstorming/narrative_system/` — NPCs performing
narratives the player can participate in, symbolic token
communication, an FST bridge to English). Those documents and this
project converged on the same architecture independently, from
opposite directions. This note records the mapping, because
independent convergence is the strongest evidence yet that the ideas
are natural attractors rather than artifacts of either project.

## The mapping

| game (generation side) | fsm_transducer (recognition side) |
|---|---|
| narrative FSMs: states = beats, transitions on sensors | story machines: states = expectations, transitions on story events |
| symbolic message (`ALERT Z_DANGER_WOLF LOC... CONF...`) | semantic frame (`{pred, agent, theme, conf}`) — primer's output |
| "the symbolic message is the canonical meaning representation" | the interlingua claim (story_machines.md addendum) |
| bridge direction (B): English → symbols → validated FSM | primer's pipeline, implemented |
| bridge direction (A): symbols → layered annotation → English | the unbuilt generation half |
| "each layer annotates tokens... until full English emerges" | the accretion architecture, named verbatim by the other project |
| confidence × trust modulation | semiring path-weight multiplication |
| beliefs with source/confidence/timestamp | labels with provenance and weight |
| sensors emitting Z_TOKENS | tier-1 adapters emitting story-event labels |
| protocol/narrative FSMs | tier-2 story machines |
| actions and belief updates | tier-3 consequences/emitters |
| social graph (who relates how to whom) | who's-on-stage discourse state (imp scope checkers; primer v2 anaphora) |

Propp closes the loop: the game runs the morphology of the folktale
forward (perform the story); the parser runs it backward (recognize
the story). One machine class, two modes — recognition/generation
duality, which is also exactly what an FST is for.

## Where the game docs need this project

The symbolic-communication doc claims determinism ("no parsing trees,
no probabilistic NLP") — true for NPC↔NPC because the game controls
the language. The bridge doc's player-input direction breaks the
assumption: players do not type controlled English. That is precisely
the regime where primer's machinery becomes necessary:

* weighted forks for genuine ambiguity in player input;
* graceful degradation (a malformed player sentence yields fewer
  frames and an eager-label record, never a crash — and never a
  failed quest trigger with no diagnostic);
* the eager/confirmed split as the game's record of "what the NPC
  considered the player to mean" vs "what it committed to" — which is
  dramatic material in itself (misunderstanding as gameplay).

The bridge doc wants "deterministic, testable, explainable, no giant
LLM as a core dependency" — this project's mission statement, stated
independently. fsm_transducer IS the bridge component that doc
wishes for.

## Where this project gains from the game

1. **The generation direction.** Direction (A) — frames → English —
   is the parser's machinery run backward, and the engine is closer
   to it than it looks: emission templates already interpolate;
   linearization FSTs over frames are story machines whose alphabet
   is frame slots. Building it would make the languages folder
   bidirectional, and the game is a motivated consumer.
2. **Discourse state at world scale.** The social-state doc
   (relationship graph, memory snippets, roles) is the entity store
   that primer v2 anaphora needs in miniature. Designing the sentence-
   scale version with the world-scale version in view avoids a
   too-small abstraction.
3. **A live testbed with an oracle.** The oracle cliff (no eval for
   English) is partially circumvented in the game: a player message
   has a ground-truth intent in the game state, and a round trip
   (frame → English → frame) is mechanically checkable. Generation +
   parsing together restore a differential-testing loop that NL alone
   cannot provide: **round-trip through English as the oracle.**
4. **Weights with consequences.** Trust-modulated belief confidence
   gives the weight algebra a job beyond parsing: the same semiring
   that merges parse paths propagates believability through a social
   graph. One algebra, two uses, already designed.

## Recorded next steps (when the projects formally meet)

* a `languages/primer/` generation module: frames → primer English
  via linearization story machines (direction A);
* round-trip tests: frame → English → frame == identity (the new
  oracle);
* a shared frame schema between the game's message types and primer's
  frames (ALERT/REQUEST/SHARE_OBS are pred classes; LOCATION_* and
  CONF_* are frame slots);
* the game's protocol FSMs re-expressed as language definitions in
  the `languages/` format — they are languages, and the folder format
  was built for exactly this.

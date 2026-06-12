# Language definition: early-reader English ("primer")

The eighth language and the first natural one. Corpus model:
early-reader primer texts ("See Spot run.", "Run, Spot, run!",
"Dick and Jane play.", "The ball is red."). Words are tokens;
vocabulary is ~25 words; sentences end at `.` `!` `?`.

## Why this is not language number eight of the same kind

Everything before this dissolved its ambiguities with deterministic
story state, because formal languages are designed to be parseable.
Primer English is where that stops:

```text
Play.            # 'play' is a verb: imperative, play{agent: you}
Play is fun.     # 'play' is a noun: subject of a copula
```

At the token `Play`, **two stories are genuinely live**. No left
context exists to consult; the disambiguating evidence (`is` vs `.`)
has not arrived yet. This is the two-stories experiment the project
has owed since the story-machines note: the clause story machine
**forks**, both narrative states persist as weighted paths, both emit
eager story labels into the bag, and later tokens kill one path.

* **Weighted lexicon** — the first weighted labels in any runner:
  `play` carries V:0.55 / N:0.45; names carry N:1.0.
* **Nondeterministic weighted story machine** — the first anchored
  machine to use the engine's NFA path semantics and semiring weights
  (idle since they were built): the S0 fork has two transitions with
  prior weights, and the frontier carries both stories.
* **Eager vs confirmed emissions** — the accretion thesis exercised:
  every path emits `STORY:*` and role labels eagerly (with path
  weight) as it consumes; only paths that reach the sentence-final
  punctuation emit the EXEC frame ops, via capture-anchored accept
  emissions. A dead story's eager labels remain in the field at their
  fork weight — fading evidence, never retracted — but contribute no
  program. The field records what was considered; the program records
  what survived.

## Output: semantic frames

The instruction set is the series' story-serialization vocabulary
applied to events: `ENT(spot)` (an entity enters the stage),
`EVT(run)` (a frame opens), `AGENT`/`THEME` (an element completes into
its frame — JSON's SETK pattern), `ATTR(red)`, `GROUP` (coordination),
`IMPYOU` (the imperative's implicit addressee), `END` (frame completes
to output). `See Spot run.` compiles to a frame with an embedded
frame: `see{agent: you, theme: run{agent: spot}}` — the raising
construction, handled by the same stack discipline as JSON's nested
containers.

## Grammar (clause shapes the story machine accepts)

* Imperative: `V (NP) (V)? .` — "Run.", "See the ball.", "See Spot run."
* Vocative imperative: `V , Name , V !` — "Run, Spot, run!" (the
  vocative names the addressee: agent = Spot, not you)
* Declarative: `NP V (NP) (V)? .` — "Spot runs.", "Spot sees the
  ball.", "Sally sees Spot run."
* Coordination: `Name and Name V .` — "Dick and Jane play."
* Copula: `NP is ADJ .` — "The ball is red.", "Play is fun."

NP = Name | Pronoun | DET N. A sentence matching no shape produces
**no frame and no error exit**: its eager labels stand in the field as
the record of every story that was tried — graceful degradation in its
NL form ("a quarter of real inputs are fragmentary"; the parser keeps
narrating).

## The oracle cliff (read PERSPECTIVE.md)

Every previous language had an external oracle (eval, json.loads, real
Python, imp itself). English has none. Validation here is
hand-validated goldens only, and that is a permanent feature of the
domain, not a v1 gap — the recorded path to scale is LLM-as-annotator
(judgments, not rules) with human-validated samples, per the session
notes that started this project arc.

## Files

Standard set. Runner: `fsm_parser.primer_lang`. Tests:
`src/tests/test_primer_lang.py`.

## Deliberate exclusions

Plural agreement checking, tense, questions, pronouns as objects,
adverbs ("Run fast."), PP attachment ("Look at Spot" — the *next*
ambiguity class, deferred so the fork experiment stays clean),
reading lexicon priors from label weights (transitions carry static
prior weights; weight-coupled transitions are a recorded engine
extension).

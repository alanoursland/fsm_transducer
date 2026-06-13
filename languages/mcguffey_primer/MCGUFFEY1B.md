# mcguffey1b — the grammar/semantics layer

`mcguffey1b` is the same tier-1 McGuffey Primer model as `mcguffey1`,
plus one new layer in the stack. It does not touch the clause story
machine, the lexicon, or the frame VM. It adds a block on top.

## Why a letter, not `mcguffey2`

The mcguffey numbers track the **reader / grade tier** of the dataset
(the Steele "grow a language per dataset" protocol): `mcguffey1` is the
Primer; `mcguffey2` is reserved for the *First Reader* corpus, grown on
top of this one. This model is the **same Primer dataset** with more
rules — a revision within the tier — so it takes a revision letter,
`1b`. That keeps the grade-level scheme intact (Primer ≈ kindergarten;
First Reader ≈ grade 1; and so on) and leaves `mcguffey2` meaning what
it should.

## The transformer framing

The architecture is a glass-box mirror of a transformer: the **label
bag is the residual stream**, and each FSM is a **block** that reads the
stream and writes new labels back. Stacking blocks is how meaning
accretes.

- `mcguffey1` is the **syntactic block**: it reads tokens, accretes
  constituent labels (`EXEC.*`), and projects a **frame** — the state
  the residual stream has reached after one block.
- `mcguffey1b` adds the **selectional/agreement block**: it reads that
  frame and applies the grammar of the world. In **analysis** it writes
  one bit (well-formed or not) and gates the parse. In **generation**
  the *same* block runs forward and re-weights the next-token field, so
  the syntactic block never gets to propose a sentence the semantic
  block would veto.

This is the project's parser/LM duality, one level up: a single
declarative layer that is both the analyzer and the generator's brake.

## The rules, and their classical grounding

All checks are the textbook inventory, applied to the projected frame
(features live in `features.yaml`, an overlay; `lexicon.yaml` is
untouched so `mcguffey1` is byte-for-byte unchanged).

| Check | Classical source | Example it kills |
|---|---|---|
| **Valency / subcategorization** | Tesnière 1959 (valence); Fillmore 1968 (case frames) | "Loves." (transitive, no theme); "Schoolhouse eat" intransitive given a theme |
| **Selectional restriction** | Katz & Fodor 1963 (semantic markers); Wilks 1975 (preference semantics) | "Schoolhouse eat." (inanimate agent of an agentive verb) |
| **Complementation class** | control/raising; perception-verb complements | "Think frog stand." (bare-inf clause under a non-licensor; only see/hear/watch/let/made license it) |
| **Agreement + verb form** | GPSG/HPSG feature checking, done on frames not by unification | "Walks John watch." (3sg verb, imperative needs base); "Seen horse show." (participle as finite matrix verb) |
| **Bare-NP / determination** | Quirk et al. (count-noun NP needs a determiner) | "Come like neck." (bare singular count noun) |

Preferences are **per-verb relaxable** (`agent_any`, `bare_ok`,
`control`), not a global hard type system — Wilks-style preference, not
Montague-style typing. The frame critic recurses into embedded clauses
(perception complements) with the finiteness checks switched off.

## Results

Against the author's salad corpus (30 strings that `mcguffey1` happily
parsed):

```
Come cap by way. Schoolhouse eat. Let neck rocks. Walks John watch. ...
```

- **29 / 30 rejected** by `mcguffey1b` (the survivor, "Fall on it.", is
  a legitimate intransitive imperative — correctly kept).
- Real-corpus coverage: `mcguffey1` parses **144/220 (65.5%)**;
  `mcguffey1b` keeps **140/144 (~97%)** of those. Precision rises,
  recall barely moves. The four it drops are parser artifacts
  (`run`-as-its-own-agent, a surname compound), logged below.

## Generation: the brake steers, it does not merely judge

`python -m fsm_parser mcguffey1b 12 --seed 100 -t 0.8`

The autoregressive sampler is `mcguffey1`'s, with two hooks:

1. **`reweight(prefix, dist)`** — before each token is sampled, the
   layer recovers, from each frontier path's transition captures, which
   register the candidate would fill and which subject the path has
   already seen, then drops candidates that would commit an
   agreement/selection/determination violation. The strongest brake is
   on the **punctuation** step: a sentence may only end when the
   completed frame passes the full critic, which folds the
   end-of-sentence valency check into generation. On a dead end the
   field returns empty and the sampler rejects the prefix outright —
   **the brake never lets a violation out** (verified: 22/22 emitted
   sentences critic-clean over 300 samples).
2. **`accept(text, frames)`** — the same critic as a final gate.

Side-by-side, same seed:

```
brakes OFF (mcguffey1):  Drives I eat. Wolf went she. Sat Jane of set.
brakes ON  (mcguffey1b): Eat Rab. Men like they. Let Sally kill. Drown for sheep.
```

What survives is **grammatical and selectionally sane, but not yet
pragmatic** — "Cool as dolls." is well-formed and means nothing. That
gap (world knowledge, discourse coherence, entity continuity across the
sentence-reset) is the next block up: the REF/centering story machine,
which would re-weight this same field rather than replace it.

### A real property: cold fields starve the brakes

The brakes shrink the acceptable region, so the sampler needs to
**explore** to hit it. At low temperature the next-token field collapses
onto a few high-weight words (often function words that dead-end), and
yield craters — empirically ~0 acceptable sentences in 400 samples at
`t=0.7`, rising to near-certain at `t=1.0`. So with the brakes engaged,
keep `temperature >= ~0.8`. This is the symbolic mirror of a familiar
LLM fact: tightly constrained decoding needs enough entropy to find the
feasible region. `max_tries` defaults to 1500 for the same reason.

## Known false rejections (the ledger)

Four corpus sentences `mcguffey1` parsed are dropped by the critic, all
traceable to upstream parser quirks, not the rules themselves:

- `Our cows do not run off.` / `The ship has run on a rock.` — the
  parser emits `{'pred':'run','agent':'run'}` (the embedded verb becomes
  its own agent); the animacy/licensing checks then fire on the bad
  frame. Fix belongs in the do-support / perfect-auxiliary handling
  upstream.
- `A good child likes to go to school.` — `to school` is read as the
  theme of `likes`, so the to-infinitive purpose clause is lost.
- `One day John went to the pond to fish.` — `went` (intransitive) gets
  a purpose-infinitive `to fish` that the valency check counts as a
  theme.

These are recorded rather than patched away: they mark exactly where the
syntactic block under this one still needs work (the to-infinitive /
preposition ambiguity, a classical chestnut), and the round-trip oracle
will keep them visible.

## Linguistic-audit pass: case, patient selection, frame closure

A second round of corrections (the `CORRECTIONS_REQUESTED.md` audit of
generated text) added four checks, each a textbook construct, each
verified to reject the observed string while leaving corpus coverage at
140/144:

| Observed leak | New check | Grounding |
|---|---|---|
| `Ran at he?` | **Case** — agent nominative, theme/prep-object accusative (`CASE:ACC_POBJ` etc.) | morphological case; nom/acc pronoun sets in `features.yaml` |
| `Drown eyes for hands.` | **Patient selection** — `theme_animate` verbs (drown/kill/feed/pet/save) need a living theme (`SEL:ANIMATE_THEME`) | Levin verbs of killing/caring; narrow per-verb, not a global animate-theme rule |
| `Fish noise from me.` | `fish` reclassified **intransitive** → `VAL:NO_THEME` | lexical valency (tier-1 `fish` is "to fish") |
| `Made Dick have?` | **Frame closure for have** — a main-verb have/has/had needs a following participle (perfect aux) or NP (object); `VAL:HAVE_NEEDS_COMPLEMENT` | Tesnière valency, surface-checked because perfect-`have` and possessive-`have` collapse at frame level |

The interesting one is **case, and why it had to become finiteness-
sensitive.** The first cut required every agent to be nominative — and
the corpus immediately broke it with *"They will not let them drown."*
"let **them** drown" is **ECM** (exceptional case marking): the subject
of a perception/causative complement takes accusative case, assigned by
the higher verb (`let`, `made`, `see`), not nominative. So the agent
rule flips with finiteness: a matrix subject is nominative
(`CASE:NOM_SUBJECT`), an embedded ECM subject is accusative
(`CASE:ACC_ECM_SUBJECT` fires on "Let *they* drown"). The round-trip
against the real corpus is what surfaced the ECM case — the same way it
keeps surfacing parser mixtures. The brake is also wired into the
generator (subject registers reject accusative pronouns, object/prep
registers reject nominative ones), so "Dress **him**" is sampled and
"at **he**" is not.

## The question-heaviness bug (and what it revealed)

Early `mcguffey1b` generation came out ~57% questions, against ~1% for
brakes-off `mcguffey1` — so the brakes were the cause, not the grammar.
The mechanism was an **asymmetry the critic created and the punctuation
gate amplified**:

- The generator constantly produces subjectless clauses; the parser
  reads the dropped subject as `agent: "you"` — an imperative.
- The critic treats `imperative = (agent == "you" and mood != "q")` and
  requires imperatives to be base-form. So a past-tense subjectless
  clause ("Ran") is vetoed as a statement ("Ran." = bad imperative).
- Flip the punctuation to "?" and `mood == "q"`: it is no longer an
  imperative, the base-form and agreement checks switch off, and "Ran?"
  comes out clean.
- The punctuation gate checks "." and "?" independently, so when the
  statement ending is vetoed and the question ending passes, the sampler
  is *forced* to emit a question. "?" became the escape hatch for clauses
  that can't be well-formed statements.

The root cause was that interrogative mood was too lenient — treated as
a free pass. Tier-1 questions are formed by **inversion** (fronting a
modal, do-support auxiliary, copula, or wh-word), not by intonation, so
`q_inversion_violations` now requires one of those licensers (surface-
checked, because do-support is absorbed: "Do you see the cat?" projects
the same frame as a bare clause). With the loophole closed the question
rate fell to ~8% and corpus coverage held at 140/144. The episode is a
clean instance of the project's thesis in miniature: a generation
statistic (too many questions) was a precise, debuggable symptom of a
missing grammatical constraint, found because the model is a glass box.

## Second generated-corpus audit: morphology, the DP, predication, weather verbs

A later generation pass surfaced six more issues, each a named construct
from classical linguistics. All reject the observed string with corpus
coverage held at 140/144.

| Observed | Check | Classical account |
|---|---|---|
| `An cow.` | a/an allomorphy (`DET:AN_BEFORE_CONSONANT`) | **morphophonemic allomorphy**: the indefinite article's realization is conditioned by the phonological onset of the following word (the textbook allomorphy example; finite-state two-level morphology, Koskenniemi 1983). |
| `Please the for goats.` | unsaturated determiner (`DET:NO_NOMINAL_HEAD`) | **DP / X-bar**: a determiner is the head/specifier that selects a nominal complement (Abney 1987); a headless article is an incomplete projection. Restricted to the true articles the/a/an, since demonstratives and quantifiers (this/that/all/more) double as pronouns and stand alone. |
| `Is in you to birds?` | copula predication (`PRED:COPULA_NO_ARGUMENTS`) | **predication / copula subcategorization**: BE links a subject to a predicative complement (Fillmore case frame); a clause with neither is not a predication. Existential *there* (where the pivot may not project into the frame) is exempted on the surface. |
| `Did of Nat on slates?` | stranded do-support (`VAL:DO_STRANDED`) | **do-support** (Chomsky 1957, affix-hopping): *do* is inserted to carry tense only when there is a verb to support; an interrogative *did* with no lexical verb is a stranded auxiliary. |
| `Snow sheep in eggs.` | avalent weather verb (`VAL:NO_THEME`) | **weather/impersonal verbs**: meteorological predicates are avalent (Tesnière) — no thematic agent or object, only an expletive subject. *snow* reclassified intransitive. |
| `Put God.` | obligatory locative (`VAL:PUT_NEEDS_LOCATION`) | **put-class subcategorization** (Levin 9.1): put-verbs obligatorily take a directional/locative PP (*put God / put God on the mat). |

## Generation performance

Generation was `support()`-bound: scoring each token swept every
frontier path × every transition × the whole vocabulary, re-evaluating
the condition tree — ~100M `support` calls for 10 sentences (99 of 130
profiled seconds). Conditions and the vocabulary are both fixed, so
`cond_support(condition)` (the candidate set of a condition: words with
nonzero support) is memoized once per distinct condition, collapsing the
sweep to a dict lookup. **30 sentences went from ~66s to ~12s (~6×)**,
output byte-identical. The frame-build in the punctuation brake (O(L) per
step, still run every step) is now the next ceiling — an incremental VM
would lift it.

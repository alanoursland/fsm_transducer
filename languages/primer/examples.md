# Worked examples (hand-validated)

There is no external oracle for English; these tables ARE the
specification of correct behavior (test-transcribed in
test_primer_lang.py).

## A. The two-stories pair (the experiment)

**`Play.`** → `[{pred: play, agent: you}]`
**`Play is fun.`** → `[{pred: is, agent: play, attr: fun}]`

In BOTH sentences, token:0 carries the eager superposition:
`STORY:IMP 0.55`, `STORY:DECL 0.45` — recorded at the fork, never
retracted. The confirmed EXEC labels differ entirely:

| | `Play.` | `Play is fun.` |
|---|---|---|
| survivor | imperative (0.55) | subject story (0.45) |
| confirmed on `Play` | IMPYOU, EVT, AGENT | ENT |
| the dead story left | STORY:DECL 0.45, nothing else | STORY:IMP 0.55, nothing else |

The field records what was considered; the program records what
survived. Note the second case: the LOWER-prior story won, decided by
evidence (`is`), not by the prior — which is the entire point of
carrying both.

## B. Raising: `See Spot run.`

`IMPYOU; EVT see; AGENT; ENT spot; EVT run; AGENT; THEME; END` →
`{pred: see, agent: you, theme: {pred: run, agent: spot}}` — Spot is
the matrix object AND the embedded agent, handled by the same stack
discipline as JSON's nested containers. ✓

## C. Declaratives, coordination, copula

`Spot sees the ball.` → `{pred: sees, agent: spot, theme: ball}` ✓
`Dick and Jane play.` → `{pred: play, agent: [dick, jane]}` (GROUP) ✓
`The ball is red.` → `{pred: is, agent: ball, attr: red}` ✓

## D. Vocative: `Run, Spot, run!`

The vocative names the addressee: `{pred: run, agent: spot}` — not
`you`. (The polymorphic AGENT op: the entity arrives after the frame.) ✓

## E. A real primer page

`See Spot. See Spot run. Run, Spot, run!` → three frames, escalating
exactly as the primer intends: see(you, spot); see(you, run(spot));
run(spot). ✓

## F. Graceful degradation

`Ball the see.` → zero frames, no exception; the field keeps the eager
STORY:DECL trail of the story that was tried. `Ball the see. Spot
runs.` → the bad sentence does not strand the good one (per-sentence
anchoring). ✓

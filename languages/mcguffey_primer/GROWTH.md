# Growth record (the Steele protocol, instrumented)

| iteration | coverage | added |
|---|---|---|
| seed grammar + tier-1 lexicon | 54.5% | NP layer, PPs, modals, questions, fragments, coordination |
| 2 (failure-driven) | 60.9% | do-imperatives, predicate possessives, noun compounds, appositives, wh-NP, subject-sharing VPs |
| 3 (failure-driven) | 65.5%* | clause-B negation, sentence-initial PPs, embedded-NP material; plausibility-structured FRAG variants |

*65.9% peaked mid-iteration; 0.4 points were deliberately returned to
restore two seed goldens (the growth invariant outranks coverage).

## The finding that matters more than the number

Several remaining failures (and both seed regressions during growth)
share one cause: **two weighted readings survive to the period and the
per-slot argmax projection mixes them into an incoherent program**
("Can this old fox catch the hen?"; "Play." as imperative vs caption;
"Run, Spot, run!" vs appositive-plus-verb). These are genuine
ambiguities — the grammar is right to fork — but projection must
select a COHERENT STORY, not per-slot winners. Interim mitigation:
plausibility encoded in state structure (fragments require a
determiner or coordination; appositives cannot start from
possibly-verbal subjects). The real fix is engine-level
story-coherent projection (group confirmed emissions by surviving
path; argmax over whole stories), which is now the architecture's
top open problem — surfaced not by theory but by McGuffey lesson 40.

## Error-ledger entries from this growth

* index captures vs slot_id captures in emission templates (positional
  species, again);
* `stack[-2][k] = stack.pop()` evaluation-order bug (positional);
* YAML 1.1 booleans (`on`/`no`/`yes`/`off` as bare keys) — the JSON
  language documented this exact hazard and it recurred anyway:
  lesson-not-transferred, a new species;
* the superset-emission trick has a boundary: a register that plays
  different roles depending on later structure (obj as matrix theme vs
  embedded agent) forces the accept sets to split.

## mcguffey1b — a second block in the stack (same tier)

Not a tier (mcguffey2 stays reserved for the First Reader); a model
revision on the *same* Primer dataset that adds one layer: a
selectional/agreement block reading the projected frame. mcguffey1
ratcheted recall (65.5% coverage); 1b ratchets precision — it rejects
29/30 of the author's salad corpus while keeping ~97% of mcguffey1's
real-corpus parses. Rules are the classical inventory (valency
Tesnière/Fillmore, selection Katz-Fodor/Wilks, agreement GPSG/HPSG,
bare-NP Quirk). See MCGUFFEY1B.md. The same block runs forward as a
generation brake (`reweight`), so violations are never sampled.

### Error-ledger entries from 1b

* **Cold fields starve constrained decoding.** With the brakes engaged
  the acceptable region is small; at low temperature the next-token
  field collapses onto a few high-weight dead-end words and generation
  yield drops to ~0 (400 samples, t=0.7), recovering at t≈1.0. The
  symbolic mirror of the LLM fact that tight constraints need decoding
  entropy. Mitigation: temperature ≥ ~0.8, max_tries=1500.
* **`run`-as-its-own-agent** surfaced again here: do-support/perfect
  frames (`{'pred':'run','agent':'run'}`) make the new animacy check
  fire on a malformed frame. Logged in MCGUFFEY1B.md; fix belongs
  upstream in the syntactic block.

## Next

Tier 2 (`mcguffey_first_reader`, 381 sentences, 513 words) grows on
this language; before it, story-coherent projection — the mixture
problem will only compound with richer grammar.

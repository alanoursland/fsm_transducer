# Language: McGuffey Primer (tier 1)

The first GROWN language (Guy Steele, "Growing a Language": design
small, with the means for growth; the McGuffey readers are the same
protocol run for children — "only about six new words per lesson").
Seed: `languages/primer/`. Corpus: the real McGuffey Eclectic Primer
(`data/early_reader/sentences/mcguffey_primer.txt`, 220 sentences,
288 words).

**The growth invariant, enforced as a test:** every sentence the seed
parses must still parse here, with the same frames. Growth never
loses ground.

## Grown constructions (over the seed)

NP-internal structure (DET/ADJ/POSS/NUM skipped to heads), noun-noun
compounds, prepositional phrases (two deep, plus sentence-initial),
modals, do-support and do-imperatives, negation, yes/no questions via
inversion that funnels back into the declarative spine, wh- and
wh-NP questions, NP fragments ("A cat and a rat."), predicate
nominals and possessives, existential 'there', appositives, clause
coordination (comma-conj and semicolon), object coordination, and
subject-sharing second VPs — each added in failure-driven iterations
against the corpus (see GROWTH.md), never by redesign.

## Current measurement

**65.5% of the real McGuffey Primer parses to well-formed frames**
(144/220; ratchet test holds the floor at 65%). Coverage by corpus
order: 100% 100% 91% 77% 73% 64% 55% 14% 41% 41% — the curve IS the
book's difficulty escalation.

## Files

`lexicon.yaml` — all 288 corpus words plus the seed vocabulary,
tagged by LLM-as-annotator (silver; spot-check per the oracle-cliff
discipline). Runner: `fsm_parser.mcguffey1_lang`. Tests:
`src/tests/test_mcguffey1_lang.py`. Measurement:
`data/early_reader/measure_coverage.py`.

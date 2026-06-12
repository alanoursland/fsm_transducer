# After the Oracle Cliff: Differential Testing for Languages With No Ground Truth

**Target venue:** arXiv first; NLP-OSS / eval workshops; possibly a
CoNLL short. Methods paper born from a real boundary hit by this
project.

## Core claim

Seven formal languages in this project were validated by merciless
external oracles (eval, json.loads, the real Python interpreter,
round-trip identity, a sibling implementation). Natural language has
none: "see(you, run(spot))" is correct because a human says so. We
chart the practical responses, in increasing strength: (1)
hand-validated golden suites (implemented; honest but unscalable);
(2) round-trip oracles — build generation (frames -> English) alongside
parsing and test frame -> text -> frame identity, restoring a
mechanical oracle for the fragment where generation is deterministic;
(3) LLM-as-annotator distillation: elicit *judgments* (labels,
acceptability, frames) rather than rules from a large model, with
human-validated samples and consistency checks, converting an opaque
model's competence into a transparent model's training targets — and
the epistemics that requires (annotator bias becomes gold; report
agreement, calibrate, version the annotator).

## What exists

The full oracle-rich series as the baseline discipline; the English
fragment at the cliff edge; the early-reader corpus (~2,000
public-domain sentences, four difficulty tiers) as the testbed; the
generation direction specified.

## Experiments needed

1. Build generation for the primer fragment; measure round-trip
   identity rates and what they catch (seeded mutations).
2. LLM-annotate tier 1-2 of the corpus with frames; measure
   model-human agreement on a validated sample; train/fit the symbolic
   parser's weights against the annotations; report coverage gains vs
   hand-authoring.

## Related work

Differential testing (McKeeman); metamorphic testing; LLM-as-judge
literature and its calibration critiques; weak supervision (Snorkel);
classic semantic-parsing datasets built by hand (GeoQuery) vs elicited.

# Paper ideas

Proposals based on this repository (and its sibling, regex_transformer).
Each file states the core claim, what already exists, the experiments
still needed, related work, and honest risks. Ordered here by
readiness, not importance.

| # | title (short) | venue tier | new work needed |
|---|---|---|---|
| 02 | Story-state dissolves ambiguity (7-language study) | SLE / Onward! | packaging + tables |
| 06 | Resource-budgeted parsing with certificates | CIAA / FSMNLP | theorem-tightening |
| 08 | Audited human-LLM co-design method + error taxonomy | arXiv -> ICSE/CHI | retrospective coding |
| 01 | Parsing as accretion (architecture statement) | arXiv / *SEM wksp | corpus eval |
| 07 | After the oracle cliff (round-trip + LLM-annotator) | arXiv / eval wksp | generation dir + annotation study |
| 04 | FSMs as agent memory | AIIDE / FDG | scenario + consolidation study |
| 05 | Explanation as provenance traversal (NPCs) | AIIDE / CHI PLAY | belief stream + demo |
| 03 | Glass-box mirror for transformer interpretability | BlackboxNLP -> NeurIPS/ICLR | training + probing + interventions |
| 09 | Recognizing the moral of the story | CMN / arXiv | grammar scale-up + arc machines |
| 10 | Compiling FSM cascades into attention (delta->QKV) | BlackboxNLP -> main | compiler + capacity + attractor-distance |

Sensible sequencing: 02 and 06 are mostly written already (the repo's
language definitions and PERSPECTIVE documents contain the content);
08 requires only retrospective analysis of the public record; 01
anchors the others; 07 unblocks 09; 03 is the flagship scientific bet
and can proceed in parallel (10 is its constructive prerequisite and
shares its infrastructure — see references/prior_work_review.md for
the three-leg program); 04+05 are one strong games paper if
merged.

A note on authorship and provenance: this repository was built in
human-LLM working sessions (the human author originated the ideas and
direction; see the PERSPECTIVE.md files for the audited division of
labor). Papers should disclose the methodology — proposal 08 makes it
the subject.

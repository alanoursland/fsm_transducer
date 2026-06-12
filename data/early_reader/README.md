# Early-reader dataset

Primer-register English sentences for building up the early-reader
language model (`languages/primer/`). ~2,000 sentences, ~2,000-word
vocabulary, in four difficulty tiers.

The actual "See Spot run" books (Dick and Jane, Scott Foresman) are
still under copyright. These are their public-domain ancestors —
the same register, the same pedagogy (tiny vocabulary, few new words
per lesson, heavy repetition), from Project Gutenberg.

## Sources (all public domain, via Project Gutenberg)

| tier | file | source | PG # |
|---|---|---|---|
| 1 | `sentences/mcguffey_primer.txt` | McGuffey's Eclectic Primer, Rev. Ed. | 14642 |
| 2 | `sentences/mcguffey_first_reader.txt` | McGuffey's First Eclectic Reader, Rev. Ed. | 14640 |
| 3 | `sentences/beacon_second_reader.txt` | The Beacon Second Reader (folk tales) | 15659 |
| 4 | `sentences/fifty_famous_stories.txt` | Fifty Famous Stories Retold (Baldwin) | 18442 |

Tier 1 is the parser's immediate target ("A cat and a rat.", "The
dog ran.", "Can Ann fan the lad?"); tiers 3–4 are folk-tale narrative
("The Shoemaker and the Elves", "King Alfred and the Cakes") — real
*stories* for the story machines, with dialogue, sequence, and cause.

## Files

- `raw/` — unmodified Project Gutenberg texts (provenance)
- `build_dataset.py` — reproducible extraction (run from this dir)
- `sentences/<source>.txt` — one cleaned sentence per line, source order
  preserved (order matters: primers escalate difficulty, and
  consecutive sentences form discourse)
- `sentences/combined.txt` — all sources, deduplicated
- `vocabulary.txt` — `word<TAB>count`, descending
- `STATS.txt` — per-source counts

## Extraction rules (see build_dataset.py)

Gutenberg boilerplate stripped; everything before each book's first
lesson/story discarded; illustrations, lesson headers, word lists,
ALL-CAPS headings, attribution lines dropped; sentences kept only if
2–12 words, clean character set, capitalized start, terminal `.!?`;
pedagogical syllabification de-hyphenated (`ex-act-ly` → `exactly`);
period spellings kept (`to-morrow`, `good-by`); meta-sentences about
the book itself removed; deduplicated case-insensitively.

## Known characteristics

- Period vocabulary and style (1880s–1910s): `Ann`, `Nat`, `lad`,
  `slate`, `oh`, `said` — fine for our purpose, worth knowing.
- Sentence-per-line loses paragraph grouping; the per-source files
  preserve order, so adjacent lines are usually discourse-adjacent
  (useful later for anaphora work).
- Tier 1 has heavy structural repetition by design — that is the
  pedagogy, and it is also ideal grammar-induction data.

## Licensing

The underlying texts are in the public domain in the United States.
The raw files retain their Project Gutenberg headers and license; the
extracted sentence files contain only the public-domain text. If this
dataset is redistributed outside this repository, follow the Project
Gutenberg license in the raw files (or strip the PG trademark per its
terms).

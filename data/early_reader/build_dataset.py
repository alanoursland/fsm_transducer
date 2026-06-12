"""Build the early-reader sentence dataset from raw Project Gutenberg texts.

Reproducible: raw/ holds the unmodified PG files; this script extracts
clean primer-register sentences into sentences/, plus a combined file,
a vocabulary list, and stats. Run from this directory:

    python build_dataset.py
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
RAW = HERE / "raw"
OUT = HERE / "sentences"

# (filename, start_marker): content before the marker (prefaces, tables
# of contents, PG credits) is discarded.
SOURCES = {
    "mcguffey_primer": ("mcguffey_primer.txt", "Lesson 1"),
    "mcguffey_first_reader": ("mcguffey_first_reader.txt", "LESSON I."),
    "beacon_second_reader": ("beacon_second_reader.txt", "THE SHOEMAKER AND THE ELVES"),
    "fifty_famous_stories": ("fifty_famous_stories.txt", "KING ALFRED AND THE CAKES"),
}

MAX_WORDS = 12          # early-reader sentence cap
_WORD = re.compile(r"[A-Za-z]+(?:'[a-z]+)?")
_SENT_OK = re.compile(r"^[A-Z\"'].*[.!?]$")
_BAD_CHARS = re.compile(r"[0-9_*\[\]()=/\\{}#@%&+<>|~^]")


def strip_gutenberg(text: str) -> str:
    start = re.search(r"\*\*\* START OF .*? \*\*\*", text)
    end = re.search(r"\*\*\* END OF .*? \*\*\*", text)
    return text[start.end() if start else 0 : end.start() if end else len(text)]


def clean_lines(text: str) -> str:
    """Drop illustrations, lesson headers, word lists, page furniture."""
    out = []
    skip_bracket = 0
    for line in text.split("\n"):
        s = line.strip()
        if skip_bracket:
            skip_bracket = 0 if "]" in s else 1
            continue
        if s.startswith("["):
            skip_bracket = 0 if "]" in s else 1
            continue
        # lesson headers, all-caps titles, roman numerals, attribution lines
        if re.fullmatch(r"(LESSON|Lesson)\b.*", s):
            continue
        if s and s == s.upper() and len(_WORD.findall(s)) >= 1:
            continue  # ALL-CAPS heading
        if re.fullmatch(r"[ivxlcIVXLC]+\.?", s):
            continue
        if s.startswith("_") or s.endswith("_"):
            continue  # italic attribution/stage lines
        out.append(line)
    return "\n".join(out)


def sentences_from(text: str) -> list[str]:
    """Paragraph-join, then split into sentences and filter to register."""
    sents: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        flat = " ".join(para.split())
        if not flat:
            continue
        # split keeping terminal punctuation
        for raw in re.findall(r"[^.!?]*[.!?]", flat):
            s = raw.strip().strip('"').strip()
            s = re.sub(r"\s+", " ", s)
            if not s or _BAD_CHARS.search(s):
                continue
            if not _SENT_OK.match(s):
                continue
            words = _WORD.findall(s)
            if not (2 <= len(words) <= MAX_WORDS):
                continue
            # primer register: no mid-sentence colon/semicolon clutter kept;
            # allow comma, semicolon, apostrophe, hyphen, quotes already stripped
            if re.search(r"[^A-Za-z ,;:'’.!?-]", s):
                continue
            if re.search(r"\b(lesson|this book|reader|primer)\b", s, re.I):
                continue  # meta-sentences about the book itself
            # de-syllabify pedagogical hyphenation (ex-act-ly -> exactly);
            # single-hyphen compounds (to-morrow, good-by) are period
            # spellings and are kept
            s = re.sub(r"\b(\w+)-(\w+)-(\w+)(?:-(\w+))?\b",
                       lambda m: "".join(g for g in m.groups() if g), s)
            sents.append(s)
    # dedupe preserving order
    seen: set[str] = set()
    unique = []
    for s in sents:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


def main() -> None:
    OUT.mkdir(exist_ok=True)
    combined: list[str] = []
    vocab: Counter[str] = Counter()
    stats = []
    for name, (fname, start_marker) in SOURCES.items():
        text = strip_gutenberg((RAW / fname).read_text(errors="replace"))
        pos = text.find(start_marker)
        if pos >= 0:
            text = text[pos:]
        text = clean_lines(text)
        sents = sentences_from(text)
        (OUT / f"{name}.txt").write_text("\n".join(sents) + "\n")
        combined.extend(sents)
        for s in sents:
            vocab.update(w.lower() for w in _WORD.findall(s))
        lens = [len(_WORD.findall(s)) for s in sents]
        stats.append(
            f"{name}: {len(sents)} sentences, "
            f"mean length {sum(lens)/len(lens):.1f} words, "
            f"vocab {len({w.lower() for s in sents for w in _WORD.findall(s)})}"
        )
    # combined, deduped across sources
    seen: set[str] = set()
    unique = [s for s in combined if not (s.lower() in seen or seen.add(s.lower()))]
    (OUT / "combined.txt").write_text("\n".join(unique) + "\n")
    (HERE / "vocabulary.txt").write_text(
        "\n".join(f"{w}\t{c}" for w, c in vocab.most_common()) + "\n"
    )
    stats.append(f"combined: {len(unique)} sentences, vocabulary {len(vocab)} words")
    (HERE / "STATS.txt").write_text("\n".join(stats) + "\n")
    print("\n".join(stats))


if __name__ == "__main__":
    main()

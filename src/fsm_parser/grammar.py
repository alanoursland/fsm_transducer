"""A small hand-built grammar used by the CLI demo and tests.

It demonstrates contextual disambiguation: ``book`` is biased toward the
verb reading after ``can``, and toward the noun reading after ``the``.
"""

from __future__ import annotations

from fsm_parser.blocks import FSMBlock, LexicalBlock
from fsm_parser.combinators import concat, literal, star
from fsm_parser.fsm import (
    Capture,
    CaptureAnchor,
    Emission,
    HasAnyLabel,
    HasLabel,
    compile_linear,
)
from fsm_parser.pipeline import Parser, ParserConfig


def lexicon() -> LexicalBlock:
    entries = {
        "the": {"POS:DET": 1.0},
        "a": {"POS:DET": 1.0},
        "an": {"POS:DET": 1.0},
        "can": {"POS:AUX": 0.7, "POS:VERB": 0.2, "POS:NOUN": 0.1},
        "will": {"POS:AUX": 1.0},
        "may": {"POS:AUX": 1.0},
        "i": {"POS:PRON": 1.0},
        "you": {"POS:PRON": 1.0},
        "he": {"POS:PRON": 1.0},
        "she": {"POS:PRON": 1.0},
        "book": {"POS:NOUN": 0.55, "POS:VERB": 0.45},
        "books": {"POS:NOUN": 0.7, "POS:VERB": 0.3},
        "cat": {"POS:NOUN": 1.0},
        "dog": {"POS:NOUN": 1.0},
        "ball": {"POS:NOUN": 1.0},
        "flights": {"POS:NOUN": 1.0},
        "slept": {"POS:VERB": 1.0},
        "fell": {"POS:VERB": 1.0},
        "chased": {"POS:VERB": 1.0},
        "ran": {"POS:VERB": 1.0},
        ".": {"PUNCT:END": 1.0},
        ",": {"PUNCT:COMMA": 1.0},
        "?": {"PUNCT:END": 1.0},
        "!": {"PUNCT:END": 1.0},
    }
    return LexicalBlock(name="lexicon", entries=entries)


def context_block() -> FSMBlock:
    det_boost_noun = compile_linear(
        "det_boosts_next_noun",
        [HasLabel("POS:DET", 0.3), HasAnyLabel(("POS:NOUN", "POS:VERB"), 0.1)],
        [Emission(label="POS:NOUN", weight=0.5, offset=0)],
    )
    aux_boost_verb = compile_linear(
        "aux_boosts_next_verb",
        [HasLabel("POS:AUX", 0.3), HasAnyLabel(("POS:NOUN", "POS:VERB"), 0.1)],
        [Emission(label="POS:VERB", weight=0.5, offset=0)],
    )
    pron_boost_verb = compile_linear(
        "pron_then_aux_then_verb",
        [
            HasLabel("POS:PRON", 0.3),
            HasLabel("POS:AUX", 0.3),
            HasAnyLabel(("POS:NOUN", "POS:VERB"), 0.1),
        ],
        [Emission(label="POS:VERB", weight=0.4, offset=0)],
    )
    return FSMBlock(
        name="context",
        fsms=[det_boost_noun, aux_boost_verb, pron_boost_verb],
    )


def phrase_block() -> FSMBlock:
    # Built compositionally: optional adjectives, capture-anchored start label.
    np_det_noun = concat(
        literal(
            HasLabel("POS:DET", 0.3),
            captures=[Capture("det")],
        ),
        star(literal(HasLabel("POS:ADJ", 0.3))),
        literal(
            HasLabel("POS:NOUN", 0.3),
            captures=[Capture("head")],
            emissions=[
                Emission("PHRASE:NP_START", 0.7, anchor=CaptureAnchor("det")),
                Emission("PHRASE:NP_HEAD", 0.8),
                Emission("PHRASE:NP_END", 0.7),
            ],
        ),
        name="np_det_noun",
    )
    np_pron = literal(
        HasLabel("POS:PRON", 0.3),
        emissions=[
            Emission("PHRASE:NP_START", 0.6),
            Emission("PHRASE:NP_HEAD", 0.6),
            Emission("PHRASE:NP_END", 0.6),
        ],
        name="np_pron",
    )
    vp_verb = literal(
        HasLabel("POS:VERB", 0.3),
        emissions=[
            Emission("PHRASE:VP_HEAD", 0.7),
            Emission("ROLE:PREDICATE", 0.5),
        ],
        name="vp_verb",
    )
    return FSMBlock(name="phrases", fsms=[np_det_noun, np_pron, vp_verb])


def dependency_block() -> FSMBlock:
    """Emit pointer-style SUBJECT_OF labels using captures."""
    subject_of = concat(
        literal(HasLabel("PHRASE:NP_HEAD", 0.3), captures=[Capture("head")]),
        literal(
            HasLabel("PHRASE:VP_HEAD", 0.3),
            captures=[Capture("verb")],
            emissions=[
                Emission(
                    "DEP:nsubj:{verb}",
                    0.5,
                    anchor=CaptureAnchor("head"),
                ),
            ],
        ),
        name="subject_of",
    )
    return FSMBlock(name="dependencies", fsms=[subject_of])


def role_block() -> FSMBlock:
    subject_before_verb = compile_linear(
        "subject_before_verb",
        [HasLabel("PHRASE:NP_END", 0.3), HasLabel("PHRASE:VP_HEAD", 0.3)],
        [Emission(label="ROLE:SUBJECT_CANDIDATE", weight=0.6, offset=-1)],
    )
    object_after_verb = compile_linear(
        "object_after_verb",
        [HasLabel("PHRASE:VP_HEAD", 0.3), HasLabel("PHRASE:NP_HEAD", 0.3)],
        [Emission(label="ROLE:OBJECT_CANDIDATE", weight=0.6, offset=0)],
    )
    return FSMBlock(name="roles", fsms=[subject_before_verb, object_after_verb])


def build_default_parser() -> Parser:
    return Parser(
        layers=[
            [lexicon()],
            [context_block()],
            [phrase_block()],
            [role_block(), dependency_block()],
        ],
        config=ParserConfig(decay=0.95, min_weight=0.005, max_labels_per_token=32),
    )

"""Tests for CharClassBlock, SimpleCharToTokenReducer, ambiguous reducer."""

from fsm_parser import (
    AmbiguousShiftRightReducer,
    CharClassBlock,
    Parser,
    ParserConfig,
    SimpleCharToTokenReducer,
    initialize_char_state,
)
from fsm_parser.normalization import NormalizationConfig
from fsm_parser.slots import SourceSpan


def test_char_class_block_labels_letters_and_digits():
    state = initialize_char_state("a1+ ")
    deltas = CharClassBlock().apply(state)
    by_slot = {(d.slot_id, d.label) for d in deltas}
    assert ("char:0", "CHAR:LETTER") in by_slot
    assert ("char:1", "CHAR:DIGIT") in by_slot
    assert ("char:2", "CHAR:OPERATOR") in by_slot
    assert ("char:3", "CHAR:WHITESPACE") in by_slot


def test_char_to_token_reducer_creates_ident():
    state = initialize_char_state("foo")
    parser = Parser(layers=[[CharClassBlock()], [SimpleCharToTokenReducer()]])
    parser.parse_state(state)
    tokens = state.tokens
    assert len(tokens) == 1
    assert tokens[0].text == "foo"
    assert tokens[0].labels.get("TOKEN:IDENT") > 0
    # source span covers the three characters
    assert tokens[0].source_span == SourceSpan(0, 3)


def test_char_to_token_reducer_creates_number():
    state = initialize_char_state("123")
    Parser(layers=[[CharClassBlock()], [SimpleCharToTokenReducer()]]).parse_state(state)
    assert state.tokens[0].labels.get("TOKEN:NUMBER") > 0


def test_char_to_token_reducer_creates_operators():
    state = initialize_char_state("foo + 123")
    Parser(layers=[[CharClassBlock()], [SimpleCharToTokenReducer()]]).parse_state(state)
    texts = [t.text for t in state.tokens]
    assert texts == ["foo", "+", "123"]
    assert state.tokens[1].labels.get("TOKEN:PLUS") > 0


def test_char_to_token_reducer_provenance():
    state = initialize_char_state("foo")
    Parser(layers=[[CharClassBlock()], [SimpleCharToTokenReducer()]]).parse_state(state)
    parents = state.tokens[0].parents
    assert len(parents) == 3
    assert all(p.relation == "derived_from" for p in parents)
    assert [p.slot_id for p in parents] == ["char:0", "char:1", "char:2"]


def test_char_stream_remains_intact_after_reduction():
    state = initialize_char_state("foo")
    Parser(layers=[[CharClassBlock()], [SimpleCharToTokenReducer()]]).parse_state(state)
    assert len(state.stream("char")) == 3


def test_ambiguous_shift_right_creates_three_candidates():
    state = initialize_char_state(">>")
    Parser(
        layers=[[CharClassBlock()], [AmbiguousShiftRightReducer()]],
        config=ParserConfig(min_weight=0.0),
    ).parse_state(state)
    tokens = state.tokens
    # SHIFT_RIGHT plus two GT alternates
    assert len(tokens) == 3
    labels = {t.text: t for t in tokens}
    # Three slots all with text ">" or ">>"
    text_counts = {}
    for t in tokens:
        text_counts[t.text] = text_counts.get(t.text, 0) + 1
    assert text_counts == {">>": 1, ">": 2}


def test_ambiguous_shift_right_alternate_to_provenance():
    state = initialize_char_state(">>")
    Parser(
        layers=[[CharClassBlock()], [AmbiguousShiftRightReducer()]],
        config=ParserConfig(min_weight=0.0),
    ).parse_state(state)
    shift = next(t for t in state.tokens if t.text == ">>")
    gts = [t for t in state.tokens if t.text == ">"]
    for gt in gts:
        relations = {(p.relation, p.slot_id) for p in gt.parents}
        assert ("alternate_to", shift.id) in relations


def test_overlapping_token_candidates_have_overlapping_spans():
    state = initialize_char_state(">>")
    Parser(
        layers=[[CharClassBlock()], [AmbiguousShiftRightReducer()]],
        config=ParserConfig(min_weight=0.0),
    ).parse_state(state)
    spans = [t.source_span for t in state.tokens]
    # There exist two slots whose source_spans share a position.
    overlaps = sum(
        1
        for i, a in enumerate(spans)
        for j, b in enumerate(spans)
        if i < j and a is not None and b is not None and a.start < b.end and b.start < a.end
    )
    assert overlaps >= 1

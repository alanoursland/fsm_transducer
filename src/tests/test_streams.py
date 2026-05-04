"""Multi-stream ParserState behavior."""

import pytest

from fsm_parser.labels import LabelBag
from fsm_parser.slots import Slot, SourceSpan
from fsm_parser.tokens import (
    ParserState,
    initialize_char_state,
    initialize_state,
)


def test_state_tokens_property_backs_token_stream():
    state = initialize_state("hi there")
    assert state.tokens is state.stream("token")
    assert len(state.tokens) == 2


def test_state_streams_lazy_creation():
    state = ParserState()
    assert "phrase" not in state.streams
    state.stream("phrase")
    assert "phrase" in state.streams
    assert state.streams["phrase"] == []


def test_get_slot_by_id():
    state = initialize_state("hi there")
    slot = state.tokens[1]
    assert state.get_slot(slot.id) is slot


def test_add_slot_appends_and_indexes():
    state = ParserState()
    s = Slot(id="phrase:0", kind="phrase", stream="phrase", order=0.0)
    state.add_slot("phrase", s)
    assert state.stream("phrase") == [s]
    assert state.get_slot("phrase:0") is s


def test_add_slot_rejects_stream_mismatch():
    state = ParserState()
    s = Slot(id="x:0", kind="x", stream="phrase", order=0.0)
    with pytest.raises(ValueError):
        state.add_slot("token", s)


def test_add_slot_rejects_duplicate_id():
    state = ParserState()
    a = Slot(id="phrase:0", stream="phrase", kind="phrase")
    b = Slot(id="phrase:0", stream="phrase", kind="phrase")
    state.add_slot("phrase", a)
    with pytest.raises(ValueError):
        state.add_slot("phrase", b)


def test_next_id_increments_per_stream():
    state = ParserState()
    assert state.next_id("phrase") == "phrase:0"
    assert state.next_id("phrase") == "phrase:1"
    assert state.next_id("semantic") == "semantic:0"


def test_legacy_tokens_constructor():
    s = Slot(id="token:0", text="x")
    state = ParserState(tokens=[s])
    assert state.tokens == [s]
    assert state.get_slot("token:0") is s


def test_initialize_char_state_creates_char_stream():
    state = initialize_char_state("a+1")
    chars = state.stream("char")
    assert len(chars) == 3
    assert chars[0].id == "char:0"
    assert chars[0].text == "a"
    assert chars[0].source_span == SourceSpan(0, 1)
    assert chars[1].text == "+"
    assert chars[2].text == "1"


def test_initialize_state_records_source_spans():
    state = initialize_state("the cat")
    spans = [t.source_span for t in state.tokens]
    assert spans[0] == SourceSpan(0, 3)
    assert spans[1] == SourceSpan(4, 7)


def test_sort_stream_orders_by_order_then_span():
    state = ParserState()
    a = Slot(id="t:0", text="b", order=1.0, source_span=SourceSpan(2, 3), stream="phrase")
    b = Slot(id="t:1", text="a", order=0.0, source_span=SourceSpan(0, 1), stream="phrase")
    state.add_slot("phrase", a)
    state.add_slot("phrase", b)
    state.sort_stream("phrase")
    assert state.stream("phrase")[0] is b

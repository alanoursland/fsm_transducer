"""AddLabel / AddSlot delta application."""

import pytest

from fsm_parser.labels import AddSlot, LabelDelta
from fsm_parser.normalization import apply_deltas
from fsm_parser.slots import Slot
from fsm_parser.tokens import ParserState, initialize_state


def test_label_delta_constructible_with_token_index():
    d = LabelDelta(token_index=2, label="X", weight=0.5)
    assert d.slot_id == "token:2"
    assert d.token_index == 2


def test_label_delta_constructible_with_slot_id():
    d = LabelDelta(slot_id="phrase:5", label="X", weight=0.5)
    assert d.slot_id == "phrase:5"
    assert d.token_index == -1


def test_label_delta_positional_int_treated_as_token_index():
    d = LabelDelta(2, "X", 0.5, "src")
    assert d.slot_id == "token:2"


def test_label_delta_positional_str_treated_as_slot_id():
    d = LabelDelta("token:9", "X", 0.5)
    assert d.slot_id == "token:9"


def test_apply_deltas_adds_label_to_slot_by_id():
    state = initialize_state("a b")
    apply_deltas(state, [LabelDelta(slot_id="token:1", label="X", weight=0.5)])
    assert state.tokens[1].labels.get("X") == 0.5


def test_apply_deltas_ignores_missing_slot():
    state = initialize_state("a")
    apply_deltas(state, [LabelDelta(slot_id="bogus:0", label="X", weight=1.0)])
    # nothing raised; nothing added
    assert state.tokens[0].labels.get("X") == 0.0


def test_apply_deltas_handles_addslot():
    state = ParserState()
    s = Slot(id="phrase:0", kind="phrase", stream="phrase", order=0.0)
    apply_deltas(state, [AddSlot(stream="phrase", slot=s)])
    assert state.stream("phrase") == [s]
    assert state.get_slot("phrase:0") is s


def test_apply_deltas_rejects_addslot_stream_mismatch():
    state = ParserState()
    s = Slot(id="phrase:0", kind="phrase", stream="phrase", order=0.0)
    with pytest.raises(ValueError):
        apply_deltas(state, [AddSlot(stream="token", slot=s)])


def test_apply_deltas_sorts_touched_streams():
    state = ParserState()
    a = Slot(id="phrase:1", stream="phrase", order=2.0)
    b = Slot(id="phrase:0", stream="phrase", order=1.0)
    apply_deltas(
        state,
        [AddSlot(stream="phrase", slot=a), AddSlot(stream="phrase", slot=b)],
    )
    assert [s.id for s in state.stream("phrase")] == ["phrase:0", "phrase:1"]

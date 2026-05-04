from fsm_parser.labels import LabelBag
from fsm_parser.slots import (
    ProvenanceEdge,
    Slot,
    SourceSpan,
    Token,
    slot_sort_key,
)


def test_slot_default_fields():
    s = Slot(id="token:0", text="hi")
    assert s.kind == "token"
    assert s.stream == "token"
    assert s.order == 0.0
    assert s.parents == ()
    assert s.source_span is None


def test_slot_index_property_for_token_stream():
    s = Slot(id="token:7", text="x")
    assert s.index == 7


def test_slot_index_handles_non_integer_suffix():
    s = Slot(id="phrase:abc", text="x")
    assert s.index == -1


def test_token_alias():
    assert Token is Slot


def test_source_span_length():
    span = SourceSpan(2, 5)
    assert span.length() == 3


def test_provenance_edge_is_hashable():
    a = ProvenanceEdge("derived_from", "char:0")
    b = ProvenanceEdge("derived_from", "char:0")
    assert a == b
    assert hash(a) == hash(b)


def test_slot_sort_key_orders_by_order_then_span():
    a = Slot(id="x:0", order=1.0, source_span=SourceSpan(0, 1))
    b = Slot(id="x:1", order=1.0, source_span=SourceSpan(2, 3))
    assert slot_sort_key(a) < slot_sort_key(b)


def test_slot_carries_label_bag():
    bag = LabelBag()
    bag.add("X", 1.0)
    s = Slot(id="t:0", labels=bag)
    assert s.labels.get("X") == 1.0

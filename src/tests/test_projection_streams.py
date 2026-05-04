from fsm_parser import (
    AmbiguousShiftRightReducer,
    CharClassBlock,
    Parser,
    ParserConfig,
    initialize_char_state,
)
from fsm_parser.projection import (
    project_dependency_edges,
    project_non_overlapping,
    project_spans,
)
from fsm_parser.slots import Slot, SourceSpan
from fsm_parser.tokens import ParserState


def test_project_spans_accepts_stream_argument():
    state = ParserState()
    a = Slot(id="phrase:0", stream="phrase", text="a", order=0.0)
    a.labels.add("NP_START", 1.0)
    a.labels.add("NP_HEAD", 1.0)
    b = Slot(id="phrase:1", stream="phrase", text="b", order=1.0)
    b.labels.add("NP_END", 1.0)
    state.add_slot("phrase", a)
    state.add_slot("phrase", b)
    spans = project_spans(
        state,
        start_label="NP_START",
        end_label="NP_END",
        head_label="NP_HEAD",
        stream="phrase",
    )
    assert len(spans) == 1
    assert spans[0].start == 0
    assert spans[0].end == 1
    assert spans[0].head == 0


def test_project_dependency_edges_accepts_stream():
    state = ParserState()
    a = Slot(id="t:0", stream="custom", text="a", order=0.0)
    b = Slot(id="t:1", stream="custom", text="b", order=1.0)
    b.labels.add("DEP:nsubj:0", 1.0)
    state.add_slot("custom", a)
    state.add_slot("custom", b)
    edges = project_dependency_edges(state, relation_prefix="DEP:", stream="custom")
    assert len(edges) == 1
    assert edges[0].relation == "nsubj"
    assert edges[0].head == 0
    assert edges[0].dependent == 1


def test_non_overlap_projection_resolves_ambiguous_tokens():
    state = initialize_char_state(">>")
    Parser(
        layers=[[CharClassBlock()], [AmbiguousShiftRightReducer()]],
        config=ParserConfig(min_weight=0.0),
    ).parse_state(state)
    chosen = project_non_overlapping(state, stream="token")
    # Greedy by start, then longer span first: should pick the one ">>" slot.
    assert len(chosen) == 1
    assert chosen[0].text == ">>"


def test_non_overlap_projection_passes_through_spanless_slots():
    state = ParserState()
    a = Slot(id="x:0", stream="custom", text="a", order=0.0, source_span=None)
    a.labels.add("X", 1.0)
    state.add_slot("custom", a)
    chosen = project_non_overlapping(state, stream="custom")
    assert chosen == [a]

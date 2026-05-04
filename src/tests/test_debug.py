from fsm_parser.debug import render_state, render_trace
from fsm_parser.grammar import build_default_parser


def test_render_state_includes_all_tokens():
    parser = build_default_parser()
    state = parser.parse("The cat slept")
    rendered = render_state(state, top_k=3)
    assert "The" in rendered
    assert "cat" in rendered
    assert "slept" in rendered
    assert "Layer" in rendered


def test_render_trace_has_layer_headers():
    parser = build_default_parser()
    _, traces = parser.parse_with_trace("the book")
    rendered = render_trace(traces, top_k=3)
    assert "Layer 0" in rendered
    assert "Layer 1" in rendered
    assert "Deltas" in rendered

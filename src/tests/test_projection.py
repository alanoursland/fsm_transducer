from fsm_parser.projection import project_dependency_edges, project_spans
from fsm_parser.tokens import initialize_state


def test_project_spans_pairs_start_and_end():
    state = initialize_state("the cat")
    state.tokens[0].labels.add("NP_START", 1.0)
    state.tokens[1].labels.add("NP_END", 1.0)
    state.tokens[1].labels.add("NP_HEAD", 1.0)
    spans = project_spans(
        state,
        start_label="NP_START",
        end_label="NP_END",
        head_label="NP_HEAD",
        span_label="NP",
    )
    assert len(spans) == 1
    assert spans[0].start == 0
    assert spans[0].end == 1
    assert spans[0].head == 1
    assert spans[0].label == "NP"


def test_project_spans_skips_unmatched_starts():
    state = initialize_state("a b c")
    state.tokens[0].labels.add("NP_START", 1.0)
    spans = project_spans(state, start_label="NP_START", end_label="NP_END")
    assert spans == []


def test_project_dependency_edges_parses_pointer_labels():
    state = initialize_state("a b c")
    state.tokens[1].labels.add("DEP:nsubj:0", 0.9)
    state.tokens[2].labels.add("DEP:obj:1", 0.8)
    edges = project_dependency_edges(state, relation_prefix="DEP:")
    by_dep = {e.dependent: e for e in edges}
    assert by_dep[1].relation == "nsubj"
    assert by_dep[1].head == 0
    assert by_dep[2].relation == "obj"
    assert by_dep[2].head == 1


def test_project_dependency_edges_threshold():
    state = initialize_state("a b")
    state.tokens[1].labels.add("DEP:obj:0", 0.05)
    edges = project_dependency_edges(state, relation_prefix="DEP:", threshold=0.1)
    assert edges == []

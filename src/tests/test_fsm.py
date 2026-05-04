from fsm_parser.fsm import (
    Always,
    Emission,
    FSMBuilder,
    FSMScanner,
    HasAnyLabel,
    HasLabel,
    compile_linear,
)
from fsm_parser.tokens import initialize_state


def _seed(state, label_map):
    """Seed POS-style labels onto tokens by index for tests."""
    for index, labels in label_map.items():
        for label, weight in labels.items():
            state.tokens[index].labels.add(label, weight)


def test_compile_linear_emits_only_on_full_match():
    state = initialize_state("the book")
    _seed(state, {0: {"POS:DET": 1.0}, 1: {"POS:NOUN": 1.0}})
    fsm = compile_linear(
        "det_noun",
        [HasLabel("POS:DET"), HasLabel("POS:NOUN")],
        [Emission(label="PHRASE:NP_HEAD", weight=0.8, offset=0)],
    )
    deltas = FSMScanner().scan(fsm, state)
    matched = [d for d in deltas if d.label == "PHRASE:NP_HEAD"]
    assert len(matched) == 1
    assert matched[0].token_index == 1


def test_partial_match_emits_nothing():
    state = initialize_state("the the")
    _seed(state, {0: {"POS:DET": 1.0}, 1: {"POS:DET": 1.0}})
    fsm = compile_linear(
        "det_noun",
        [HasLabel("POS:DET"), HasLabel("POS:NOUN")],
        [Emission(label="PHRASE:NP_HEAD", weight=0.8)],
    )
    assert FSMScanner().scan(fsm, state) == []


def test_offset_minus_one_targets_previous_token():
    state = initialize_state("the cat")
    _seed(state, {0: {"POS:DET": 1.0}, 1: {"POS:NOUN": 1.0}})
    fsm = compile_linear(
        "np",
        [HasLabel("POS:DET"), HasLabel("POS:NOUN")],
        [Emission(label="PHRASE:NP_START", weight=0.7, offset=-1)],
    )
    deltas = FSMScanner().scan(fsm, state)
    assert any(d.token_index == 0 and d.label == "PHRASE:NP_START" for d in deltas)


def test_scanner_runs_at_every_position():
    state = initialize_state("the cat the dog")
    _seed(state, {
        0: {"POS:DET": 1.0},
        1: {"POS:NOUN": 1.0},
        2: {"POS:DET": 1.0},
        3: {"POS:NOUN": 1.0},
    })
    fsm = compile_linear(
        "np",
        [HasLabel("POS:DET"), HasLabel("POS:NOUN")],
        [Emission(label="PHRASE:NP_HEAD", weight=0.8)],
    )
    deltas = FSMScanner().scan(fsm, state)
    assert {d.token_index for d in deltas if d.label == "PHRASE:NP_HEAD"} == {1, 3}


def test_has_any_label():
    state = initialize_state("x")
    _seed(state, {0: {"POS:NOUN": 1.0}})
    fsm = compile_linear(
        "any",
        [HasAnyLabel(("POS:NOUN", "POS:VERB"))],
        [Emission(label="HIT", weight=1.0)],
    )
    assert any(d.label == "HIT" for d in FSMScanner().scan(fsm, state))


def test_min_weight_threshold():
    state = initialize_state("x")
    _seed(state, {0: {"POS:NOUN": 0.05}})
    weak = compile_linear(
        "weak",
        [HasLabel("POS:NOUN", min_weight=0.1)],
        [Emission(label="HIT", weight=1.0)],
    )
    strong = compile_linear(
        "strong",
        [HasLabel("POS:NOUN", min_weight=0.01)],
        [Emission(label="HIT", weight=1.0)],
    )
    assert FSMScanner().scan(weak, state) == []
    assert any(d.label == "HIT" for d in FSMScanner().scan(strong, state))


def test_branching_fsm_with_builder():
    state = initialize_state("the cat ran")
    _seed(state, {
        0: {"POS:DET": 1.0},
        1: {"POS:NOUN": 1.0},
        2: {"POS:VERB": 1.0},
    })
    b = FSMBuilder("det_then_noun_or_verb")
    s0, s1, s2 = b.state("q0"), b.state("q1"), b.state("q2")
    b.start(s0).accept(s2)
    b.transition(s0, HasLabel("POS:DET"), s1)
    b.transition(
        s1,
        HasLabel("POS:NOUN"),
        s2,
        emissions=(Emission(label="VIA_NOUN", weight=1.0),),
    )
    b.transition(
        s1,
        HasLabel("POS:VERB"),
        s2,
        emissions=(Emission(label="VIA_VERB", weight=1.0),),
    )
    fsm = b.build()
    deltas = FSMScanner().scan(fsm, state)
    labels = {d.label for d in deltas}
    assert "VIA_NOUN" in labels
    assert "VIA_VERB" not in labels


def test_scanner_supports_loops_via_builder():
    state = initialize_state("cat cat dog")
    _seed(state, {
        0: {"POS:NOUN": 1.0},
        1: {"POS:NOUN": 1.0},
        2: {"POS:NOUN": 1.0},
    })
    b = FSMBuilder("nouns")
    s0, s1 = b.state("q0"), b.state("q1")
    b.start(s0).accept(s1)
    b.transition(s0, HasLabel("POS:NOUN"), s1)
    # loop on accept state
    b.transition(
        s1,
        HasLabel("POS:NOUN"),
        s1,
        emissions=(Emission(label="REPEATED_NOUN", weight=1.0),),
    )
    fsm = b.build()
    deltas = FSMScanner().scan(fsm, state)
    assert any(d.label == "REPEATED_NOUN" for d in deltas)


def test_always_condition():
    state = initialize_state("abc")
    fsm = compile_linear(
        "any",
        [Always()],
        [Emission(label="MATCH", weight=1.0)],
    )
    assert len(FSMScanner().scan(fsm, state)) == 1


def test_builder_requires_start_and_accept():
    import pytest

    b = FSMBuilder("bad")
    with pytest.raises(ValueError):
        b.build()
    s = b.state()
    b.start(s)
    with pytest.raises(ValueError):
        b.build()

from fsm_parser.combinators import literal
from fsm_parser.fsm import (
    And,
    AtSentenceStart,
    Emission,
    FSMScanner,
    HasLabel,
    LabelPredicate,
    Not,
    Or,
    ScanContext,
    WeightAbove,
    WeightBelow,
    compile_linear,
)
from fsm_parser.tokens import initialize_state


def _seed(state, label_map):
    for index, labels in label_map.items():
        for label, weight in labels.items():
            state.tokens[index].labels.add(label, weight)


def test_not_inverts_match():
    state = initialize_state("a b")
    _seed(state, {0: {"X": 1.0}})
    cond = Not(HasLabel("X"))
    assert cond.matches(state.tokens[0]) is False
    assert cond.matches(state.tokens[1]) is True


def test_and_requires_all():
    state = initialize_state("a")
    _seed(state, {0: {"X": 1.0, "Y": 1.0}})
    assert And((HasLabel("X"), HasLabel("Y"))).matches(state.tokens[0])
    assert not And((HasLabel("X"), HasLabel("Z"))).matches(state.tokens[0])


def test_or_requires_any():
    state = initialize_state("a")
    _seed(state, {0: {"X": 1.0}})
    assert Or((HasLabel("Z"), HasLabel("X"))).matches(state.tokens[0])
    assert not Or((HasLabel("Z"), HasLabel("W"))).matches(state.tokens[0])


def test_weight_above_below():
    state = initialize_state("a")
    _seed(state, {0: {"X": 0.5}})
    assert WeightAbove("X", 0.4).matches(state.tokens[0])
    assert not WeightAbove("X", 0.5).matches(state.tokens[0])
    assert WeightBelow("X", 0.6).matches(state.tokens[0])
    assert not WeightBelow("X", 0.4).matches(state.tokens[0])


def test_at_sentence_start_and_end_via_scan():
    state = initialize_state("a b c")
    fsm = compile_linear(
        "first_only",
        [And((AtSentenceStart(), HasLabel("TOKEN")))],
        [Emission("FIRST", 1.0)],
    )
    deltas = FSMScanner().scan(fsm, state)
    hits = [d.token_index for d in deltas if d.label == "FIRST"]
    assert hits == [0]


def test_at_sentence_start_requires_ctx():
    cond = AtSentenceStart()
    state = initialize_state("a")
    # without ctx, defaults to False
    assert cond.matches(state.tokens[0]) is False
    ctx = ScanContext(scan_start=0, n=1, pos=0)
    assert cond.matches(state.tokens[0], ctx) is True


def test_label_predicate_matches_by_string():
    state = initialize_state("the cat")
    state.tokens[1].labels.add("POS:NOUN", 1.0)
    fsm = compile_linear(
        "any_pos",
        [LabelPredicate(lambda label: label.startswith("POS:"))],
        [Emission("HAS_POS", 1.0)],
    )
    deltas = FSMScanner().scan(fsm, state)
    assert any(d.label == "HAS_POS" and d.token_index == 1 for d in deltas)


def test_combined_conditions_in_combinator_grammar():
    state = initialize_state("the dog")
    _seed(state, {0: {"POS:DET": 1.0}, 1: {"POS:NOUN": 1.0}})
    machine = literal(
        Or((HasLabel("POS:NOUN"), HasLabel("POS:VERB"))),
        emissions=[Emission("CONTENT_WORD", 1.0)],
    )
    deltas = FSMScanner().scan(machine, state)
    indices = sorted({d.token_index for d in deltas if d.label == "CONTENT_WORD"})
    assert indices == [1]

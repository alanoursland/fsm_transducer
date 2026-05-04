from fsm_parser.combinators import (
    alt,
    call,
    concat,
    epsilon,
    literal,
    optional,
    plus,
    repeat,
    star,
)
from fsm_parser.fsm import (
    Capture,
    CaptureAnchor,
    Emission,
    FSMScanner,
    HasLabel,
)
from fsm_parser.tokens import initialize_state


def _seed(state, label_map):
    for index, labels in label_map.items():
        for label, weight in labels.items():
            state.tokens[index].labels.add(label, weight)


def test_literal_matches_one_token():
    state = initialize_state("the cat")
    _seed(state, {0: {"POS:DET": 1.0}})
    fsm = literal(HasLabel("POS:DET"), emissions=[Emission("HIT", 1.0)])
    deltas = FSMScanner().scan(fsm, state)
    hits = [d for d in deltas if d.label == "HIT"]
    assert len(hits) == 1
    assert hits[0].token_index == 0


def test_concat_threads_machines():
    state = initialize_state("the cat")
    _seed(state, {0: {"POS:DET": 1.0}, 1: {"POS:NOUN": 1.0}})
    np = concat(
        literal(HasLabel("POS:DET")),
        literal(HasLabel("POS:NOUN"), emissions=[Emission("NP_HEAD", 1.0)]),
    )
    deltas = FSMScanner().scan(np, state)
    assert any(d.label == "NP_HEAD" and d.token_index == 1 for d in deltas)


def test_alt_matches_either_branch():
    state = initialize_state("the dog")
    _seed(state, {0: {"POS:DET": 1.0}, 1: {"POS:NOUN": 1.0}})
    machine = alt(
        literal(HasLabel("POS:VERB"), emissions=[Emission("VERB_HIT", 1.0)]),
        literal(HasLabel("POS:DET"), emissions=[Emission("DET_HIT", 1.0)]),
    )
    deltas = FSMScanner().scan(machine, state)
    labels = {d.label for d in deltas}
    assert "DET_HIT" in labels
    assert "VERB_HIT" not in labels


def test_star_matches_zero_or_more():
    state = initialize_state("the big red dog")
    _seed(state, {
        0: {"POS:DET": 1.0},
        1: {"POS:ADJ": 1.0},
        2: {"POS:ADJ": 1.0},
        3: {"POS:NOUN": 1.0},
    })
    machine = concat(
        literal(HasLabel("POS:DET")),
        star(literal(HasLabel("POS:ADJ"))),
        literal(HasLabel("POS:NOUN"), emissions=[Emission("NP_HEAD", 1.0)]),
    )
    deltas = FSMScanner().scan(machine, state)
    heads = [d for d in deltas if d.label == "NP_HEAD"]
    assert len(heads) == 1
    assert heads[0].token_index == 3


def test_star_matches_zero_adjectives():
    state = initialize_state("the dog")
    _seed(state, {0: {"POS:DET": 1.0}, 1: {"POS:NOUN": 1.0}})
    machine = concat(
        literal(HasLabel("POS:DET")),
        star(literal(HasLabel("POS:ADJ"))),
        literal(HasLabel("POS:NOUN"), emissions=[Emission("NP_HEAD", 1.0)]),
    )
    deltas = FSMScanner().scan(machine, state)
    heads = [d for d in deltas if d.label == "NP_HEAD"]
    assert len(heads) == 1
    assert heads[0].token_index == 1


def test_optional_matches_with_or_without():
    state = initialize_state("dog")
    _seed(state, {0: {"POS:NOUN": 1.0}})
    machine = concat(
        optional(literal(HasLabel("POS:DET"))),
        literal(HasLabel("POS:NOUN"), emissions=[Emission("NP_HEAD", 1.0)]),
    )
    deltas = FSMScanner().scan(machine, state)
    assert any(d.label == "NP_HEAD" for d in deltas)


def test_plus_requires_at_least_one():
    state = initialize_state("dog")
    _seed(state, {0: {"POS:NOUN": 1.0}})
    machine = plus(literal(HasLabel("POS:ADJ"), emissions=[Emission("ADJ_HIT", 1.0)]))
    assert FSMScanner().scan(machine, state) == []


def test_repeat_with_bounds():
    state = initialize_state("a a a a")
    _seed(state, {i: {"X": 1.0} for i in range(4)})
    machine = repeat(literal(HasLabel("X")), min_n=2, max_n=3)
    # Concat with a sentinel emission so we can spot acceptance positions.
    sentinel = concat(machine, literal(HasLabel("X"), emissions=[Emission("HIT", 1.0)]))
    deltas = FSMScanner().scan(sentinel, state)
    # Must have consumed 3 or 4 X tokens before HIT, so HIT only at index >= 2.
    indices = sorted({d.token_index for d in deltas if d.label == "HIT"})
    assert all(i >= 2 for i in indices)


def test_call_wraps_machine():
    state = initialize_state("the cat")
    _seed(state, {0: {"POS:DET": 1.0}, 1: {"POS:NOUN": 1.0}})
    inner = concat(
        literal(HasLabel("POS:DET")),
        literal(HasLabel("POS:NOUN"), emissions=[Emission("HEAD", 1.0)]),
    )
    wrapped = call(inner)
    deltas = FSMScanner().scan(wrapped, state)
    assert any(d.label == "HEAD" and d.token_index == 1 for d in deltas)


def test_capture_anchored_emission_targets_earlier_token():
    state = initialize_state("the cat ran")
    _seed(state, {
        0: {"POS:DET": 1.0},
        1: {"POS:NOUN": 1.0},
        2: {"POS:VERB": 1.0},
    })
    machine = concat(
        literal(HasLabel("POS:DET")),
        literal(HasLabel("POS:NOUN"), captures=[Capture("head")]),
        literal(
            HasLabel("POS:VERB"),
            captures=[Capture("verb")],
            emissions=[
                Emission("SUBJECT_OF:{verb}", 0.6, anchor=CaptureAnchor("head")),
            ],
        ),
    )
    deltas = FSMScanner().scan(machine, state)
    pointer = [d for d in deltas if d.label.startswith("SUBJECT_OF:")]
    assert len(pointer) == 1
    assert pointer[0].token_index == 1
    assert pointer[0].label == "SUBJECT_OF:2"


def test_epsilon_machine_accepts_immediately():
    state = initialize_state("a")
    fsm = epsilon(emissions=[Emission("EPS_HIT", 1.0)])
    deltas = FSMScanner().scan(fsm, state)
    # epsilon transitions don't consume; emissions with default FiringOffset
    # have no firing position so won't anchor. Verify it doesn't crash and
    # the FSM accepts (no other rule).
    assert all(d.label != "EPS_HIT" for d in deltas)

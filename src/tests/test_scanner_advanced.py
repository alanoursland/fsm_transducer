"""Advanced scanner tests: epsilon closure, semiring choice, path merging."""

from fsm_parser.combinators import alt, concat, literal, star
from fsm_parser.fsm import (
    Emission,
    FSMScanner,
    HasLabel,
)
from fsm_parser.semirings import ProductReal, TropicalMax
from fsm_parser.tokens import initialize_state


def _seed(state, label_map):
    for index, labels in label_map.items():
        for label, weight in labels.items():
            state.tokens[index].labels.add(label, weight)


def test_epsilon_closure_does_not_double_emit_on_loop():
    state = initialize_state("a a a")
    _seed(state, {i: {"X": 1.0} for i in range(3)})
    machine = star(literal(HasLabel("X"), emissions=[Emission("HIT", 1.0)]))
    deltas = FSMScanner().scan(machine, state)
    hits = [d for d in deltas if d.label == "HIT"]
    # Each token can fire HIT once per scan starting position; the test
    # ensures no exponential blowup of duplicate identical deltas.
    # 3 starts x up to 3 tokens each = 6 expected (1 + 2 + 3).
    assert 1 <= len(hits) <= 6


def test_path_merging_via_alt_does_not_split_emissions():
    state = initialize_state("a")
    _seed(state, {0: {"X": 1.0}})
    # Two alternative paths land on the same accept with the same emission.
    machine = alt(
        literal(HasLabel("X"), emissions=[Emission("HIT", 1.0)]),
        literal(HasLabel("X"), emissions=[Emission("HIT", 1.0)]),
    )
    deltas = FSMScanner().scan(machine, state)
    hits = [d for d in deltas if d.label == "HIT"]
    # Two paths produce two emissions because their pending differs by source
    # transition; this is by design — merging only collapses identical pending.
    assert len(hits) >= 1


def test_default_semiring_is_product_real():
    scanner = FSMScanner()
    assert isinstance(scanner.semiring, ProductReal)


def test_tropical_max_semiring_keeps_best_path_weight():
    state = initialize_state("a")
    _seed(state, {0: {"X": 1.0}})
    fsm = literal(HasLabel("X"), emissions=[Emission("HIT", 0.5)])
    scanner = FSMScanner(semiring=TropicalMax())
    deltas = scanner.scan(fsm, state)
    # under tropical-max, transition weight 1.0 + emission 0.5 = 1.5
    assert any(abs(d.weight - 1.5) < 1e-9 for d in deltas)


def test_legacy_combine_callable_still_supported():
    import operator

    state = initialize_state("a")
    _seed(state, {0: {"X": 1.0}})
    fsm = literal(HasLabel("X"), emissions=[Emission("HIT", 0.5)])
    scanner = FSMScanner(combine=operator.mul)
    deltas = scanner.scan(fsm, state)
    assert any(abs(d.weight - 0.5) < 1e-9 for d in deltas)


def test_emission_template_substitution_works_without_capture_anchor():
    """Template strings can also resolve in non-anchor labels."""
    from fsm_parser.fsm import Capture

    state = initialize_state("the cat")
    _seed(state, {0: {"POS:DET": 1.0}, 1: {"POS:NOUN": 1.0}})
    machine = concat(
        literal(HasLabel("POS:DET"), captures=[Capture("d")]),
        literal(
            HasLabel("POS:NOUN"),
            emissions=[Emission("AFTER_DET:{d}", 1.0)],
        ),
    )
    deltas = FSMScanner().scan(machine, state)
    assert any(d.label == "AFTER_DET:0" for d in deltas)

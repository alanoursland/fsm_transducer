"""transduce() must equal scan() up to delta ordering, on every machine shape."""

from fsm_parser.combinators import alt, concat, literal, optional, star
from fsm_parser.fsm import (
    Always,
    Capture,
    CaptureAnchor,
    Emission,
    FSMScanner,
    HasLabel,
    compile_linear,
)
from fsm_parser.semirings import LogSemiring, ProductReal, TropicalMax
from fsm_parser.tokens import initialize_state


def _delta_multiset(deltas):
    return sorted((d.slot_id, d.label, round(d.weight, 9), d.source) for d in deltas)


def _state(text="the big big cat sat on the mat"):
    state = initialize_state(text)
    pos = {
        "the": ("POS:DET", 0.9),
        "big": ("POS:ADJ", 0.8),
        "cat": ("POS:NOUN", 0.7),
        "mat": ("POS:NOUN", 0.7),
        "sat": ("POS:VERB", 0.8),
        "on": ("POS:PREP", 0.9),
    }
    for slot in state.tokens:
        label, w = pos[slot.text]
        slot.labels.add(label, w)
    return state


def _machines():
    det_noun = compile_linear(
        "det_noun",
        [HasLabel("POS:DET"), HasLabel("POS:NOUN")],
        [Emission("PHRASE:NP_HEAD", 0.8, offset=0), Emission("PHRASE:NP_START", 0.8, offset=-1)],
    )
    np_star = concat(
        literal(HasLabel("POS:DET"), emissions=[Emission("NP_OPEN", 0.5, offset=0)]),
        star(literal(HasLabel("POS:ADJ"), emissions=[Emission("NP_MOD", 0.5, offset=0)])),
        literal(HasLabel("POS:NOUN"), emissions=[Emission("NP_HEAD", 0.5, offset=0)]),
        name="np_star",
    )
    captures = concat(
        literal(
            HasLabel("POS:NOUN"),
            captures=[Capture("subj", kind="top_label")],
        ),
        optional(literal(HasLabel("POS:ADJ"))),
        literal(
            HasLabel("POS:VERB"),
            emissions=[
                Emission("SUBJ_OF:{subj}", 0.6, anchor=CaptureAnchor("subj")),
            ],
        ),
        name="captures",
    )
    anything = alt(
        literal(Always(), emissions=[Emission("ANY", 0.1, offset=0)]),
        literal(HasLabel("POS:VERB"), emissions=[Emission("V", 0.2, offset=0)]),
        name="any_or_verb",
    )
    return [det_noun, np_star, captures, anything]


def test_transduce_matches_scan_default_semiring():
    scanner = FSMScanner()
    for fsm in _machines():
        a = _delta_multiset(scanner.scan(fsm, _state()))
        b = _delta_multiset(scanner.transduce(fsm, _state()))
        assert a == b, fsm.name


def test_transduce_matches_scan_other_semirings():
    for sr in (ProductReal(), TropicalMax(), LogSemiring()):
        scanner = FSMScanner(semiring=sr)
        for fsm in _machines():
            a = _delta_multiset(scanner.scan(fsm, _state()))
            b = _delta_multiset(scanner.transduce(fsm, _state()))
            assert a == b, (type(sr).__name__, fsm.name)


def test_transduce_empty_input():
    state = initialize_state("")
    scanner = FSMScanner()
    for fsm in _machines():
        assert scanner.transduce(fsm, state) == []


def test_transduce_frontier_is_bounded_for_capture_free_machine():
    """Capture-free machines: frontier <= live starts * |Q|.

    For the acyclic det_noun machine, paths die within 2 positions, so
    the frontier should stay O(|Q|) regardless of input length.
    """

    det_noun = _machines()[0]
    n_states = len(det_noun.states())
    state = _state("the cat " * 30)

    max_frontier = 0
    orig = FSMScanner._epsilon_close

    def spy(self, paths, fsm, deltas, *, slots):
        nonlocal max_frontier
        result = orig(self, paths, fsm, deltas, slots=slots)
        max_frontier = max(max_frontier, len(result))
        return result

    FSMScanner._epsilon_close = spy
    try:
        FSMScanner().transduce(det_noun, state)
    finally:
        FSMScanner._epsilon_close = orig
    # Machine depth is 2, so at most 2 live start offsets contribute.
    assert max_frontier <= 2 * n_states

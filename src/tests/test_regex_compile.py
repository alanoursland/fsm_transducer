"""Regex front-end: parsing, compilation, group emissions, config hookup."""

import pytest

from fsm_parser.analysis import accepts
from fsm_parser.config import parse_grammar
from fsm_parser.fsm import Emission, FSMScanner, HasLabel
from fsm_parser.pipeline import Parser
from fsm_parser.regex_compile import (
    RegexError,
    RxAlt,
    RxAtom,
    RxConcat,
    RxGroup,
    RxRepeat,
    compile_regex,
    parse_regex,
)
from fsm_parser.slots import Slot
from fsm_parser.tokens import initialize_state


def _slots(*label_lists):
    out = []
    for i, labels in enumerate(label_lists):
        slot = Slot(id=f"token:{i}", order=float(i))
        for lab in labels:
            slot.labels.add(lab, 1.0)
        out.append(slot)
    return out


# --- Parsing -----------------------------------------------------------------


def test_parse_atom_and_weight():
    ast = parse_regex("<POS:DET@0.3>")
    assert ast == RxAtom(HasLabel("POS:DET", min_weight=0.3))


def test_parse_precedence_star_binds_tighter_than_concat_and_alt():
    ast = parse_regex("<A> <B>* | <C>")
    assert isinstance(ast, RxAlt)
    left = ast.parts[0]
    assert isinstance(left, RxConcat)
    assert isinstance(left.parts[1], RxRepeat)
    assert left.parts[1].min_n == 0 and left.parts[1].max_n is None


def test_parse_groups_and_bounds():
    ast = parse_regex("(?P<np> <N>{2,3})")
    assert isinstance(ast, RxGroup) and ast.name == "np"
    assert ast.inner == RxRepeat(RxAtom(HasLabel("N")), 2, 3)


@pytest.mark.parametrize(
    "bad",
    ["", "<", "<>", "(<A>", "<A>)", "(?P<1bad> <A>)", "<A>{x}", "|<A>", "<A@z>"],
)
def test_parse_errors(bad):
    with pytest.raises(RegexError):
        parse_regex(bad)


# --- Acceptance semantics ----------------------------------------------------


def test_compiled_acceptance():
    fsm = compile_regex("<A> (<B>|<C>)* <D>?")
    assert accepts(fsm, _slots(["A"]))
    assert accepts(fsm, _slots(["A"], ["B"], ["C"], ["B"]))
    assert accepts(fsm, _slots(["A"], ["C"], ["D"]))
    assert not accepts(fsm, _slots(["B"]))
    assert not accepts(fsm, _slots(["A"], ["D"], ["D"]))


def test_bounded_repetition():
    fsm = compile_regex("<A>{2,3}")
    assert not accepts(fsm, _slots(["A"]))
    assert accepts(fsm, _slots(["A"], ["A"]))
    assert accepts(fsm, _slots(["A"], ["A"], ["A"]))
    assert not accepts(fsm, _slots(["A"], ["A"], ["A"], ["A"]))


def test_dot_matches_anything():
    fsm = compile_regex(". <A>")
    assert accepts(fsm, _slots(["ZZZ"], ["A"]))


# --- Group emissions ---------------------------------------------------------


def _np_state():
    state = initialize_state("the big red cat sat")
    pos = {
        "the": "POS:DET",
        "big": "POS:ADJ",
        "red": "POS:ADJ",
        "cat": "POS:NOUN",
        "sat": "POS:VERB",
    }
    for slot in state.tokens:
        slot.labels.add(pos[slot.text], 1.0)
    return state


def test_group_emissions_mark_span():
    fsm = compile_regex(
        "<POS:DET> (?P<NP> <POS:ADJ>* <POS:NOUN>)", name="np_rule"
    )
    state = _np_state()
    deltas = FSMScanner().transduce(fsm, state)
    by_label = {}
    for d in deltas:
        by_label.setdefault(d.label, set()).add(d.slot_id)
    # big, red, cat are members; big starts; cat ends.
    assert by_label["NP"] == {"token:1", "token:2", "token:3"}
    assert by_label["NP_START"] == {"token:1"}
    assert by_label["NP_END"] == {"token:3"}
    assert all(d.source == "np_rule" for d in deltas)


def test_group_start_end_coincide_on_single_token_group():
    fsm = compile_regex("(?P<V> <POS:VERB>)")
    deltas = FSMScanner().transduce(fsm, _np_state())
    labels = {(d.label, d.slot_id) for d in deltas}
    assert labels == {
        ("V", "token:4"),
        ("V_START", "token:4"),
        ("V_END", "token:4"),
    }


def test_whole_pattern_emit_on_accept():
    fsm = compile_regex(
        "<POS:DET> <POS:ADJ>* <POS:NOUN>",
        emit=[Emission("PHRASE:NP_END", 0.9, offset=0)],
    )
    deltas = FSMScanner().transduce(fsm, _np_state())
    hits = {(d.label, d.slot_id) for d in deltas if d.label == "PHRASE:NP_END"}
    assert ("PHRASE:NP_END", "token:3") in hits


# --- Config integration ------------------------------------------------------


def test_regex_rule_in_yaml_grammar():
    grammar = parse_grammar(
        {
            "layers": [
                {
                    "blocks": [
                        {
                            "name": "pos",
                            "type": "lexical",
                            "entries": {
                                "the": {"POS:DET": 1.0},
                                "cat": {"POS:NOUN": 1.0},
                            },
                        },
                    ]
                },
                {
                    "blocks": [
                        {
                            "name": "np",
                            "type": "fsm",
                            "fsms": [
                                {
                                    "name": "np_regex",
                                    "regex": "<POS:DET> (?P<NP> <POS:NOUN>)",
                                    "group_weight": 0.7,
                                }
                            ],
                        }
                    ]
                },
            ]
        }
    )
    state = Parser(grammar.layers).parse("the cat")
    cat = state.tokens[1]
    assert cat.labels.get("NP") > 0
    assert cat.labels.get("NP_START") > 0
    assert cat.labels.get("NP_END") > 0

"""Bounds toolkit: accepts(), determinize(), minimize(), analyze()."""

import itertools

import pytest

from fsm_parser.analysis import accepts, analyze, determinize, is_plain, minimize
from fsm_parser.combinators import concat, literal
from fsm_parser.fsm import Capture, Emission, HasLabel, compile_linear
from fsm_parser.regex_compile import compile_regex
from fsm_parser.slots import Slot


def _slots(labels_seq):
    out = []
    for i, lab in enumerate(labels_seq):
        slot = Slot(id=f"token:{i}", order=float(i))
        slot.labels.add(lab, 1.0)
        out.append(slot)
    return out


def _all_strings(alphabet, max_len):
    for n in range(max_len + 1):
        yield from itertools.product(alphabet, repeat=n)


def test_determinize_and_minimize_preserve_language():
    # Classic (a|b)*abb. Note the deterministic alphabet is *minterms* of
    # the conditions, so slots carrying both A and B are part of the
    # language space and the minimal machine is larger than the textbook
    # 4-state DFA over an exclusive {a, b} alphabet.
    nfa = compile_regex("(<A>|<B>)* <A> <B> <B>")
    dfa = determinize(nfa)
    mdfa = minimize(dfa)
    for word in _all_strings(["A", "B"], 6):
        slots = _slots(word)
        expected = accepts(nfa, slots)
        assert accepts(dfa, slots) == expected, word
        assert accepts(mdfa, slots) == expected, word
    assert len(mdfa.states()) <= len(dfa.states())


def test_minimize_reaches_known_minimum_single_condition():
    # <A>+ over a one-condition alphabet has a 2-state minimal DFA.
    nfa = compile_regex("<A>+")
    mdfa = minimize(determinize(nfa))
    for word in _all_strings(["A"], 4):
        assert accepts(mdfa, _slots(word)) == (len(word) >= 1)
    assert len(mdfa.states()) == 2


def test_determinize_rejects_non_plain_machines():
    with_emissions = compile_linear(
        "e", [HasLabel("A")], [Emission("X", 1.0, offset=0)]
    )
    with_captures = concat(
        literal(HasLabel("A"), captures=[Capture("c")]), literal(HasLabel("B"))
    )
    for fsm in (with_emissions, with_captures):
        assert not is_plain(fsm)
        with pytest.raises(ValueError):
            determinize(fsm)


def test_determinize_condition_guard():
    pattern = " ".join(f"<L{i}>" for i in range(12))
    nfa = compile_regex(pattern)
    with pytest.raises(ValueError):
        determinize(nfa, max_conditions=10)
    determinize(nfa, max_conditions=12)  # explicit opt-in works


def test_overlapping_conditions_are_handled_by_minterms():
    # A slot can satisfy both <A> and <A@0.5>; minterm construction must
    # keep the DFA faithful anyway.
    nfa = compile_regex("<A> <A@0.5>")
    dfa = determinize(nfa)

    def slot(weight):
        s = Slot(id="token:0", order=0.0)
        s.labels.add("A", weight)
        return s

    def two(w1, w2):
        a, b = slot(w1), slot(w2)
        b.id, b.order = "token:1", 1.0
        return [a, b]

    for w1, w2 in [(1.0, 1.0), (1.0, 0.3), (0.3, 1.0), (0.3, 0.3)]:
        expected = accepts(nfa, two(w1, w2))
        assert accepts(dfa, two(w1, w2)) == expected, (w1, w2)


def test_analyze_reports():
    plain = compile_regex("<A>* <B>")
    a = analyze(plain)
    assert a.plain and a.determinizable and not a.has_captures
    assert "|Q| = " in a.frontier_bound
    assert f"states:                {a.n_states}" in a.report()

    capturing = concat(
        literal(HasLabel("A"), captures=[Capture("x")]),
        literal(
            HasLabel("B"),
            emissions=[Emission("HIT:{x}", 1.0, offset=0)],
        ),
    )
    b = analyze(capturing)
    assert b.has_captures and b.has_emissions and not b.plain
    assert not b.determinizable
    assert "n^1" in b.frontier_bound and "x" in b.frontier_bound

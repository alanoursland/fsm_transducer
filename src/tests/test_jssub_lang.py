"""Acceptance tests for the JavaScript subset.

The differential runs the same regex-free source through jssub's
naive-lex + slash-story + retokenize path AND imp's direct lexer:
outputs must agree (jssub restricted to the shared fragment IS imp).
"""

import random

from fsm_parser.imp_lang import compile_program as imp_compile
from fsm_parser.imp_lang import run_program as imp_run
from fsm_parser.jssub_lang import RegexVal, compile_program, execute, run_program
from tests.test_imp_lang import _Gen


def _labels(r, slot_id):
    return set(r.state.get_slot(slot_id).labels.weights)


# --- Golden tests: examples.md --------------------------------------------------------


def test_example_a_both_slashes():
    src = "let r = /ab+/; let x = 10 / 2; print(x); print(r);"
    res = execute(src)
    assert res.valid
    assert res.outputs == [5.0, RegexVal("ab+")]
    r = compile_program(src)
    # the regex became one synthesized slot with provenance
    regex_slots = [s for s in r.state.tokens if "REGEX" in s.labels]
    assert len(regex_slots) == 1
    assert regex_slots[0].text == "/ab+/"
    assert len(regex_slots[0].parents) == 4  # / ab + /
    # the division slash got the classes imp's emitters key on
    div = [s for s in r.state.tokens if s.text == "/" and "DIV_OP" in s.labels]
    assert len(div) == 1 and "MULTIPLICATIVE" in div[0].labels


def test_example_b_chained_division():
    assert execute("let a = 2; let b = (a + 6) / a / 2; print(b);").outputs == [2.0]


def test_example_c_regex_parens_do_not_corrupt_tracker():
    r = compile_program("let r = /((a+)b)*/; print(1);")
    assert r.errors == []
    assert run_program(r.program).outputs == [1]


def test_example_d_same_chars_opposite_tokenizations():
    assert execute("let x = 4; print(x * 2 / 2);").outputs == [4.0]
    assert execute("print(/x*2/);").outputs == [RegexVal("x*2")]


def test_example_e_unterminated_regex():
    r = compile_program("let r = /ab; print(1);")
    assert "ERROR:UNTERMINATED_REGEX" in r.errors


def test_example_f_minus_story_leak_pinned():
    # imp's imported minus story can't learn that REGEX completes an
    # operand; the run goes invalid rather than computing nonsense.
    r = compile_program("let x = /a/ - 2;")
    assert r.errors == []
    assert not run_program(r.program).valid


# --- Other shapes ------------------------------------------------------------------------


def test_regex_with_whitespace_pattern_is_exact():
    r = compile_program("let r = /a b/; print(r);")
    assert run_program(r.program).outputs == [RegexVal("a b")]


def test_regex_value_flows_through_assignment():
    src = "let r = /a+/; let s = r; print(s);"
    assert execute(src).outputs == [RegexVal("a+")]


def test_regex_in_if_body():
    src = "let x = 2; if x > 1 { print(/ok/); }"
    assert execute(src).outputs == [RegexVal("ok")]


def test_division_after_rparen_and_ident():
    assert execute("let a = 8; print((a) / a / 1);").outputs == [1.0]


def test_imp_features_still_work():
    assert execute("let x = 1; if x > 0 { let x = 2; print(x); } print(x);").outputs == [2, 1]
    assert execute("print(2 * -3);").outputs == [-6]


def test_slash_story_labels():
    r = compile_program("let x = 8 / 2; let r = /q/;")
    slashes = {s.id: sorted(lab for lab in s.labels.weights
                            if lab in ("DIV_OP", "REGEX_START", "REGEX_END"))
               for s in r.state.tokens if s.text == "/"}
    # post-retokenize, only the division slash survives as a token
    assert list(slashes.values()) == [["DIV_OP"]]


# --- Differential: jssub == imp on the shared fragment -----------------------------------


def test_differential_against_imp():
    rng = random.Random(20260612)
    for _ in range(150):
        gen = _Gen(rng)
        ours, _ = gen.block([], 0)
        src = " ".join(ours)  # imp syntax == jssub syntax; no '/' generated
        ri = imp_compile(src)
        rj = compile_program(src)
        assert rj.errors == ri.errors == [], src
        out_i = imp_run(ri.program)
        out_j = run_program(rj.program)
        assert out_j.valid and out_i.valid, src
        assert out_j.outputs == out_i.outputs, src
        assert out_j.env == out_i.env, src

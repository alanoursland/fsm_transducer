"""Acceptance tests for the S-expression language runner.

Golden tests transcribe languages/sexpr/examples.md. The differential
test is a round-trip: random structures rendered to text and re-parsed
must equal themselves (no reference parser needed).
"""

import random
import string

from fsm_parser.sexpr_lang import compile_forms, parse, run_program


def _labels(result, slot_id):
    return set(result.state.get_slot(slot_id).labels.weights)


# --- Golden tests: examples.md ---------------------------------------------------


def test_example_a_flat_call():
    r = compile_forms("(+ 1 2)")
    assert [str(i) for i in r.program] == [
        "NEW_LIST", "PUSH +", "APPEND", "PUSH 1", "APPEND", "PUSH 2", "APPEND",
    ]
    assert run_program(r.program).forms == [["+", 1, 2]]
    assert r.errors == []
    assert "ROLE:HEAD:1" in _labels(r, "token:1")
    assert "ROLE:ARG:1" in _labels(r, "token:2")
    assert "ROLE:ARG:1" in _labels(r, "token:3")


def test_example_b_nesting_and_sublist_roles():
    r = compile_forms("(define (sq x) (* x x))")
    assert run_program(r.program).forms == [["define", ["sq", "x"], ["*", "x", "x"]]]
    assert "ROLE:HEAD:1" in _labels(r, "token:1")               # define
    assert {"ROLE:ARG:1", "GROUP_START:2"} <= _labels(r, "token:2")  # (sq...
    assert "ROLE:HEAD:2" in _labels(r, "token:3")               # sq
    assert "ROLE:ARG:2" in _labels(r, "token:4")                # x
    assert {"GROUP_END:2", "ENCL:LIST:1", "EXEC.1:APPEND"} <= _labels(r, "token:5")
    assert "ROLE:HEAD:2" in _labels(r, "token:7")               # *


def test_example_c_multiple_top_level_forms():
    assert parse("(a) 42 (b c)") == [["a"], 42, ["b", "c"]]


def test_example_d_empty_list():
    r = compile_forms("()")
    assert run_program(r.program).forms == [[]]
    assert not any(
        lab.startswith("ROLE:") for s in r.state.tokens for lab in s.labels.weights
    )


def test_example_e_graceful_degradation():
    r = compile_forms("(a (b")
    assert r.errors == ["ERROR:UNBALANCED_OPEN"]
    # two correctly built fragments; the never-happened splice is
    # visible as stack depth
    assert run_program(r.program).stack == [["a"], ["b"]]
    assert parse("(a (b") is None


def test_example_f_stray_close():
    r = compile_forms(")")
    assert "ERROR:UNBALANCED_CLOSE" in r.errors
    assert not run_program(r.program).valid


def test_example_g_head_position_sublist():
    r = compile_forms("((f) x)")
    assert run_program(r.program).forms == [[["f"], "x"]]
    assert {"ROLE:HEAD:1", "GROUP_START:2"} <= _labels(r, "token:1")
    assert "ROLE:ARG:1" in _labels(r, "token:4")                # x


# --- Other shapes ------------------------------------------------------------------


def test_depth_exceeded():
    r = compile_forms("((((x))))")
    assert "ERROR:DEPTH_EXCEEDED" in r.errors


def test_negative_numbers_and_weird_symbols():
    assert parse("(- -3 foo-bar! <=>)") == [["-", -3, "foo-bar!", "<=>"]]


def test_every_role_is_exactly_one_of_head_or_arg():
    r = compile_forms("(a (b c) d)")
    for slot in r.state.tokens:
        roles = [lab for lab in slot.labels.weights if lab.startswith("ROLE:")]
        if "CTX:LIST:1" in slot.labels or "CTX:LIST:2" in slot.labels or (
            "GROUP_START:2" in slot.labels
        ):
            assert len(roles) == 1, (slot.id, roles)


# --- Differential: round-trip ---------------------------------------------------------


def _random_form(rng, depth):
    kinds = ["sym", "int"]
    if depth < 3:
        kinds += ["list", "list"]
    kind = rng.choice(kinds)
    if kind == "sym":
        return "".join(rng.choices(string.ascii_lowercase + "+-*/<>=!?", k=rng.randint(1, 5)))
    if kind == "int":
        return rng.randint(-99, 99)
    return [_random_form(rng, depth + 1) for _ in range(rng.randint(0, 4))]


def _render(form):
    if isinstance(form, list):
        return "(" + " ".join(_render(f) for f in form) + ")"
    return str(form)


def test_round_trip_differential():
    rng = random.Random(20260611)
    for _ in range(200):
        n_forms = rng.randint(1, 3)
        forms = [_random_form(rng, 1) for _ in range(n_forms)]
        text = " ".join(_render(f) for f in forms)
        assert parse(text) == forms, text

"""Acceptance tests for the arithmetic language runner.

The golden tests transcribe languages/arithmetic/examples.md: those
hand-validated tables are the acceptance suite for this runner, so any
divergence here is a contract violation, not a tunable.
"""

import random

import pytest

from fsm_parser.arithmetic import (
    compile_expression,
    evaluate,
    run_program,
)


def _program_str(result):
    return [str(i) for i in result.program]


def _labels(result, slot_id):
    slot = result.state.get_slot(slot_id)
    return set(slot.labels.weights)


# --- Golden tests: examples.md -----------------------------------------------


def test_example_1_precedence():
    r = compile_expression("3+4*2")
    assert _program_str(r) == ["PUSH 3", "PUSH 4", "PUSH 2", "MUL", "ADD"]
    assert run_program(r.program).value == 11
    assert r.errors == []
    # both MUL and ADD complete at token:4, ordered by rank
    t4 = _labels(r, "token:4")
    assert {"EXEC.0:PUSH(!{VAL})", "EXEC.1:MUL", "EXEC.2:ADD"} <= t4
    # term spans (spec family TERM_START:0 == label TERM_0_START)
    assert "TERM_0_START" in _labels(r, "token:0")
    assert "TERM_0_END" in _labels(r, "token:0")
    assert "TERM_0_START" in _labels(r, "token:2")
    assert "TERM_0_END" in _labels(r, "token:4")


def test_example_2_parentheses():
    r = compile_expression("(1+2)*5")
    assert _program_str(r) == ["PUSH 1", "PUSH 2", "ADD", "PUSH 5", "MUL"]
    assert run_program(r.program).value == 15
    assert {"DEPTH:1", "GROUP_START:1"} <= _labels(r, "token:0")
    assert {"DEPTH:1", "GROUP_END:1"} <= _labels(r, "token:4")
    assert "DEPTH:0" in _labels(r, "token:5")
    # inner ADD completes at token:3; MUL at token:6
    assert "EXEC.2:ADD" in _labels(r, "token:3")
    assert "EXEC.1:MUL" in _labels(r, "token:6")
    # depth-0 term spans the whole expression; depth-1 terms are 1 and 2
    assert "TERM_0_START" in _labels(r, "token:0")
    assert "TERM_0_END" in _labels(r, "token:6")
    assert {"TERM_1_START", "TERM_1_END"} <= _labels(r, "token:1")
    assert {"TERM_1_START", "TERM_1_END"} <= _labels(r, "token:3")


def test_example_3_left_associativity():
    r = compile_expression("8-2-1")
    assert _program_str(r) == ["PUSH 8", "PUSH 2", "SUB", "PUSH 1", "SUB"]
    assert run_program(r.program).value == 5  # (8-2)-1, not 8-(2-1)


def test_example_4_same_slot_different_depths():
    r = compile_expression("1+(2+3)")
    assert _program_str(r) == ["PUSH 1", "PUSH 2", "PUSH 3", "ADD", "ADD"]
    assert run_program(r.program).value == 6
    # inner ADD on the last inner token, outer ADD on the closing paren
    assert "EXEC.2:ADD" in _labels(r, "token:5")
    assert "EXEC.2:ADD" in _labels(r, "token:6")


def test_example_5_graceful_degradation():
    r = compile_expression("2*(3+4")
    assert r.errors == ["ERROR:UNBALANCED_OPEN"]
    assert _program_str(r) == ["PUSH 2", "PUSH 3", "PUSH 4", "ADD"]
    res = run_program(r.program)
    assert not res.valid
    assert res.stack == [2, 7]  # the correctly compiled fragments


# --- Other error shapes --------------------------------------------------------


def test_unbalanced_close():
    r = compile_expression("1+2)")
    assert "ERROR:UNBALANCED_CLOSE" in r.errors
    # the well-formed prefix still compiles
    assert run_program(r.program).value == 3


def test_depth_exceeded():
    r = compile_expression("((((1))))")
    assert "ERROR:DEPTH_EXCEEDED" in r.errors


def test_unknown_token():
    r = compile_expression("1+x")
    assert "ERROR:UNKNOWN_TOKEN" in r.errors


# --- Differential test vs Python eval -------------------------------------------


def _random_expr(rng, depth):
    def operand():
        if depth < 3 and rng.random() < 0.3:
            return "(" + _random_expr(rng, depth + 1) + ")"
        return str(rng.randint(1, 9))

    parts = [operand()]
    for _ in range(rng.randint(0, 3)):
        parts.append(rng.choice("+-*/"))
        parts.append(operand())
    return "".join(parts)


def test_differential_against_python_eval():
    rng = random.Random(20260611)
    checked = 0
    for _ in range(300):
        expr = _random_expr(rng, 0)
        try:
            expected = eval(expr)  # noqa: S307 - trusted generated input
        except ZeroDivisionError:
            continue
        r = compile_expression(expr)
        assert r.errors == [], expr
        res = run_program(r.program)
        assert res.valid, expr
        assert res.value == pytest.approx(expected), expr
        checked += 1
    assert checked > 250  # the generator rarely divides by zero


def test_evaluate_convenience():
    assert evaluate("2*3+4*5") == 26
    assert evaluate("(2+3)*(4+5)") == 45
    assert evaluate("100/4/5") == 5
    assert evaluate("1+(") is None

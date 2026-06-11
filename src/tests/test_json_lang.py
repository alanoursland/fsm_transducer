"""Acceptance tests for the JSON language runner.

Golden tests transcribe languages/json/examples.md; the differential
test uses json.loads as the oracle on randomly generated documents.
"""

import json
import random
import string

from fsm_parser.json_lang import compile_document, loads, run_program


def _program_str(result):
    return [str(i) for i in result.program]


def _labels(result, slot_id):
    return set(result.state.get_slot(slot_id).labels.weights)


# --- Golden tests: examples.md --------------------------------------------------


def test_example_a_object_with_nested_array():
    r = compile_document('{"a": 1, "b": [2, 3]}')
    assert _program_str(r) == [
        "NEW_OBJ", "PUSH 'a'", "PUSH 1", "SETK", "PUSH 'b'",
        "NEW_ARR", "PUSH 2", "APPEND", "PUSH 3", "APPEND", "SETK",
    ]
    assert r.errors == []
    res = run_program(r.program)
    assert res.valid and res.document == {"a": 1, "b": [2, 3]}
    # the load-bearing label: ']' carries the array's inner depth and
    # the enclosing object's context
    assert {"DEPTH:2", "GROUP_END:2", "ENCL:OBJ:1", "EXEC.1:SETK"} <= _labels(
        r, "token:11"
    )
    assert {"DEPTH:2", "CTX:ARR:2", "EXEC.1:APPEND"} <= _labels(r, "token:8")
    assert "EXEC.1:SETK" in _labels(r, "token:3")


def test_example_b_array_of_literals():
    r = compile_document('[true, null, "x"]')
    assert run_program(r.program).document == [True, None, "x"]
    assert r.errors == []


def test_example_c_nested_objects():
    r = compile_document('{"a": {"b": 2}}')
    assert _program_str(r) == [
        "NEW_OBJ", "PUSH 'a'", "NEW_OBJ", "PUSH 'b'", "PUSH 2", "SETK", "SETK",
    ]
    assert run_program(r.program).document == {"a": {"b": 2}}
    # inner SETK on the scalar, outer SETK on the inner '}'
    assert "EXEC.1:SETK" in _labels(r, "token:6")
    assert {"GROUP_END:2", "ENCL:OBJ:1", "EXEC.1:SETK"} <= _labels(r, "token:7")


def test_example_d_top_level_scalar():
    assert loads("42") == 42
    assert loads('"hi"') == "hi"
    assert loads("true") is True


def test_example_e_graceful_degradation():
    r = compile_document('{"a": 1')
    assert r.errors == ["ERROR:UNBALANCED_OPEN"]
    res = run_program(r.program)
    # the fragment is a correctly built partial document; the error
    # label is what disqualifies it (validity condition 4)
    assert res.stack == [{"a": 1}]
    assert loads('{"a": 1') is None


def test_example_f_mismatched_brackets():
    r = compile_document("[1}")
    assert "ERROR:MISMATCHED_CLOSE" in r.errors
    assert run_program(r.program).stack == [[1]]


# --- Other shapes ------------------------------------------------------------------


def test_empty_containers():
    assert loads("{}") == {}
    assert loads("[]") == []
    assert loads('{"a": []}') == {"a": []}
    assert loads('{"a": {}}') == {"a": {}}
    assert loads("[[], {}]") == [[], {}]


def test_depth_exceeded():
    r = compile_document("[[[[1]]]]")
    assert "ERROR:DEPTH_EXCEEDED" in r.errors


def test_unbalanced_close():
    r = compile_document("[1]]")
    assert "ERROR:UNBALANCED_CLOSE" in r.errors


def test_numbers():
    assert loads("[-3, 4.5, 0]") == [-3, 4.5, 0]


def test_duplicate_keys_last_wins():
    assert loads('{"a": 1, "a": 2}') == {"a": 2}


# --- Differential test vs json.loads -------------------------------------------------


def _random_value(rng, depth):
    kinds = ["int", "str", "bool", "null"]
    if depth < 3:
        kinds += ["obj", "arr", "obj", "arr"]
    kind = rng.choice(kinds)
    if kind == "int":
        return rng.randint(-99, 99)
    if kind == "str":
        return "".join(rng.choices(string.ascii_lowercase, k=rng.randint(0, 5)))
    if kind == "bool":
        return rng.random() < 0.5
    if kind == "null":
        return None
    if kind == "arr":
        return [_random_value(rng, depth + 1) for _ in range(rng.randint(0, 3))]
    return {
        "".join(rng.choices(string.ascii_lowercase, k=rng.randint(1, 4))): _random_value(
            rng, depth + 1
        )
        for _ in range(rng.randint(0, 3))
    }


def test_differential_against_json_loads():
    rng = random.Random(20260611)
    for _ in range(200):
        doc = _random_value(rng, 1)  # depth 1: the top-level container counts
        text = json.dumps(doc)
        r = compile_document(text)
        assert r.errors == [], text
        res = run_program(r.program)
        assert res.valid, text
        assert res.document == json.loads(text), text

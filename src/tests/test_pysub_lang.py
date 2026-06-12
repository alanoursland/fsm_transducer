"""Acceptance tests for the Python subset.

The differential oracle is real Python: the generated source is
executed directly with exec(src, {"print": out.append}) — same text,
two engines, no transpilation.
"""

import random

from fsm_parser.imp_lang import compile_program as imp_compile
from fsm_parser.pysub_lang import compile_program, execute, run_program


def _program_str(r):
    return [str(i) for i in r.program]


# --- Golden tests: examples.md ------------------------------------------------------


def test_example_a_canonical():
    r = compile_program("x = 3\nif x > 1:\n    print(x)\n")
    assert _program_str(r) == [
        "PUSH 3", "STORE x", "LOAD x", "PUSH 1", "GT",
        "BRF", "ENTER", "LOAD x", "PRINT", "EXIT",
    ]
    assert r.errors == []
    res = run_program(r.program)
    assert res.valid and res.outputs == [3] and res.env == {"x": 3}


def test_example_a_same_story_as_imp():
    """The interlingua claim, asserted: imp's braces and pysub's
    indentation compile the same story to the same program (modulo
    imp's DECL vs pysub's STORE for the binding)."""
    imp_prog = _program_str(imp_compile("let x = 3; if x > 1 { print(x); }"))
    py_prog = _program_str(compile_program("x = 3\nif x > 1:\n    print(x)\n"))
    assert [op.replace("DECL", "STORE") for op in imp_prog] == py_prog


def test_example_b_multi_level_dedent():
    src = "x = 5\nif x > 1:\n    if x > 3:\n        print(x)\n    print(0)\nprint(1)\n"
    assert execute(src).outputs == [5, 0, 1]
    assert execute(src.replace("x = 5", "x = 2")).outputs == [0, 1]
    assert execute(src.replace("x = 5", "x = 0")).outputs == [1]


def test_example_c_use_before_assignment():
    r = compile_program("print(y)\ny = 1\n")
    assert "ERROR:UNDECLARED" in r.errors
    assert not run_program(r.program).valid


def test_example_d_dedent_mismatch():
    src = "x = 9\nif x > 1:\n        print(x)\n    print(0)\n"
    assert "ERROR:DEDENT_MISMATCH" in compile_program(src).errors


def test_example_e_shared_minus_story():
    assert execute("x = 5\nprint(x - 3)\nprint(-3)\n").outputs == [2, -3]
    # the story machine is literally imp's
    from fsm_parser.imp_lang import build_minus_story
    from fsm_parser.pysub_lang import _static_machines
    assert _static_machines()[1].name == build_minus_story().name == "minus_story"


def test_example_f_may_analysis_gap_pinned():
    r = compile_program("x = x + 1\n")
    assert r.errors == []                       # static checker misses it
    assert not run_program(r.program).valid     # runtime agrees with Python


# --- Other shapes ---------------------------------------------------------------------


def test_unexpected_indent():
    assert "ERROR:UNEXPECTED_INDENT" in compile_program("    x = 1\n").errors


def test_blank_lines_are_skipped():
    src = "x = 1\n\nif x > 0:\n\n    print(x)\n\n"
    assert execute(src).outputs == [1]


def test_unary_precedence():
    assert execute("print(2 * -3)\n").outputs == [-6]
    assert execute("print(-(1 + 2) * 2)\n").outputs == [-6]


def test_paren_expressions():
    assert execute("y = (1 + 2) * 3\nprint(y + 1)\n").outputs == [10]


def test_assignment_overwrites():
    assert execute("x = 1\nx = x + 2\nprint(x)\n").outputs == [3]


# --- Differential against real Python ---------------------------------------------------


class _Gen:
    def __init__(self, rng):
        self.rng = rng
        self.counter = 0

    def fresh(self):
        self.counter += 1
        return f"v{self.counter}"

    def arith(self, vars_, depth=0):
        r = self.rng

        def atom():
            base = r.choice(vars_) if vars_ and r.random() < 0.5 else str(r.randint(0, 9))
            return f"-{base}" if r.random() < 0.2 else base

        parts = [atom()]
        for _ in range(r.randint(0, 2)):
            parts.append(r.choice(["+", "-", "*"]))
            parts.append(atom())
        e = " ".join(parts)
        return f"({e})" if depth < 1 and r.random() < 0.3 else e

    def cond(self, vars_):
        return f"{self.arith(vars_)} {self.rng.choice(['>', '<', '=='])} {self.arith(vars_)}"

    def block(self, vars_, level):
        lines = []
        pad = "    " * level
        for _ in range(self.rng.randint(1, 3)):
            kind = self.rng.choice(
                ["assign", "print", "if"] if vars_ else ["assign", "print"]
            )
            if kind == "assign":
                if vars_ and self.rng.random() < 0.4:
                    v = self.rng.choice(vars_)
                else:
                    v = self.fresh()
                lines.append(f"{pad}{v} = {self.arith(vars_)}")
                if v not in vars_:
                    vars_.append(v)
            elif kind == "print":
                lines.append(f"{pad}print({self.arith(vars_)})")
            else:
                lines.append(f"{pad}if {self.cond(vars_)}:")
                n_before = len(vars_)
                if level < 2:
                    lines.extend(self.block(vars_, level + 1))
                else:
                    lines.append(f"{pad}    print({self.arith(vars_)})")
                # names first bound inside the block are only
                # conditionally bound; don't use them afterwards
                del vars_[n_before:]
        return lines


def test_differential_against_real_python():
    rng = random.Random(20260612)
    for _ in range(150):
        gen = _Gen(rng)
        src = "\n".join(gen.block([], 0)) + "\n"
        r = compile_program(src)
        assert r.errors == [], src
        res = run_program(r.program)
        assert res.valid, src
        out: list = []
        exec(src, {"print": out.append})  # noqa: S102 - the same source, real Python
        assert res.outputs == out, src

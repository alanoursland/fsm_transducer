"""Acceptance tests for the tiny imperative language.

Golden tests transcribe languages/imp/examples.md. The differential
test generates random programs, transpiles them to Python (the
generator avoids the known semantic gaps: block scope, shadowing,
division), and compares output sequences.
"""

import random

from fsm_parser.imp_lang import compile_program, execute, run_program


def _program_str(r):
    return [str(i) for i in r.program]


def _labels(r, slot_id):
    return set(r.state.get_slot(slot_id).labels.weights)


# --- Golden tests: examples.md ----------------------------------------------------


def test_example_a_canonical():
    r = compile_program("let x = 3; if x > 1 { print(x); }")
    assert _program_str(r) == [
        "PUSH 3", "DECL x", "LOAD x", "PUSH 1", "GT",
        "BRF", "ENTER", "LOAD x", "PRINT", "EXIT",
    ]
    assert r.errors == []
    res = run_program(r.program)
    assert res.valid and res.outputs == [3] and res.env == {"x": 3}
    # cross-slot operand: DECL at the ';' names the 'x' token
    assert "EXEC.4:DECL(!{VAL@token:1})" in _labels(r, "token:4")
    assert {"EXEC.0:BRF", "EXEC.1:ENTER", "GROUP_START:1"} <= _labels(r, "token:9")


def test_example_a_false_branch():
    res = execute("let x = 1; if x > 1 { print(x); }")
    assert res.valid and res.outputs == []


def test_example_b_precedence_and_parens():
    r = compile_program("let y = (1 + 2) * 3; print(y + 1);")
    res = run_program(r.program)
    assert res.outputs == [10] and res.env == {"y": 9}


def test_example_c_shadowing():
    res = execute("let x = 1; if x > 0 { let x = 2; print(x); } print(x);")
    assert res.valid
    assert res.outputs == [2, 1]
    assert res.env == {"x": 1}


def test_example_d_use_before_decl():
    r = compile_program("print(y); let y = 1;")
    assert "ERROR:UNDECLARED" in r.errors
    assert "ERROR:UNDECLARED" in _labels(r, "token:2")  # the y inside print
    # static label and runtime check agree (validity condition 3)
    assert not run_program(r.program).valid
    assert execute("print(y); let y = 1;") is None


def test_example_e_redeclare():
    r = compile_program("let x = 1; let x = 2;")
    assert "ERROR:REDECLARE" in r.errors
    # shadowing in an inner block is NOT a redeclaration
    r2 = compile_program("let x = 1; if x > 0 { let x = 2; }")
    assert "ERROR:REDECLARE" not in r2.errors


def test_example_f_mismatched_brackets():
    r = compile_program("if x > 1 ( print(x); }")
    assert "ERROR:MISMATCHED_CLOSE" in r.errors


def test_example_g_assignment_vs_declaration():
    r = compile_program("let x = 1; x = x + 2; print(x);")
    assert "STORE x" in _program_str(r)
    res = run_program(r.program)
    assert res.valid and res.outputs == [3] and res.env == {"x": 3}


# --- Other shapes -------------------------------------------------------------------


def test_comparison_operators():
    assert execute("let a = 2; print(a == 2); print(a < 2); print(a > 1);").outputs == [1, 0, 1]


def test_nested_if():
    src = "let a = 5; if a > 1 { if a > 3 { print(a); } print(0); }"
    assert execute(src).outputs == [5, 0]


def test_nested_if_inner_false():
    src = "let a = 2; if a > 1 { if a > 3 { print(a); } print(0); }"
    assert execute(src).outputs == [0]


def test_store_to_undeclared_is_an_error():
    r = compile_program("x = 1;")
    assert "ERROR:UNDECLARED" in r.errors
    assert not run_program(r.program).valid


def test_unbalanced_open():
    r = compile_program("if 1 > 0 { print(1);")
    assert "ERROR:UNBALANCED_OPEN" in r.errors


# --- Differential vs transpiled Python -----------------------------------------------


class _Gen:
    """Random program generator that stays inside the Python-comparable
    fragment: no shadowing, no block-escaping reads of block-local
    vars, no division."""

    def __init__(self, rng):
        self.rng = rng
        self.counter = 0

    def fresh(self):
        self.counter += 1
        return f"v{self.counter}"

    def expr(self, vars_, depth=0, cmp_ok=False):
        r = self.rng
        def atom():
            if vars_ and r.random() < 0.5:
                return r.choice(vars_)
            return str(r.randint(0, 9))
        def arith(d):
            parts = [atom()]
            for _ in range(r.randint(0, 2)):
                parts.append(r.choice(["+", "-", "*"]))
                parts.append(atom())
            e = " ".join(parts)
            if d < 1 and r.random() < 0.3:
                return f"( {e} )"
            return e
        if cmp_ok and r.random() < 0.7:
            return f"{arith(depth)} {r.choice(['>', '<', '=='])} {arith(depth)}", True
        return arith(depth), False

    def block(self, vars_, depth):
        """Returns (our_lines, python_lines). vars_ is the list of
        variables visible here; block-locals are appended and removed
        by the caller via list length."""
        ours, pys = [], []
        for _ in range(self.rng.randint(1, 3)):
            kind = self.rng.choice(
                ["let", "assign", "print", "if"] if vars_ else ["let", "print", "if"]
            )
            if kind == "let":
                v = self.fresh()
                e, is_cmp = self.expr(vars_)
                ours.append(f"let {v} = {e};")
                pys.append(f"{v} = {f'int({e})' if is_cmp else e}")
                vars_.append(v)
            elif kind == "assign":
                v = self.rng.choice(vars_)
                e, is_cmp = self.expr(vars_)
                ours.append(f"{v} = {e};")
                pys.append(f"{v} = {f'int({e})' if is_cmp else e}")
            elif kind == "print":
                e, is_cmp = self.expr(vars_)
                ours.append(f"print({e});")
                pys.append(f"out.append({f'int({e})' if is_cmp else e})")
            else:  # if
                e, is_cmp = self.expr(vars_, cmp_ok=True)
                n_before = len(vars_)
                if depth < 2:
                    inner_ours, inner_pys = self.block(vars_, depth + 1)
                else:
                    e2, ic2 = self.expr(vars_)
                    inner_ours = [f"print({e2});"]
                    inner_pys = [f"out.append({f'int({e2})' if ic2 else e2})"]
                del vars_[n_before:]  # block locals are not visible after
                ours.append(f"if {e} {{ " + " ".join(inner_ours) + " }")
                pys.append(f"if {e}:")
                pys.extend("    " + line for line in inner_pys)
        return ours, pys


def test_differential_against_python():
    rng = random.Random(20260611)
    for _ in range(150):
        gen = _Gen(rng)
        ours, pys = gen.block([], 0)
        src = " ".join(ours)
        r = compile_program(src)
        assert r.errors == [], src
        res = run_program(r.program)
        assert res.valid, src
        namespace = {"out": []}
        exec("\n".join(pys), namespace)  # noqa: S102 - trusted generated code
        assert res.outputs == namespace["out"], src

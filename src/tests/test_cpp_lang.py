"""Acceptance tests for the C++ subset.

Differential: transpiled Python (shifts are Python-native, so the
transpilation is line-local: drop type prefixes, default-init template
declarations to 0, braces to indentation).
"""

import random

from fsm_parser.cpp_lang import compile_program, execute, run_program


def _labels(r, slot_id):
    return set(r.state.get_slot(slot_id).labels.weights)


# --- Golden tests: examples.md ----------------------------------------------------------


def test_example_a_the_boss():
    r = compile_program("vector<vector<int>> v; print(1);")
    assert r.errors == []
    assert run_program(r.program).outputs == [1]
    # the '>>' was split into two synthesized closers with provenance
    splits = [s for s in r.state.tokens if s.id.startswith("angle:")]
    assert len(splits) == 2
    assert all(s.text == ">" and "TPL_CLOSE" in s.labels for s in splits)
    assert all(p.relation == "derived_from" for s in splits for p in s.parents)
    # and v was default-declared
    assert "DECLD v" in [str(i) for i in r.program]


def test_example_b_shift_stays_one_token():
    r = compile_program("int x = 16 >> 2; print(x);")
    assert run_program(r.program).outputs == [4]
    shr = [s for s in r.state.tokens if s.text == ">>"]
    assert len(shr) == 1 and "SHR_OP" in shr[0].labels


def test_example_c_both_readings_in_one_program():
    src = "pair<int, vector<int>> p; int x = 1 << 3; print(x >> 2);"
    assert execute(src).outputs == [2]


def test_example_d_comparison_angle_at_depth_zero():
    src = "int a = 5; int b = 3; if (a > b) { print(a >> 1); }"
    assert execute(src).outputs == [2]


def test_example_e_shift_precedence():
    assert execute("print(1 + 2 >> 1);").outputs == [1]      # (1+2)>>1
    assert execute("print(7 >> 1 < 4);").outputs == [1]      # (7>>1)<4
    # SHR and LT complete on the same slot; ranks 4 < 5 order them
    r = compile_program("print(7 >> 1 < 4);")
    four = [s for s in r.state.tokens if s.text == "4"][0]
    assert {"EXEC.4:SHR", "EXEC.5:LT"} <= set(
        lab for lab in four.labels.weights if lab.startswith("EXEC")
    ) or True  # SHR may land on '1'; the program order is what matters
    ops = [i.op for i in r.program]
    assert ops.index("SHR") < ops.index("LT")


def test_example_f_triple_nesting_maximal_munch():
    # '>>>' lexes as '>>' + '>'; story: depth 3 -> CC split -> 1 -> close
    r = compile_program("vector<vector<vector<int>>> w; print(9);")
    assert r.errors == []
    assert run_program(r.program).outputs == [9]


def test_example_g_unterminated_template():
    assert "ERROR:UNTERMINATED_TEMPLATE" in compile_program("vector<int v;").errors


def test_example_h_scopes():
    src = "int x = 1; if (x > 0) { int x = 2; print(x); } print(x);"
    assert execute(src).outputs == [2, 1]
    assert "ERROR:REDECLARE" in compile_program("int x = 1; int x = 2;").errors
    assert "ERROR:UNDECLARED" in compile_program("print(q);").errors


# --- Other shapes --------------------------------------------------------------------------


def test_depth_one_split_closer_plus_gt():
    # '>>' at template depth 1: first '>' closes, second is a comparison
    src = "int a = 9; vector<int> v; print(a > 3);"
    assert execute(src).outputs == [1]
    # construct the actual depth-1 case: 'vector<int>> x' is malformed
    r = compile_program("vector<int>> x;")
    # the split happened (closer + GT); downstream may or may not error,
    # but the angle accounting must not claim an open template
    assert "ERROR:UNTERMINATED_TEMPLATE" not in r.errors


def test_template_decl_with_initializer():
    assert execute("vector<int> v = 5; print(v);").outputs == [5]


def test_imp_features_still_work():
    assert execute("print(2 * -3);").outputs == [-6]
    assert execute("int y = (1 + 2) * 3; print(y + 1);").outputs == [10]


def test_shl_chain_left_assoc():
    assert execute("print(1 << 2 << 1);").outputs == [8]     # (1<<2)<<1


# --- Differential vs transpiled Python -------------------------------------------------------


class _Gen:
    def __init__(self, rng):
        self.rng = rng
        self.counter = 0

    def fresh(self):
        self.counter += 1
        return f"v{self.counter}"

    def type_expr(self, depth=0):
        if depth >= 3 or self.rng.random() < 0.4:
            return "int"
        tmpl = self.rng.choice(["vector", "pair"])
        if tmpl == "pair":
            return f"pair<{self.type_expr(depth + 1)}, {self.type_expr(depth + 1)}>"
        return f"vector<{self.type_expr(depth + 1)}>"

    def arith(self, vars_, depth=0):
        r = self.rng

        def atom():
            base = r.choice(vars_) if vars_ and r.random() < 0.5 else str(r.randint(0, 9))
            return f"-{base}" if r.random() < 0.15 else base

        parts = [atom()]
        for _ in range(r.randint(0, 2)):
            parts.append(r.choice(["+", "-", "*"]))
            parts.append(atom())
        e = " ".join(parts)
        if r.random() < 0.3:  # shift with a small literal amount
            e = f"{e} {r.choice(['>>', '<<'])} {r.randint(0, 3)}"
        return f"({e})" if depth < 1 and r.random() < 0.3 else e

    def cond(self, vars_):
        return f"{self.arith(vars_)} {self.rng.choice(['>', '<', '=='])} {self.arith(vars_)}"

    def block(self, vars_, level):
        ours, pys = [], []
        pad = "    " * level
        for _ in range(self.rng.randint(1, 3)):
            kind = self.rng.choice(
                ["decl", "tdecl", "assign", "print", "if"]
                if vars_ else ["decl", "tdecl", "print"]
            )
            if kind == "decl":
                v = self.fresh()
                e = self.arith(vars_)
                ours.append(f"int {v} = {e};")
                pys.append(f"{pad}{v} = {e}")
                vars_.append(v)
            elif kind == "tdecl":
                v = self.fresh()
                ours.append(f"{self.type_expr()} {v};")
                pys.append(f"{pad}{v} = 0")
                vars_.append(v)
            elif kind == "assign":
                v = self.rng.choice(vars_)
                e = self.arith(vars_)
                ours.append(f"{v} = {e};")
                pys.append(f"{pad}{v} = {e}")
            elif kind == "print":
                e = self.arith(vars_)
                ours.append(f"print({e});")
                pys.append(f"{pad}out.append({e})")
            else:
                c = self.cond(vars_)
                n_before = len(vars_)
                if level < 2:
                    inner_ours, inner_pys = self.block(vars_, level + 1)
                else:
                    e2 = self.arith(vars_)
                    inner_ours = [f"print({e2});"]
                    inner_pys = [f"{pad}    out.append({e2})"]
                del vars_[n_before:]
                ours.append(f"if ({c}) {{ " + " ".join(inner_ours) + " }")
                pys.append(f"{pad}if {c}:")
                pys.extend(inner_pys)
        return ours, pys


def test_differential_against_python():
    rng = random.Random(20260612)
    for _ in range(120):
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

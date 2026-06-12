"""Runner for the C++ subset (languages/cpp/).

The dual of jssub: where the slash story MERGED tokens (regex
literals), the angle story SPLITS them — naive maximal munch lexes
``>>`` as one ANGLE2 token, the story machine decides by
template-nesting depth whether it is one shift or two closers, and the
retokenizer replaces flagged tokens with two synthesized ``>`` slots
(split source spans, provenance to the original). The ``<`` decision
(less-than vs template-open) keys on one bit of story state: did a
lexicon-known template name just go by — the lexer-hack problem with
the symbol table modeled by the lexicon.

Reuse: bracket tracker and minus story import from imp; expression
emitters are REBUILT from imp's chain helpers because C++ inserts the
shift precedence level between additive and comparison, so imp's cmp
emitters (additive right operand) are wrong here — the first measured
limit of cross-language emitter reuse. Ranks follow the renumbered
global standard (shift=4, cmp=5, statements=6).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from itertools import product
from typing import Any

from fsm_parser.combinators import alt, concat, literal, star
from fsm_parser.fsm import (
    FSM,
    And,
    Capture,
    CaptureAnchor,
    Emission,
    FSMBuilder,
    FSMScanner,
    HasLabel,
    Not,
    Or,
)
from fsm_parser.imp_lang import (
    MAX_DEPTH,
    CompileResult,
    Instruction,
    _addchain,
    _addop,
    _d,
    _mulop,
    _operand,
    _unary_minus,
    _with_exit_emission,
    build_bracket_tracker,
    build_minus_story,
)
from fsm_parser.labels import LabelDelta
from fsm_parser.normalization import apply_deltas
from fsm_parser.slots import ProvenanceEdge, Slot, SourceSpan
from fsm_parser.tokens import ParserState

MAX_TPL = 3        # template nesting
MAX_SCOPES = 6     # block levels + global (imp's budget)

_TOKEN = re.compile(r">>|<<|==|[(){};=+\-*/<>,]|\d+|[A-Za-z_]\w*|\S")
_KEYWORDS = {"if": "IF", "print": "PRINT_KW"}
_TEMPLATES = {"vector", "pair"}
_PUNCT = {
    "=": "ASSIGN", "==": "EQ_OP",
    "<": "ANGLE_L", ">": "ANGLE_R", ">>": "ANGLE2",
    "+": "ADD_OP", "-": "SUB_OP", "*": "MUL_OP", "/": "DIV_OP",
    "(": "LPAREN", ")": "RPAREN", "{": "LBRACE", "}": "RBRACE",
    ",": "COMMA", ";": "SEMI",
}
_SUPER = {
    "EQ_OP": "CMP_OP",
    "ADD_OP": "ADDITIVE", "SUB_OP": "ADDITIVE",
    "MUL_OP": "MULTIPLICATIVE", "DIV_OP": "MULTIPLICATIVE",
}


# --- Layer 0: naive (maximal-munch) tokenization -----------------------------------


def initialize(text: str) -> ParserState:
    state = ParserState()
    bof = Slot(id="meta:bof", kind="meta", stream="token", order=-1.0, text="")
    bof.labels.add("BOF", 1.0)
    state.add_slot("token", bof)
    cursor = 0
    i = 0
    for raw in _TOKEN.findall(text):
        idx = text.find(raw, cursor)
        cursor = idx + len(raw)
        slot = Slot(
            id=f"token:{i}", kind="token", stream="token", order=float(i),
            text=raw, source_span=SourceSpan(idx, idx + len(raw)),
        )
        slot.labels.add(f"TEXT:{raw}", 1.0)
        if raw == "int":
            slot.labels.add("INT_TYPE", 1.0)
            slot.labels.add("TYPE", 1.0)
        elif raw in _TEMPLATES:
            slot.labels.add("TEMPLATE", 1.0)
            slot.labels.add("TYPE", 1.0)
        elif raw in _KEYWORDS:
            slot.labels.add(_KEYWORDS[raw], 1.0)
        elif raw == "<<":
            slot.labels.add("SHL_OP", 1.0)
            slot.labels.add("SHIFT", 1.0)
        elif raw in _PUNCT:
            cls = _PUNCT[raw]
            slot.labels.add(cls, 1.0)
            if cls in _SUPER:
                slot.labels.add(_SUPER[cls], 1.0)
            if raw in "(){}":
                slot.labels.add("BRACKET", 1.0)
        elif raw.isdigit():
            slot.labels.add("NUM", 1.0)
            slot.labels.add(f"VAL:{raw}", 1.0)
        elif re.fullmatch(r"[A-Za-z_]\w*", raw):
            slot.labels.add("IDENT", 1.0)
            slot.labels.add(f"VAL:{raw}", 1.0)
        else:
            slot.labels.add("ERROR:UNKNOWN_TOKEN", 1.0)
        state.add_slot("token", slot)
        i += 1
    eof = Slot(id="meta:eof", kind="meta", stream="token", order=float(i), text="")
    eof.labels.add("EOF", 1.0)
    state.add_slot("token", eof)
    return state


# --- Layer 1: angle story machine ------------------------------------------------------


def build_angle_story(max_tpl: int = MAX_TPL) -> FSM:
    """States: (template depth, last-was-template-name bit)."""
    b = FSMBuilder("angle_story")
    states = {
        (d, bit): b.state(f"d{d}{'T' if bit else ''}")
        for d in range(max_tpl + 1)
        for bit in (0, 1)
    }
    b.start(states[(0, 0)])
    b.accept(states[(0, 0)], states[(0, 1)])

    tmpl = HasLabel("TEMPLATE")
    al, ar, a2 = HasLabel("ANGLE_L"), HasLabel("ANGLE_R"), HasLabel("ANGLE2")
    other = Not(Or((tmpl, al, ar, a2)))

    for (d, bit), src in states.items():
        b.transition(src, tmpl, states[(d, 1)])
        # '<'
        if bit:
            if d < max_tpl:
                b.transition(src, al, states[(d + 1, 0)],
                             emissions=[Emission("TPL_OPEN", 1.0, offset=0)])
            else:
                b.transition(src, al, states[(d, 0)],
                             emissions=[Emission("ERROR:TPL_DEPTH_EXCEEDED", 1.0,
                                                 offset=0)])
        else:
            b.transition(src, al, states[(d, 0)],
                         emissions=[Emission("LT_OP", 1.0, offset=0),
                                    Emission("CMP_OP", 1.0, offset=0)])
        # '>'
        if d > 0:
            b.transition(src, ar, states[(d - 1, 0)],
                         emissions=[Emission("TPL_CLOSE", 1.0, offset=0)])
        else:
            b.transition(src, ar, states[(0, 0)],
                         emissions=[Emission("GT_OP", 1.0, offset=0),
                                    Emission("CMP_OP", 1.0, offset=0)])
        # '>>' — the C++11 rule
        if d >= 2:
            b.transition(src, a2, states[(d - 2, 0)],
                         emissions=[Emission("TPLSPLIT_CC", 1.0, offset=0)])
        elif d == 1:
            b.transition(src, a2, states[(0, 0)],
                         emissions=[Emission("TPLSPLIT_CG", 1.0, offset=0)])
        else:
            b.transition(src, a2, states[(0, 0)],
                         emissions=[Emission("SHR_OP", 1.0, offset=0),
                                    Emission("SHIFT", 1.0, offset=0)])
        b.transition(src, other, states[(d, 0)])
    return b.build()


# --- Layer 1b: retokenization by splitting ----------------------------------------------


def retokenize(state: ParserState) -> ParserState:
    """Split each TPLSPLIT-flagged '>>' into two synthesized '>' slots."""
    new = ParserState()
    order = 0.0
    angle_n = 0
    for slot in state.stream("token"):
        kind = ("CC" if "TPLSPLIT_CC" in slot.labels
                else "CG" if "TPLSPLIT_CG" in slot.labels else None)
        if kind is None:
            slot.order = order
            order += 1.0
            new.add_slot("token", slot)
            continue
        span = slot.source_span
        for half, labels in enumerate(
            (("TPL_CLOSE",),
             ("TPL_CLOSE",) if kind == "CC" else ("GT_OP", "CMP_OP"))
        ):
            piece = Slot(
                id=f"angle:{angle_n}", kind="token", stream="token",
                order=order, text=">",
                source_span=SourceSpan(span.start + half, span.start + half + 1),
                parents=(ProvenanceEdge("derived_from", slot.id),),
            )
            angle_n += 1
            piece.labels.add("TEXT:>", 1.0)
            for lab in labels:
                piece.labels.add(lab, 1.0)
            new.add_slot("token", piece)
            order += 1.0
    return new


# --- Layer 2: declaration sites + scope checkers -----------------------------------------


def _type_expr(k: int) -> FSM:
    base = literal(HasLabel("INT_TYPE"))
    if k == 0:
        return base
    def inner() -> FSM:
        return _type_expr(k - 1)
    tmpl = concat(
        literal(HasLabel("TEMPLATE")),
        literal(HasLabel("TPL_OPEN")),
        inner(),
        star(concat(literal(HasLabel("COMMA")), inner())),
        literal(HasLabel("TPL_CLOSE")),
    )
    return alt(base, tmpl)


def build_decl_site_marker() -> FSM:
    m = concat(
        _type_expr(MAX_TPL),
        literal(HasLabel("IDENT"),
                emissions=[Emission("DECL_SITE", 1.0, offset=0)]),
    )
    m.name = "decl_site_marker"
    return m


def build_scope_checker(name: str, max_scopes: int = MAX_SCOPES) -> FSM:
    """imp's bit-stack checker, keyed on DECL_SITE (the type announces
    the binding BEFORE the name, but the checker only needs the label)."""
    b = FSMBuilder(f"scope_check@{name}")
    configs = [
        bits for n in range(1, max_scopes + 1) for bits in product((0, 1), repeat=n)
    ]
    states = {bits: b.state("".join(map(str, bits))) for bits in configs}
    b.start(states[(0,)])
    b.accept(*states.values())

    is_x = And((HasLabel("IDENT"), HasLabel(f"TEXT:{name}")))
    is_decl = And((is_x, HasLabel("DECL_SITE")))
    is_use = And((is_x, Not(HasLabel("DECL_SITE"))))
    lb, rb = HasLabel("LBRACE"), HasLabel("RBRACE")
    other = Not(Or((is_x, lb, rb)))

    for bits, src in states.items():
        if bits[-1]:
            b.transition(src, is_decl, src,
                         emissions=[Emission("ERROR:REDECLARE", 1.0, offset=0)])
        else:
            b.transition(src, is_decl, states[bits[:-1] + (1,)])
        ems = [] if any(bits) else [Emission("ERROR:UNDECLARED", 1.0, offset=0)]
        b.transition(src, is_use, src, emissions=ems)
        pushed = bits + (0,) if len(bits) < max_scopes else bits
        b.transition(src, lb, states[pushed])
        popped = bits[:-1] if len(bits) > 1 else bits
        b.transition(src, rb, states[popped])
        b.transition(src, other, src)
    return b.build()


# --- Layer 3: expression emitters (rebuilt: C++ precedence) -------------------------------


def _shiftop(d: int):
    return And((HasLabel("SHIFT"), _d(d)))


def _shiftchain(d: int) -> FSM:
    return concat(_addchain(d), star(concat(literal(_shiftop(d)), _addchain(d))))


def _expression_emitters_cpp(max_depth: int) -> list[FSM]:
    machines: list[FSM] = []
    for d in range(max_depth + 1):
        neg = _with_exit_emission(
            concat(literal(_unary_minus(d)), _operand(d)),
            Emission("EXEC.1:NEG", 1.0, anchor=CaptureAnchor("end")),
        )
        neg.name = f"neg@{d}"
        machines.append(neg)
        for label, instr in (("MUL_OP", "MUL"), ("DIV_OP", "DIV")):
            m = _with_exit_emission(
                concat(_operand(d), literal(And((HasLabel(label), _d(d)))), _operand(d)),
                Emission(f"EXEC.2:{instr}", 1.0, anchor=CaptureAnchor("end")),
            )
            m.name = f"{instr.lower()}@{d}"
            machines.append(m)
        for label, instr in (("ADD_OP", "ADD"), ("SUB_OP", "SUB")):
            op_cond = (
                And((HasLabel(label), HasLabel("MINUS:BINARY"), _d(d)))
                if instr == "SUB" else And((HasLabel(label), _d(d)))
            )
            m = concat(
                literal(op_cond),
                concat(_operand(d), star(concat(literal(_mulop(d)), _operand(d)))),
                literal(Not(_mulop(d)),
                        emissions=[Emission(f"EXEC.3:{instr}", 1.0,
                                            anchor=CaptureAnchor("end"))]),
            )
            m.name = f"{instr.lower()}@{d}"
            machines.append(m)
        for label, instr in (("SHL_OP", "SHL"), ("SHR_OP", "SHR")):
            m = concat(
                literal(And((HasLabel(label), _d(d)))),
                _addchain(d),
                literal(Not(Or((_mulop(d), _addop(d)))),
                        emissions=[Emission(f"EXEC.4:{instr}", 1.0,
                                            anchor=CaptureAnchor("end"))]),
            )
            m.name = f"{instr.lower()}@{d}"
            machines.append(m)
        for label, instr in (("GT_OP", "GT"), ("LT_OP", "LT"), ("EQ_OP", "EQ")):
            # right operand is a SHIFT chain: a < b >> c == a < (b >> c)
            m = concat(
                literal(And((HasLabel(label), _d(d)))),
                _shiftchain(d),
                literal(Not(Or((_mulop(d), _addop(d), _shiftop(d)))),
                        emissions=[Emission(f"EXEC.5:{instr}", 1.0,
                                            anchor=CaptureAnchor("end"))]),
            )
            m.name = f"{instr.lower()}@{d}"
            machines.append(m)
    return machines


# --- Layer 4: statement emitters -----------------------------------------------------------


def _statement_emitters_cpp() -> list[FSM]:
    machines: list[FSM] = []
    type_ish = Or((HasLabel("TYPE"), HasLabel("TPL_CLOSE")))

    push = literal(HasLabel("NUM"),
                   emissions=[Emission("EXEC.0:PUSH(!{VAL})", 1.0, offset=0)])
    push.name = "push_num"
    machines.append(push)

    load = concat(
        literal(Not(type_ish)),
        literal(HasLabel("IDENT")),
        literal(Not(HasLabel("ASSIGN")),
                emissions=[Emission("EXEC.0:LOAD(!{VAL})", 1.0, offset=-1)]),
    )
    load.name = "load"
    machines.append(load)

    var_cap = Capture("var", kind="slot_id")
    decl_init = concat(
        _type_expr(MAX_TPL),
        literal(HasLabel("IDENT"), captures=[var_cap]),
        literal(HasLabel("ASSIGN")),
        star(literal(Not(HasLabel("SEMI")))),
        literal(HasLabel("SEMI"),
                emissions=[Emission("EXEC.6:DECL(!{VAL@{var}})", 1.0, offset=0)]),
    )
    decl_init.name = "decl_init"
    machines.append(decl_init)

    decl_default = concat(
        _type_expr(MAX_TPL),
        literal(HasLabel("IDENT"), captures=[var_cap]),
        literal(HasLabel("SEMI"),
                emissions=[Emission("EXEC.6:DECLD(!{VAL@{var}})", 1.0, offset=0)]),
    )
    decl_default.name = "decl_default"
    machines.append(decl_default)

    assign = concat(
        literal(Not(type_ish)),
        literal(HasLabel("IDENT"), captures=[var_cap]),
        literal(HasLabel("ASSIGN")),
        star(literal(Not(HasLabel("SEMI")))),
        literal(HasLabel("SEMI"),
                emissions=[Emission("EXEC.6:STORE(!{VAL@{var}})", 1.0, offset=0)]),
    )
    assign.name = "assign"
    machines.append(assign)

    print_stmt = concat(
        literal(HasLabel("PRINT_KW")),
        star(literal(Not(HasLabel("SEMI")))),
        literal(HasLabel("SEMI"),
                emissions=[Emission("EXEC.6:PRINT", 1.0, offset=0)]),
    )
    print_stmt.name = "print_stmt"
    machines.append(print_stmt)

    block_open = literal(
        HasLabel("LBRACE"),
        emissions=[Emission("EXEC.0:BRF", 1.0, offset=0),
                   Emission("EXEC.1:ENTER", 1.0, offset=0)],
    )
    block_open.name = "block_open"
    machines.append(block_open)

    block_close = literal(HasLabel("RBRACE"),
                          emissions=[Emission("EXEC.0:EXIT", 1.0, offset=0)])
    block_close.name = "block_close"
    machines.append(block_close)
    return machines


@lru_cache(maxsize=2)
def _static_machines():
    return (
        build_angle_story(),
        build_bracket_tracker(MAX_DEPTH),
        build_minus_story(),
        build_decl_site_marker(),
        tuple(_expression_emitters_cpp(MAX_DEPTH) + _statement_emitters_cpp()),
    )


# --- Compile -------------------------------------------------------------------------------


_EXEC = re.compile(r"EXEC\.(\d+):([A-Z_]+)(?:\((.*)\))?$")
_REF = re.compile(r"!\{(\w+)(?:@([\w:]+))?\}$")


def _resolve_operand(state: ParserState, slot: Slot, ref: str) -> Any:
    m = _REF.match(ref)
    if not m or m.group(1) != "VAL":
        raise ValueError(f"unsupported operand reference: {ref!r}")
    target = state.get_slot(m.group(2)) if m.group(2) else slot
    if target is None:
        raise ValueError(f"dangling slot reference in {ref!r}")
    vals = sorted(
        ((w, lab) for lab, w in target.labels.items() if lab.startswith("VAL:")),
        reverse=True,
    )
    if not vals:
        raise ValueError(f"no VAL label on {target.id}")
    if len(vals) > 1 and vals[1][0] >= 0.5 * vals[0][0]:
        raise ValueError(f"ambiguous VAL on {target.id}: {vals[:2]}")
    raw = vals[0][1].split(":", 1)[1]
    return int(raw) if "NUM" in target.labels else raw


def compile_program(text: str) -> CompileResult:
    state = initialize(text)
    scanner = FSMScanner()
    angle_story, tracker, minus_story, decl_marker, emitters = _static_machines()

    apply_deltas(state, scanner.transduce(angle_story, state, anchored=True))
    state = retokenize(state)
    real = [s for s in state.tokens if s.kind == "token"]
    opens_t = sum(1 for s in state.tokens for lab in s.labels.weights
                  if lab == "TPL_OPEN")
    closes_t = sum(1 for s in state.tokens for lab in s.labels.weights
                   if lab == "TPL_CLOSE")
    if opens_t > closes_t and real:
        apply_deltas(state, [LabelDelta(slot_id=real[-1].id,
                                        label="ERROR:UNTERMINATED_TEMPLATE",
                                        weight=1.0, source="angle_story")])

    apply_deltas(state, scanner.transduce(tracker, state, anchored=True))
    opens = sum(1 for s in state.tokens for lab in s.labels.weights
                if lab.startswith("GROUP_START:"))
    closes = sum(1 for s in state.tokens for lab in s.labels.weights
                 if lab.startswith("GROUP_END:"))
    if opens > closes and real:
        apply_deltas(state, [LabelDelta(slot_id=real[-1].id,
                                        label="ERROR:UNBALANCED_OPEN",
                                        weight=1.0, source="bracket_tracker")])

    apply_deltas(state, scanner.transduce(decl_marker, state))
    idents = sorted({
        s.text for s in state.tokens
        if s.kind == "token" and "IDENT" in s.labels and s.text
    })
    for name in idents:
        apply_deltas(
            state, scanner.transduce(build_scope_checker(name), state, anchored=True)
        )
    apply_deltas(state, scanner.transduce(minus_story, state, anchored=True))

    emit_deltas: list[LabelDelta] = []
    for m in emitters:
        emit_deltas.extend(scanner.transduce(m, state))
    apply_deltas(state, emit_deltas)

    program: list[Instruction] = []
    for slot in state.tokens:
        if slot.kind != "token":
            continue
        execs = []
        for lab in slot.labels.weights:
            match = _EXEC.match(lab)
            if match:
                execs.append((int(match.group(1)), match.group(2), match.group(3)))
        for rank, op, arg in sorted(execs):
            operand = _resolve_operand(state, slot, arg) if arg else None
            program.append(Instruction(op=op, operand=operand,
                                       slot_id=slot.id, rank=rank))

    errors = sorted({lab for s in state.tokens for lab in s.labels.weights
                     if lab.startswith("ERROR:")})
    return CompileResult(state=state, program=program, errors=errors)


# --- VM (imp's, plus SHL/SHR/DECLD) ---------------------------------------------------------


@dataclass
class RunResult:
    outputs: list[Any]
    env: dict[str, Any] = field(default_factory=dict)
    valid: bool = True


_BINOPS = {
    "ADD": lambda a, b: a + b,
    "SUB": lambda a, b: a - b,
    "MUL": lambda a, b: a * b,
    "DIV": lambda a, b: a / b,
    "SHL": lambda a, b: int(a) << int(b),
    "SHR": lambda a, b: int(a) >> int(b),
    "GT": lambda a, b: 1 if a > b else 0,
    "LT": lambda a, b: 1 if a < b else 0,
    "EQ": lambda a, b: 1 if a == b else 0,
}


def run_program(program: list[Instruction]) -> RunResult:
    stack: list[Any] = []
    scopes: list[dict[str, Any]] = [{}]
    outputs: list[Any] = []

    def fail() -> RunResult:
        return RunResult(outputs=outputs, env=scopes[0], valid=False)

    pc = 0
    while pc < len(program):
        ins = program[pc]
        if ins.op == "PUSH":
            stack.append(ins.operand)
        elif ins.op == "LOAD":
            for scope in reversed(scopes):
                if ins.operand in scope:
                    stack.append(scope[ins.operand])
                    break
            else:
                return fail()
        elif ins.op == "DECL":
            if not stack:
                return fail()
            scopes[-1][ins.operand] = stack.pop()
        elif ins.op == "DECLD":
            scopes[-1][ins.operand] = 0  # default initialization
        elif ins.op == "STORE":
            if not stack:
                return fail()
            v = stack.pop()
            for scope in reversed(scopes):
                if ins.operand in scope:
                    scope[ins.operand] = v
                    break
            else:
                return fail()
        elif ins.op == "NEG":
            if not stack:
                return fail()
            stack.append(-stack.pop())
        elif ins.op in _BINOPS:
            if len(stack) < 2:
                return fail()
            b_val, a_val = stack.pop(), stack.pop()
            stack.append(_BINOPS[ins.op](a_val, b_val))
        elif ins.op == "PRINT":
            if not stack:
                return fail()
            outputs.append(stack.pop())
        elif ins.op == "BRF":
            if not stack:
                return fail()
            if not stack.pop():
                depth = 0
                j = pc + 1
                while j < len(program):
                    if program[j].op == "ENTER":
                        depth += 1
                    elif program[j].op == "EXIT":
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                pc = j
        elif ins.op == "ENTER":
            scopes.append({})
        elif ins.op == "EXIT":
            if len(scopes) <= 1:
                return fail()
            scopes.pop()
        else:
            raise ValueError(f"unknown instruction {ins.op}")
        pc += 1

    valid = not stack and len(scopes) == 1
    return RunResult(outputs=outputs, env=scopes[0], valid=valid)


def execute(text: str) -> RunResult | None:
    result = compile_program(text)
    if result.errors:
        return None
    return run_program(result.program)

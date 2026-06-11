"""Runner for the tiny imperative language (languages/imp/).

New machinery relative to the earlier languages:

* **input-indexed schema instantiation**: one anchored scope-checker
  machine per identifier occurring in the input (declared-before-use is
  not regular over unbounded names, but is regular per name: a stack of
  one declared-bit per block level);
* **cross-slot operands**: ``DECL``/``STORE`` execute at the statement's
  ``;`` but name the variable token via a slot-id capture interpolated
  into the emission label (``EXEC.4:DECL(!{VAL@token:1})``) — first use
  of template interpolation and the ``!{FAMILY@id}`` reference form;
* **structured control flow**: ``BRF``/``ENTER``/``EXIT`` matched
  markers instead of address jumps (emissions cannot point forward).

Expression machinery (operand/chain/guard construction, exit-emission
envelope) is arithmetic's, extended with identifiers as operands and a
comparison precedence level below additive.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from fsm_parser.combinators import _embed, alt, concat, literal, star
from fsm_parser.fsm import (
    FSM,
    Always,
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
from fsm_parser.labels import LabelDelta
from fsm_parser.normalization import apply_deltas
from fsm_parser.slots import Slot, SourceSpan
from fsm_parser.tokens import ParserState

MAX_DEPTH = 5          # combined paren + block nesting
MAX_SCOPES = MAX_DEPTH + 1   # block levels + global

_TOKEN = re.compile(r"==|[(){};=+\-*/<>]|\d+|[A-Za-z_]\w*|\S")

_KEYWORDS = {"let": "LET", "if": "IF", "print": "PRINT_KW"}
_PUNCT = {
    "=": "ASSIGN", "==": "EQ_OP", ">": "GT_OP", "<": "LT_OP",
    "+": "ADD_OP", "-": "SUB_OP", "*": "MUL_OP", "/": "DIV_OP",
    "(": "LPAREN", ")": "RPAREN", "{": "LBRACE", "}": "RBRACE", ";": "SEMI",
}
_SUPER = {
    "EQ_OP": "CMP_OP", "GT_OP": "CMP_OP", "LT_OP": "CMP_OP",
    "ADD_OP": "ADDITIVE", "SUB_OP": "ADDITIVE",
    "MUL_OP": "MULTIPLICATIVE", "DIV_OP": "MULTIPLICATIVE",
}


# --- Layer 0 -------------------------------------------------------------------


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
        if raw in _KEYWORDS:
            slot.labels.add(_KEYWORDS[raw], 1.0)
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


# --- Layer 1: bracket tracker ------------------------------------------------------


def build_bracket_tracker(max_depth: int = MAX_DEPTH) -> FSM:
    """Anchored tracker over bracket-kind stacks {P, B} (layers.yaml)."""
    from itertools import product

    b = FSMBuilder("bracket_tracker")
    stacks = [s for n in range(max_depth + 1) for s in product("PB", repeat=n)]
    states = {s: b.state("".join(s) or "top") for s in stacks}
    overflow = b.state("overflow")
    b.start(states[()])
    b.accept(states[()])

    openers = {"P": HasLabel("LPAREN"), "B": HasLabel("LBRACE")}
    closers = {"P": HasLabel("RPAREN"), "B": HasLabel("RBRACE")}
    non_bracket = Not(HasLabel("BRACKET"))

    for sigma in stacks:
        d = len(sigma)
        src = states[sigma]
        for kind, cond in openers.items():
            if d < max_depth:
                b.transition(
                    src, cond, states[sigma + (kind,)],
                    emissions=[Emission(f"DEPTH:{d + 1}", 1.0, offset=0),
                               Emission(f"GROUP_START:{d + 1}", 1.0, offset=0)],
                )
            else:
                b.transition(
                    src, cond, overflow,
                    emissions=[Emission("ERROR:DEPTH_EXCEEDED", 1.0, offset=0)],
                )
        if sigma:
            top, rest = sigma[-1], sigma[:-1]
            base = [Emission(f"DEPTH:{d}", 1.0, offset=0),
                    Emission(f"GROUP_END:{d}", 1.0, offset=0)]
            for kind, cond in closers.items():
                ems = list(base)
                if kind != top:
                    ems.append(Emission("ERROR:MISMATCHED_CLOSE", 1.0, offset=0))
                b.transition(src, cond, states[rest], emissions=ems)
        else:
            for cond in closers.values():
                b.transition(
                    src, cond, src,
                    emissions=[Emission("ERROR:UNBALANCED_CLOSE", 1.0, offset=0)],
                )
        b.transition(
            src, non_bracket, src,
            emissions=[Emission(f"DEPTH:{d}", 1.0, offset=0)],
        )
    b.transition(overflow, Always(), overflow,
                 emissions=[Emission("DEPTH:OVERFLOW", 1.0, offset=0)])
    return b.build()


# --- Layer 2: per-identifier scope checkers ------------------------------------------


def build_scope_checker(name: str, max_scopes: int = MAX_SCOPES) -> FSM:
    """Anchored declared-before-use checker for one identifier.

    States are (bit-stack, expect-decl): one bit per open block level
    plus global. ~252 states for max_scopes=6. Input-indexed schema
    instantiation: one machine per identifier in the input.
    """
    from itertools import product

    b = FSMBuilder(f"scope_check@{name}")
    configs = [
        (bits, e)
        for n in range(1, max_scopes + 1)
        for bits in product((0, 1), repeat=n)
        for e in (False, True)
    ]
    states = {
        cfg: b.state(f"{''.join(map(str, cfg[0]))}{'E' if cfg[1] else ''}")
        for cfg in configs
    }
    b.start(states[((0,), False)])
    b.accept(*states.values())

    is_let = HasLabel("LET")
    is_x = And((HasLabel("IDENT"), HasLabel(f"TEXT:{name}")))
    lb, rb = HasLabel("LBRACE"), HasLabel("RBRACE")
    other = Not(Or((is_let, is_x, lb, rb)))

    for (bits, expect), src in states.items():
        b.transition(src, is_let, states[(bits, True)])
        # occurrence of the identifier
        if expect:
            if bits[-1]:
                b.transition(
                    src, is_x, states[(bits, False)],
                    emissions=[Emission("ERROR:REDECLARE", 1.0, offset=0)],
                )
            else:
                declared = bits[:-1] + (1,)
                b.transition(src, is_x, states[(declared, False)])
        else:
            ems = [] if any(bits) else [Emission("ERROR:UNDECLARED", 1.0, offset=0)]
            b.transition(src, is_x, states[(bits, False)], emissions=ems)
        pushed = bits + (0,) if len(bits) < max_scopes else bits
        b.transition(src, lb, states[(pushed, False)])
        popped = bits[:-1] if len(bits) > 1 else bits
        b.transition(src, rb, states[(popped, False)])
        b.transition(src, other, states[(bits, False)])
    return b.build()


# --- Layer 3: expression emitters (arithmetic's construction + IDENT + cmp) ----------


def _d(d: int) -> HasLabel:
    return HasLabel(f"DEPTH:{d}")


def _mulop(d):
    return And((HasLabel("MULTIPLICATIVE"), _d(d)))


def _addop(d):
    return And((HasLabel("ADDITIVE"), _d(d)))


def _operand(d: int) -> FSM:
    end_cap = Capture("end", kind="index")
    scalar = literal(
        And((Or((HasLabel("NUM"), HasLabel("IDENT"))), _d(d))), captures=[end_cap]
    )
    if d >= MAX_DEPTH:
        return scalar
    group = concat(
        literal(And((HasLabel("LPAREN"), HasLabel(f"GROUP_START:{d + 1}")))),
        star(literal(Not(HasLabel(f"GROUP_END:{d + 1}")))),
        literal(And((HasLabel("RPAREN"), HasLabel(f"GROUP_END:{d + 1}"))),
                captures=[end_cap]),
    )
    return alt(scalar, group)


def _mulchain(d: int) -> FSM:
    return concat(_operand(d), star(concat(literal(_mulop(d)), _operand(d))))


def _addchain(d: int) -> FSM:
    return concat(_mulchain(d), star(concat(literal(_addop(d)), _mulchain(d))))


def _with_exit_emission(machine: FSM, emission: Emission) -> FSM:
    b = FSMBuilder(machine.name)
    sub_start, sub_accepts = _embed(b, machine)
    exit_state = b.state("exit")
    b.start(sub_start).accept(exit_state)
    for a in sub_accepts:
        b.epsilon(a, exit_state)
    b.state_info(exit_state, on_enter=(emission,))
    return b.build()


def _expression_emitters(max_depth: int) -> list[FSM]:
    machines: list[FSM] = []
    for d in range(max_depth + 1):
        for label, instr in (("MUL_OP", "MUL"), ("DIV_OP", "DIV")):
            m = _with_exit_emission(
                concat(_operand(d), literal(And((HasLabel(label), _d(d)))), _operand(d)),
                Emission(f"EXEC.1:{instr}", 1.0, anchor=CaptureAnchor("end")),
            )
            m.name = f"{instr.lower()}@{d}"
            machines.append(m)
        for label, instr in (("ADD_OP", "ADD"), ("SUB_OP", "SUB")):
            m = concat(
                literal(And((HasLabel(label), _d(d)))),
                _mulchain(d),
                literal(Not(_mulop(d)),
                        emissions=[Emission(f"EXEC.2:{instr}", 1.0,
                                            anchor=CaptureAnchor("end"))]),
            )
            m.name = f"{instr.lower()}@{d}"
            machines.append(m)
        for label, instr in (("GT_OP", "GT"), ("LT_OP", "LT"), ("EQ_OP", "EQ")):
            m = concat(
                literal(And((HasLabel(label), _d(d)))),
                _addchain(d),
                literal(Not(Or((_mulop(d), _addop(d)))),
                        emissions=[Emission(f"EXEC.3:{instr}", 1.0,
                                            anchor=CaptureAnchor("end"))]),
            )
            m.name = f"{instr.lower()}@{d}"
            machines.append(m)
    return machines


# --- Layer 4: statement emitters ------------------------------------------------------


def _statement_emitters() -> list[FSM]:
    machines: list[FSM] = []

    push = literal(HasLabel("NUM"),
                   emissions=[Emission("EXEC.0:PUSH(!{VAL})", 1.0, offset=0)])
    push.name = "push_num"
    machines.append(push)

    load = concat(
        literal(Not(HasLabel("LET"))),
        literal(HasLabel("IDENT")),
        literal(Not(HasLabel("ASSIGN")),
                emissions=[Emission("EXEC.0:LOAD(!{VAL})", 1.0, offset=-1)]),
    )
    load.name = "load"
    machines.append(load)

    var_cap = Capture("var", kind="slot_id")
    let_decl = concat(
        literal(HasLabel("LET")),
        literal(HasLabel("IDENT"), captures=[var_cap]),
        literal(HasLabel("ASSIGN")),
        star(literal(Not(HasLabel("SEMI")))),
        literal(HasLabel("SEMI"),
                emissions=[Emission("EXEC.4:DECL(!{VAL@{var}})", 1.0, offset=0)]),
    )
    let_decl.name = "let_decl"
    machines.append(let_decl)

    assign = concat(
        literal(Not(HasLabel("LET"))),
        literal(HasLabel("IDENT"), captures=[var_cap]),
        literal(HasLabel("ASSIGN")),
        star(literal(Not(HasLabel("SEMI")))),
        literal(HasLabel("SEMI"),
                emissions=[Emission("EXEC.4:STORE(!{VAL@{var}})", 1.0, offset=0)]),
    )
    assign.name = "assign"
    machines.append(assign)

    print_stmt = concat(
        literal(HasLabel("PRINT_KW")),
        star(literal(Not(HasLabel("SEMI")))),
        literal(HasLabel("SEMI"),
                emissions=[Emission("EXEC.4:PRINT", 1.0, offset=0)]),
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


@lru_cache(maxsize=4)
def _static_machines(max_depth: int) -> tuple[FSM, tuple[FSM, ...]]:
    return (
        build_bracket_tracker(max_depth),
        tuple(_expression_emitters(max_depth) + _statement_emitters()),
    )


# --- Projection and VM ------------------------------------------------------------------


@dataclass
class Instruction:
    op: str
    operand: Any = None
    slot_id: str = ""
    rank: int = 0

    def __str__(self) -> str:
        return f"{self.op} {self.operand}" if self.operand is not None else self.op


@dataclass
class CompileResult:
    state: ParserState
    program: list[Instruction]
    errors: list[str]


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


def compile_program(text: str, *, max_depth: int = MAX_DEPTH) -> CompileResult:
    state = initialize(text)
    scanner = FSMScanner()
    tracker, emitters = _static_machines(max_depth)

    deltas = scanner.transduce(tracker, state, anchored=True)
    apply_deltas(state, deltas)
    opens = sum(1 for s in state.tokens for lab in s.labels.weights
                if lab.startswith("GROUP_START:"))
    closes = sum(1 for s in state.tokens for lab in s.labels.weights
                 if lab.startswith("GROUP_END:"))
    real = [s for s in state.tokens if s.kind == "token"]
    if opens > closes and real:
        apply_deltas(state, [LabelDelta(slot_id=real[-1].id,
                                        label="ERROR:UNBALANCED_OPEN",
                                        weight=1.0, source="bracket_tracker")])

    # input-indexed scope checkers
    idents = sorted({
        s.text for s in real if "IDENT" in s.labels and s.text
    })
    scope_deltas: list[LabelDelta] = []
    for name in idents:
        scope_deltas.extend(
            scanner.transduce(build_scope_checker(name), state, anchored=True)
        )
    apply_deltas(state, scope_deltas)

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
                pc = j  # lands on the matched EXIT; loop's pc+1 skips past
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
    """Compile + run; None if the field carries ERROR labels."""
    result = compile_program(text)
    if result.errors:
        return None
    return run_program(result.program)

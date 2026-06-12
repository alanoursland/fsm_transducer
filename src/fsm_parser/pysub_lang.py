"""Runner for the Python subset (languages/pysub/).

The headline is what is NOT here: the paren tracker, the minus story
machine, and the entire expression-emitter layer are imported from
``fsm_parser.imp_lang`` unchanged — the first cross-language machine
reuse, and the first running test of the interlingua claim
(notes/story_machines.md): same machines, different syntax adapter.

What is here:

* **layout synthesis** (layer 0): the classic indent-stack algorithm
  producing NEWLINE / INDENT / DEDENT slots with no source text — the
  first language to synthesize slots. One slot per DEDENT pop, so EXIT
  markers can never collide in a label bag (routing around imp's
  documented bag-not-multiset limitation by representation);
* **target marking**: Python announces a binding *after* the name
  (``x =``), so a two-token reflex marks assignment targets before the
  anchored per-identifier checkers run — the adapter normalizing word
  order so shared machinery doesn't have to;
* **two-state assignment checkers** (no block scope in Python);
* NEWLINE-terminated statement emitters; BRF on ``:``, ENTER on
  INDENT slots, EXIT on DEDENT slots; a single-environment VM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from fsm_parser.combinators import concat, literal, star
from fsm_parser.fsm import (
    FSM,
    And,
    Capture,
    Emission,
    FSMBuilder,
    FSMScanner,
    HasLabel,
    Not,
)
from fsm_parser.imp_lang import (
    MAX_DEPTH,
    _expression_emitters,
    build_bracket_tracker,
    build_minus_story,
)
from fsm_parser.labels import LabelDelta
from fsm_parser.normalization import apply_deltas
from fsm_parser.slots import Slot, SourceSpan
from fsm_parser.tokens import ParserState

MAX_INDENT = 4   # indent stack depth (block nesting levels)

_TOKEN = re.compile(r"==|[():=+\-*/<>]|\d+|[A-Za-z_]\w*|\S")
_KEYWORDS = {"if": "IF", "print": "PRINT_KW"}
_PUNCT = {
    "=": "ASSIGN", "==": "EQ_OP", ">": "GT_OP", "<": "LT_OP",
    "+": "ADD_OP", "-": "SUB_OP", "*": "MUL_OP", "/": "DIV_OP",
    "(": "LPAREN", ")": "RPAREN", ":": "COLON",
}
_SUPER = {
    "EQ_OP": "CMP_OP", "GT_OP": "CMP_OP", "LT_OP": "CMP_OP",
    "ADD_OP": "ADDITIVE", "SUB_OP": "ADDITIVE",
    "MUL_OP": "MULTIPLICATIVE", "DIV_OP": "MULTIPLICATIVE",
}


# --- Layer 0: tokenization + layout synthesis -----------------------------------


def initialize(text: str) -> ParserState:
    state = ParserState()
    order = 0.0

    def add(slot: Slot) -> Slot:
        nonlocal order
        slot.order = order
        order += 1.0
        state.add_slot("token", slot)
        return slot

    bof = Slot(id="meta:bof", kind="meta", stream="token", text="")
    bof.labels.add("BOF", 1.0)
    add(bof)

    indent_stack = [0]
    tok_i = 0
    lay_i = 0
    char_pos = 0

    def layout(label: str, extra: str | None = None) -> Slot:
        nonlocal lay_i
        slot = Slot(id=f"layout:{lay_i}", kind="layout", stream="token", text="")
        lay_i += 1
        slot.labels.add(label, 1.0)
        slot.labels.add("LAYOUT", 1.0)
        if extra:
            slot.labels.add(extra, 1.0)
        return add(slot)

    first_line = True
    for line in text.split("\n"):
        line_start = char_pos
        char_pos += len(line) + 1
        if not line.strip():
            continue
        col = len(line) - len(line.lstrip(" "))
        pending_error: str | None = None
        if first_line:
            if col > 0:
                pending_error = "ERROR:UNEXPECTED_INDENT"
            first_line = False
        elif col > indent_stack[-1]:
            if len(indent_stack) > MAX_INDENT:
                layout("INDENT", "ERROR:DEPTH_EXCEEDED")
            else:
                indent_stack.append(col)
                layout("INDENT")
        elif col < indent_stack[-1]:
            while indent_stack[-1] > col:
                indent_stack.pop()
                layout("DEDENT")
            if indent_stack[-1] != col:
                pending_error = "ERROR:DEDENT_MISMATCH"
                indent_stack.append(col)  # recover at this level

        cursor = col
        for raw in _TOKEN.findall(line):
            idx = line.find(raw, cursor)
            cursor = idx + len(raw)
            slot = Slot(
                id=f"token:{tok_i}", kind="token", stream="token", text=raw,
                source_span=SourceSpan(line_start + idx, line_start + idx + len(raw)),
            )
            tok_i += 1
            slot.labels.add(f"TEXT:{raw}", 1.0)
            if pending_error:
                slot.labels.add(pending_error, 1.0)
                pending_error = None
            if raw in _KEYWORDS:
                slot.labels.add(_KEYWORDS[raw], 1.0)
            elif raw in _PUNCT:
                cls = _PUNCT[raw]
                slot.labels.add(cls, 1.0)
                if cls in _SUPER:
                    slot.labels.add(_SUPER[cls], 1.0)
                if raw in "()":
                    slot.labels.add("BRACKET", 1.0)
            elif raw.isdigit():
                slot.labels.add("NUM", 1.0)
                slot.labels.add(f"VAL:{raw}", 1.0)
            elif re.fullmatch(r"[A-Za-z_]\w*", raw):
                slot.labels.add("IDENT", 1.0)
                slot.labels.add(f"VAL:{raw}", 1.0)
            else:
                slot.labels.add("ERROR:UNKNOWN_TOKEN", 1.0)
            add(slot)
        layout("NEWLINE")

    while len(indent_stack) > 1:
        indent_stack.pop()
        layout("DEDENT")

    eof = Slot(id="meta:eof", kind="meta", stream="token", text="")
    eof.labels.add("EOF", 1.0)
    add(eof)
    return state


# --- Layer 2: target marking + assignment checkers --------------------------------


def build_target_marker() -> FSM:
    m = concat(
        literal(HasLabel("IDENT")),
        literal(HasLabel("ASSIGN"),
                emissions=[Emission("TARGET", 1.0, offset=-1)]),
    )
    m.name = "target_marker"
    return m


def build_assign_checker(name: str) -> FSM:
    """Two states (Python has no block scope): unassigned / assigned."""
    b = FSMBuilder(f"assign_check@{name}")
    u = b.state("unassigned")
    a = b.state("assigned")
    b.start(u)
    b.accept(u, a)
    is_x = And((HasLabel("IDENT"), HasLabel(f"TEXT:{name}")))
    is_target = And((is_x, HasLabel("TARGET")))
    is_use = And((is_x, Not(HasLabel("TARGET"))))
    other = Not(is_x)
    b.transition(u, is_target, a)
    b.transition(u, is_use, u,
                 emissions=[Emission("ERROR:UNDECLARED", 1.0, offset=0)])
    b.transition(u, other, u)
    for cond in (is_target, is_use, other):
        b.transition(a, cond, a)
    return b.build()


# --- Layer 4: statement emitters ----------------------------------------------------


def _statement_emitters() -> list[FSM]:
    machines: list[FSM] = []

    push = literal(HasLabel("NUM"),
                   emissions=[Emission("EXEC.0:PUSH(!{VAL})", 1.0, offset=0)])
    push.name = "push_num"
    machines.append(push)

    load = concat(
        literal(HasLabel("IDENT")),
        literal(Not(HasLabel("ASSIGN")),
                emissions=[Emission("EXEC.0:LOAD(!{VAL})", 1.0, offset=-1)]),
    )
    load.name = "load"
    machines.append(load)

    var_cap = Capture("var", kind="slot_id")
    assign = concat(
        literal(HasLabel("IDENT"), captures=[var_cap]),
        literal(HasLabel("ASSIGN")),
        star(literal(Not(HasLabel("NEWLINE")))),
        literal(HasLabel("NEWLINE"),
                emissions=[Emission("EXEC.5:STORE(!{VAL@{var}})", 1.0, offset=0)]),
    )
    assign.name = "assign"
    machines.append(assign)

    print_stmt = concat(
        literal(HasLabel("PRINT_KW")),
        star(literal(Not(HasLabel("NEWLINE")))),
        literal(HasLabel("NEWLINE"),
                emissions=[Emission("EXEC.5:PRINT", 1.0, offset=0)]),
    )
    print_stmt.name = "print_stmt"
    machines.append(print_stmt)

    brf = literal(HasLabel("COLON"),
                  emissions=[Emission("EXEC.0:BRF", 1.0, offset=0)])
    brf.name = "if_branch"
    machines.append(brf)

    enter = literal(HasLabel("INDENT"),
                    emissions=[Emission("EXEC.1:ENTER", 1.0, offset=0)])
    enter.name = "block_enter"
    machines.append(enter)

    exit_m = literal(HasLabel("DEDENT"),
                     emissions=[Emission("EXEC.0:EXIT", 1.0, offset=0)])
    exit_m.name = "block_exit"
    machines.append(exit_m)
    return machines


@lru_cache(maxsize=2)
def _static_machines() -> tuple[FSM, FSM, FSM, tuple[FSM, ...]]:
    return (
        build_bracket_tracker(MAX_DEPTH),       # imported from imp
        build_minus_story(),                    # imported from imp
        build_target_marker(),
        tuple(_expression_emitters(MAX_DEPTH)   # imported from imp
              + _statement_emitters()),
    )


# --- Projection and VM ----------------------------------------------------------------


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


def compile_program(text: str) -> CompileResult:
    state = initialize(text)
    scanner = FSMScanner()
    tracker, minus_story, target_marker, emitters = _static_machines()

    apply_deltas(state, scanner.transduce(tracker, state, anchored=True))
    apply_deltas(state, scanner.transduce(target_marker, state))
    idents = sorted({
        s.text for s in state.tokens
        if s.kind == "token" and "IDENT" in s.labels and s.text
    })
    for name in idents:
        apply_deltas(
            state, scanner.transduce(build_assign_checker(name), state, anchored=True)
        )
    apply_deltas(state, scanner.transduce(minus_story, state, anchored=True))

    emit_deltas: list[LabelDelta] = []
    for m in emitters:
        emit_deltas.extend(scanner.transduce(m, state))
    apply_deltas(state, emit_deltas)

    program: list[Instruction] = []
    for slot in state.tokens:
        if slot.kind == "meta":
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
    env: dict[str, Any] = {}
    outputs: list[Any] = []

    def fail() -> RunResult:
        return RunResult(outputs=outputs, env=env, valid=False)

    pc = 0
    while pc < len(program):
        ins = program[pc]
        if ins.op == "PUSH":
            stack.append(ins.operand)
        elif ins.op == "LOAD":
            if ins.operand not in env:
                return fail()
            stack.append(env[ins.operand])
        elif ins.op == "STORE":
            if not stack:
                return fail()
            env[ins.operand] = stack.pop()
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
        elif ins.op in ("ENTER", "EXIT"):
            pass  # pure control markers: Python blocks do not scope
        else:
            raise ValueError(f"unknown instruction {ins.op}")
        pc += 1

    return RunResult(outputs=outputs, env=env, valid=not stack)


def execute(text: str) -> RunResult | None:
    result = compile_program(text)
    if result.errors:
        return None
    return run_program(result.program)

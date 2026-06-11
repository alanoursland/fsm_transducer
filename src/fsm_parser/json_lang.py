"""Runner for the JSON language definition (languages/json/).

Pipeline mirrors fsm_parser.arithmetic:

1. tokenize + lexicon (STRING/NUM/literals/brackets, VAL labels)
2. anchored shape tracker — states are container-type stacks over
   {O, A} up to MAX_DEPTH (15 states + overflow for K=3); emits
   DEPTH:d, GROUP_START/END:d, CTX:<kind>:d on interior tokens,
   ENCL:<kind>:d on closing brackets, and located ERROR:* labels
3. emitters: NEW_OBJ/NEW_ARR/PUSH (global) and per-depth
   APPEND/SETK completion machines — all single- or two-token patterns,
   no guards needed: the ENCL label on a closing bracket already says
   how the finished container completes in its parent
4. projection: EXEC labels in (token, rank) order; !{VAL} resolves with
   class-directed typing (STRING -> str, NUM -> int/float,
   TRUE/FALSE/NULL -> True/False/None)
5. a five-op builder VM (PUSH, NEW_OBJ, NEW_ARR, APPEND, SETK)

The instruction set has no END ops: a container completes the moment
its last element completes, and keys live on the VM stack under their
values (PUSHed like any scalar, consumed by SETK).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from typing import Any

from fsm_parser.combinators import concat, literal
from fsm_parser.fsm import (
    FSM,
    Always,
    And,
    Emission,
    FSMBuilder,
    FSMScanner,
    HasLabel,
    Not,
)
from fsm_parser.labels import LabelDelta
from fsm_parser.normalization import apply_deltas
from fsm_parser.slots import Slot, SourceSpan
from fsm_parser.tokens import ParserState

MAX_DEPTH = 3

_TOKEN = re.compile(r'"[^"\\]*"|-?\d+(?:\.\d+)?|true|false|null|[{}\[\]:,]|\S')

_PUNCT = {
    "{": "LBRACE",
    "}": "RBRACE",
    "[": "LBRACKET",
    "]": "RBRACKET",
    ":": "COLON",
    ",": "COMMA",
}


# --- Layer 0: tokenization + lexicon ------------------------------------------


def initialize(text: str) -> ParserState:
    state = ParserState()
    cursor = 0
    for i, raw in enumerate(_TOKEN.findall(text)):
        idx = text.find(raw, cursor)
        cursor = idx + len(raw)
        slot = Slot(
            id=f"token:{i}",
            kind="token",
            stream="token",
            order=float(i),
            text=raw,
            source_span=SourceSpan(idx, idx + len(raw)),
        )
        slot.labels.add(f"TEXT:{raw}", 1.0)
        if raw.startswith('"'):
            slot.labels.add("STRING", 1.0)
            slot.labels.add("SCALAR", 1.0)
            slot.labels.add(f"VAL:{raw[1:-1]}", 1.0)
        elif raw in ("true", "false", "null"):
            slot.labels.add(raw.upper(), 1.0)
            slot.labels.add("SCALAR", 1.0)
            slot.labels.add(f"VAL:{raw}", 1.0)
        elif raw in _PUNCT:
            slot.labels.add(_PUNCT[raw], 1.0)
            if raw in "{}[]":
                slot.labels.add("BRACKET", 1.0)
        elif re.fullmatch(r"-?\d+(?:\.\d+)?", raw):
            slot.labels.add("NUM", 1.0)
            slot.labels.add("SCALAR", 1.0)
            slot.labels.add(f"VAL:{raw}", 1.0)
        else:
            slot.labels.add("ERROR:UNKNOWN_TOKEN", 1.0)
        state.add_slot("token", slot)
    return state


# --- Layer 1: shape tracker -----------------------------------------------------


def _kind_name(c: str) -> str:
    return "OBJ" if c == "O" else "ARR"


def build_shape_tracker(max_depth: int = MAX_DEPTH) -> FSM:
    """Anchored machine over container-type stacks (layers.yaml)."""
    b = FSMBuilder("shape_tracker")
    stacks = [
        sigma
        for n in range(max_depth + 1)
        for sigma in product("OA", repeat=n)
    ]
    states = {sigma: b.state("".join(sigma) or "top") for sigma in stacks}
    overflow = b.state("overflow")
    b.start(states[()])
    b.accept(states[()])

    openers = {"O": HasLabel("LBRACE"), "A": HasLabel("LBRACKET")}
    closers = {"O": HasLabel("RBRACE"), "A": HasLabel("RBRACKET")}
    non_bracket = Not(HasLabel("BRACKET"))

    for sigma in stacks:
        d = len(sigma)
        src = states[sigma]
        # opening brackets
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
        # closing brackets
        if sigma:
            top, rest = sigma[-1], sigma[:-1]
            close_emit = [
                Emission(f"DEPTH:{d}", 1.0, offset=0),
                Emission(f"GROUP_END:{d}", 1.0, offset=0),
            ]
            if rest:
                close_emit.append(
                    Emission(f"ENCL:{_kind_name(rest[-1])}:{d - 1}", 1.0, offset=0)
                )
            for kind, cond in closers.items():
                ems = list(close_emit)
                if kind != top:  # error recovery: pop anyway, flag it
                    ems.append(Emission("ERROR:MISMATCHED_CLOSE", 1.0, offset=0))
                b.transition(src, cond, states[rest], emissions=ems)
        else:
            for cond in closers.values():
                b.transition(
                    src, cond, src,
                    emissions=[Emission("ERROR:UNBALANCED_CLOSE", 1.0, offset=0)],
                )
        # interior tokens
        interior = [Emission(f"DEPTH:{d}", 1.0, offset=0)]
        if sigma:
            interior.append(
                Emission(f"CTX:{_kind_name(sigma[-1])}:{d}", 1.0, offset=0)
            )
        b.transition(src, non_bracket, src, emissions=interior)

    b.transition(
        overflow, Always(), overflow,
        emissions=[Emission("DEPTH:OVERFLOW", 1.0, offset=0)],
    )
    return b.build()


# --- Layer 2: emitters ------------------------------------------------------------


def _emitters(max_depth: int) -> list[FSM]:
    machines: list[FSM] = []

    def single(name: str, cond, label: str) -> None:
        m = literal(cond, emissions=[Emission(label, 1.0, offset=0)])
        m.name = name
        machines.append(m)

    single("new_obj", HasLabel("LBRACE"), "EXEC.0:NEW_OBJ")
    single("new_arr", HasLabel("LBRACKET"), "EXEC.0:NEW_ARR")
    single("push", HasLabel("SCALAR"), "EXEC.0:PUSH(!{VAL})")
    for d in range(1, max_depth + 1):
        single(
            f"append_scalar@{d}",
            And((HasLabel("SCALAR"), HasLabel(f"CTX:ARR:{d}"))),
            "EXEC.1:APPEND",
        )
        setk = concat(
            literal(And((HasLabel("COLON"), HasLabel(f"CTX:OBJ:{d}")))),
            literal(
                And((HasLabel("SCALAR"), HasLabel(f"CTX:OBJ:{d}"))),
                emissions=[Emission("EXEC.1:SETK", 1.0, offset=0)],
            ),
        )
        setk.name = f"setk_scalar@{d}"
        machines.append(setk)
        if d < max_depth:
            single(
                f"append_container@{d}",
                And((HasLabel(f"GROUP_END:{d + 1}"), HasLabel(f"ENCL:ARR:{d}"))),
                "EXEC.1:APPEND",
            )
            single(
                f"setk_container@{d}",
                And((HasLabel(f"GROUP_END:{d + 1}"), HasLabel(f"ENCL:OBJ:{d}"))),
                "EXEC.1:SETK",
            )
    return machines


@lru_cache(maxsize=4)
def _machines_for(max_depth: int) -> tuple[FSM, tuple[FSM, ...]]:
    return build_shape_tracker(max_depth), tuple(_emitters(max_depth))


# --- Projection and VM --------------------------------------------------------------


@dataclass
class Instruction:
    op: str                  # PUSH | NEW_OBJ | NEW_ARR | APPEND | SETK
    operand: Any = None      # typed scalar for PUSH
    slot_id: str = ""
    rank: int = 0

    def __str__(self) -> str:
        return f"PUSH {self.operand!r}" if self.op == "PUSH" else self.op


@dataclass
class CompileResult:
    state: ParserState
    program: list[Instruction]
    errors: list[str]


_EXEC = re.compile(r"EXEC\.(\d+):([A-Z_]+)(?:\((.*)\))?$")


def _resolve_operand(slot: Slot, ref: str) -> Any:
    if ref != "!{VAL}":
        raise ValueError(f"unsupported operand reference: {ref!r}")
    vals = sorted(
        ((w, lab) for lab, w in slot.labels.items() if lab.startswith("VAL:")),
        reverse=True,
    )
    if not vals:
        raise ValueError(f"no VAL label on {slot.id}")
    if len(vals) > 1 and vals[1][0] >= 0.5 * vals[0][0]:
        raise ValueError(f"ambiguous VAL on {slot.id}: {vals[:2]}")
    raw = vals[0][1].split(":", 1)[1]
    # class-directed typing (lexicon.yaml)
    if "STRING" in slot.labels:
        return raw
    if "NUM" in slot.labels:
        return float(raw) if "." in raw else int(raw)
    return {"true": True, "false": False, "null": None}[raw]


def compile_document(text: str, *, max_depth: int = MAX_DEPTH) -> CompileResult:
    state = initialize(text)
    scanner = FSMScanner()
    shape_tracker, emitters = _machines_for(max_depth)

    deltas = scanner.transduce(shape_tracker, state, anchored=True)
    apply_deltas(state, deltas)
    opens = sum(
        1 for s in state.tokens for lab in s.labels.weights if lab.startswith("GROUP_START:")
    )
    closes = sum(
        1 for s in state.tokens for lab in s.labels.weights if lab.startswith("GROUP_END:")
    )
    if opens > closes and state.tokens:
        apply_deltas(
            state,
            [LabelDelta(slot_id=state.tokens[-1].id, label="ERROR:UNBALANCED_OPEN",
                        weight=1.0, source="shape_tracker")],
        )

    emit_deltas: list[LabelDelta] = []
    for m in emitters:
        emit_deltas.extend(scanner.transduce(m, state))
    apply_deltas(state, emit_deltas)

    program: list[Instruction] = []
    for slot in state.tokens:
        execs = []
        for lab in slot.labels.weights:
            match = _EXEC.match(lab)
            if match:
                execs.append((int(match.group(1)), match.group(2), match.group(3)))
        for rank, op, arg in sorted(execs):
            operand = _resolve_operand(slot, arg) if arg else None
            program.append(Instruction(op=op, operand=operand, slot_id=slot.id, rank=rank))

    errors = sorted(
        {lab for s in state.tokens for lab in s.labels.weights if lab.startswith("ERROR:")}
    )
    return CompileResult(state=state, program=program, errors=errors)


@dataclass
class RunResult:
    stack: list[Any]
    valid: bool

    @property
    def document(self) -> Any:
        return self.stack[0] if self.valid else None


def run_program(program: list[Instruction]) -> RunResult:
    stack: list[Any] = []
    for ins in program:
        if ins.op == "PUSH":
            stack.append(ins.operand)
        elif ins.op == "NEW_OBJ":
            stack.append({})
        elif ins.op == "NEW_ARR":
            stack.append([])
        elif ins.op == "APPEND":
            if len(stack) < 2 or not isinstance(stack[-2], list):
                return RunResult(stack=stack, valid=False)
            v = stack.pop()
            stack[-1].append(v)
        elif ins.op == "SETK":
            if len(stack) < 3 or not isinstance(stack[-3], dict):
                return RunResult(stack=stack, valid=False)
            v, k = stack.pop(), stack.pop()
            stack[-1][k] = v
        else:
            raise ValueError(f"unknown instruction {ins.op}")
    return RunResult(stack=stack, valid=len(stack) == 1)


def loads(text: str) -> Any:
    """Compile + run; None if the field has errors or the run is invalid.

    (Note None is also a legitimate document for input "null"; check
    compile_document().errors to distinguish, as json.loads users check
    exceptions.)
    """
    result = compile_document(text)
    if result.errors:
        return None
    return run_program(result.program).document

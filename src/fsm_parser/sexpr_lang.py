"""Runner for the S-expression language definition (languages/sexpr/).

Pipeline mirrors json_lang, with two differences that are the point of
this language:

* the anchored tracker's stack alphabet is *expectation* states
  ({F: head pending, R: in body}), so it emits ROLE:HEAD:d / ROLE:ARG:d
  — positional grammatical relations — alongside the structural
  families;
* the output contract is a *sequence* of top-level forms (a Lisp file),
  so RunResult exposes `forms` and validity is "every stack entry is a
  completed form" rather than "exactly one document".

Instruction set: PUSH, NEW_LIST, APPEND (three ops; single container
type makes SETK unnecessary, and roles are pure annotation that the
builder ignores — they exist for downstream layers).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from typing import Any

from fsm_parser.combinators import literal
from fsm_parser.fsm import (
    FSM,
    Always,
    And,
    Emission,
    FSMBuilder,
    FSMScanner,
    HasLabel,
)
from fsm_parser.labels import LabelDelta
from fsm_parser.normalization import apply_deltas
from fsm_parser.slots import Slot, SourceSpan
from fsm_parser.tokens import ParserState

MAX_DEPTH = 3

_TOKEN = re.compile(r"[()]|[^()\s]+")


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
        if raw == "(":
            slot.labels.add("LPAREN", 1.0)
            slot.labels.add("PAREN", 1.0)
        elif raw == ")":
            slot.labels.add("RPAREN", 1.0)
            slot.labels.add("PAREN", 1.0)
        else:
            slot.labels.add("NUM" if re.fullmatch(r"-?\d+", raw) else "SYMBOL", 1.0)
            slot.labels.add("ATOM", 1.0)
            slot.labels.add(f"VAL:{raw}", 1.0)
        state.add_slot("token", slot)
    return state


# --- Layer 1: shape/role tracker -----------------------------------------------


def build_shape_role_tracker(max_depth: int = MAX_DEPTH) -> FSM:
    """Anchored machine over expectation stacks (layers.yaml).

    Stack symbols: "F" (head position pending) and "R" (in body).
    Consuming an element while top=F emits ROLE:HEAD and flips to R;
    while top=R it emits ROLE:ARG.
    """
    b = FSMBuilder("shape_role_tracker")
    stacks = [
        sigma for n in range(max_depth + 1) for sigma in product("FR", repeat=n)
    ]
    states = {sigma: b.state("".join(sigma) or "top") for sigma in stacks}
    overflow = b.state("overflow")
    b.start(states[()])
    b.accept(states[()])

    lparen, rparen, atom = HasLabel("LPAREN"), HasLabel("RPAREN"), HasLabel("ATOM")

    def role_emission(sigma, d):
        role = "HEAD" if sigma[-1] == "F" else "ARG"
        return Emission(f"ROLE:{role}:{d}", 1.0, offset=0)

    def flipped(sigma):
        return sigma[:-1] + ("R",)

    for sigma in stacks:
        d = len(sigma)
        src = states[sigma]
        # open a list: it is itself an element of the enclosing list
        if d < max_depth:
            ems = [
                Emission(f"DEPTH:{d + 1}", 1.0, offset=0),
                Emission(f"GROUP_START:{d + 1}", 1.0, offset=0),
            ]
            parent = sigma
            if sigma:
                ems.append(role_emission(sigma, d))
                parent = flipped(sigma)
            b.transition(src, lparen, states[parent + ("F",)], emissions=ems)
        else:
            b.transition(
                src, lparen, overflow,
                emissions=[Emission("ERROR:DEPTH_EXCEEDED", 1.0, offset=0)],
            )
        # close
        if sigma:
            ems = [
                Emission(f"DEPTH:{d}", 1.0, offset=0),
                Emission(f"GROUP_END:{d}", 1.0, offset=0),
            ]
            if sigma[:-1]:
                ems.append(Emission(f"ENCL:LIST:{d - 1}", 1.0, offset=0))
            b.transition(src, rparen, states[sigma[:-1]], emissions=ems)
        else:
            b.transition(
                src, rparen, src,
                emissions=[Emission("ERROR:UNBALANCED_CLOSE", 1.0, offset=0)],
            )
        # atoms
        ems = [Emission(f"DEPTH:{d}", 1.0, offset=0)]
        target = sigma
        if sigma:
            ems.append(Emission(f"CTX:LIST:{d}", 1.0, offset=0))
            ems.append(role_emission(sigma, d))
            target = flipped(sigma)
        b.transition(src, atom, states[target], emissions=ems)

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

    single("new_list", HasLabel("LPAREN"), "EXEC.0:NEW_LIST")
    single("push", HasLabel("ATOM"), "EXEC.0:PUSH(!{VAL})")
    for d in range(1, max_depth + 1):
        single(
            f"append_atom@{d}",
            And((HasLabel("ATOM"), HasLabel(f"CTX:LIST:{d}"))),
            "EXEC.1:APPEND",
        )
        if d < max_depth:
            single(
                f"append_list@{d}",
                And((HasLabel(f"GROUP_END:{d + 1}"), HasLabel(f"ENCL:LIST:{d}"))),
                "EXEC.1:APPEND",
            )
    return machines


@lru_cache(maxsize=4)
def _machines_for(max_depth: int) -> tuple[FSM, tuple[FSM, ...]]:
    return build_shape_role_tracker(max_depth), tuple(_emitters(max_depth))


# --- Projection and VM --------------------------------------------------------------


@dataclass
class Instruction:
    op: str                  # PUSH | NEW_LIST | APPEND
    operand: Any = None
    slot_id: str = ""
    rank: int = 0

    def __str__(self) -> str:
        if self.op == "PUSH":
            return f"PUSH {self.operand}" if isinstance(self.operand, int) else f"PUSH {self.operand!s}"
        return self.op


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
    return int(raw) if "NUM" in slot.labels else raw


def compile_forms(text: str, *, max_depth: int = MAX_DEPTH) -> CompileResult:
    state = initialize(text)
    scanner = FSMScanner()
    tracker, emitters = _machines_for(max_depth)

    deltas = scanner.transduce(tracker, state, anchored=True)
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
                        weight=1.0, source="shape_role_tracker")],
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
    def forms(self) -> list[Any] | None:
        """The sequence of top-level forms (a Lisp file), if valid."""
        return self.stack if self.valid else None


def run_program(program: list[Instruction]) -> RunResult:
    stack: list[Any] = []
    for ins in program:
        if ins.op == "PUSH":
            stack.append(ins.operand)
        elif ins.op == "NEW_LIST":
            stack.append([])
        elif ins.op == "APPEND":
            if len(stack) < 2 or not isinstance(stack[-2], list):
                return RunResult(stack=stack, valid=False)
            v = stack.pop()
            stack[-1].append(v)
        else:
            raise ValueError(f"unknown instruction {ins.op}")
    return RunResult(stack=stack, valid=len(stack) >= 1)


def parse(text: str) -> list[Any] | None:
    """Compile + run; the list of top-level forms, or None on errors."""
    result = compile_forms(text)
    if result.errors:
        return None
    return run_program(result.program).forms

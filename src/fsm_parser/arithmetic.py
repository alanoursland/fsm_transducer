"""Runner for the arithmetic language definition (languages/arithmetic/).

Implements the contract in ``languages/arithmetic/*.yaml`` with real
machines. Pipeline:

1. tokenize, add BOF/EOF sentinel slots (parser end-markers; they make
   "not followed by X" expressible as a consuming guard token)
2. lexicon pass (NUM/VAL/operator/paren class labels)
3. anchored depth tracker -> DEPTH:d, GROUP_START/END:d, ERROR:*
4. per-depth term markers (deepest first) -> TERM_{d}, TERM_{d}_START/_END
   (spec families TERM_START:d / TERM_END:d)
5. per-depth instruction emitters -> EXEC.r labels
6. projection: EXEC labels in (token, rank) order -> program
7. a small stack VM to validate programs

Design notes vs the spec:

* Maximal-munch for terms and additive right operands is enforced with
  *guard tokens*: a pattern only completes by consuming a following
  token that is not a multiplicative operator at that depth. The EOF
  sentinel guarantees the guard token exists at end of input (and BOF
  the symmetric left guard), so no lookahead machinery is needed.
* Multiplicative emitters need no maximality: each ``* /`` fires at the
  end of its immediate right operand, which is exactly left-associative
  RPN order.
* Operand ends are located with an overwriting capture register
  (``end``) written by the final consuming transition of each operand
  alternative; emissions anchor on it (``CaptureAnchor``), the same
  tagged-NFA mechanism the regex front-end groups use.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from fsm_parser.combinators import alt, concat, literal, star
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
from fsm_parser.regex_compile import _decorate_group
from fsm_parser.slots import Slot, SourceSpan
from fsm_parser.tokens import ParserState

MAX_DEPTH = 3

_TOKEN = re.compile(r"\d+|[()+\-*/]|\S")

_OP_CLASSES = {
    "+": ("OP:ADD", "ADDITIVE"),
    "-": ("OP:SUB", "ADDITIVE"),
    "*": ("OP:MUL", "MULTIPLICATIVE"),
    "/": ("OP:DIV", "MULTIPLICATIVE"),
}


# --- Layer 0: tokenization + lexicon -----------------------------------------


def initialize(text: str) -> ParserState:
    """Tokenize and apply the lexicon (languages/arithmetic/lexicon.yaml).

    Adds BOF/EOF sentinel slots (kind="meta") so boundary guards are
    ordinary consuming transitions; they carry no class labels and are
    excluded from projection.
    """
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
            id=f"token:{i}",
            kind="token",
            stream="token",
            order=float(i),
            text=raw,
            source_span=SourceSpan(idx, idx + len(raw)),
        )
        slot.labels.add(f"TEXT:{raw}", 1.0)
        if raw.isdigit():
            slot.labels.add("NUM", 1.0)
            slot.labels.add(f"VAL:{raw}", 1.0)
        elif raw in _OP_CLASSES:
            specific, super_class = _OP_CLASSES[raw]
            slot.labels.add(specific, 1.0)
            slot.labels.add("OPERATOR", 1.0)
            slot.labels.add(super_class, 1.0)
        elif raw == "(":
            slot.labels.add("LPAREN", 1.0)
            slot.labels.add("PAREN", 1.0)
        elif raw == ")":
            slot.labels.add("RPAREN", 1.0)
            slot.labels.add("PAREN", 1.0)
        else:
            slot.labels.add("ERROR:UNKNOWN_TOKEN", 1.0)
        state.add_slot("token", slot)
        i += 1
    eof = Slot(id="meta:eof", kind="meta", stream="token", order=float(i), text="")
    eof.labels.add("EOF", 1.0)
    state.add_slot("token", eof)
    return state


# --- Layer 1: depth tracker ---------------------------------------------------


def build_depth_tracker(max_depth: int = MAX_DEPTH) -> FSM:
    """Anchored 5-state machine: layers.yaml `depth_tracker`."""
    b = FSMBuilder("depth_tracker")
    depth_states = [b.state(f"d{d}") for d in range(max_depth + 1)]
    overflow = b.state("overflow")
    b.start(depth_states[0])
    b.accept(depth_states[0])
    lparen, rparen = HasLabel("LPAREN"), HasLabel("RPAREN")
    not_paren = Not(HasLabel("PAREN"))
    for d in range(max_depth):
        b.transition(
            depth_states[d], lparen, depth_states[d + 1],
            emissions=[Emission(f"DEPTH:{d + 1}", 1.0, offset=0),
                       Emission(f"GROUP_START:{d + 1}", 1.0, offset=0)],
        )
        b.transition(
            depth_states[d + 1], rparen, depth_states[d],
            emissions=[Emission(f"DEPTH:{d + 1}", 1.0, offset=0),
                       Emission(f"GROUP_END:{d + 1}", 1.0, offset=0)],
        )
    b.transition(
        depth_states[max_depth], lparen, overflow,
        emissions=[Emission("ERROR:DEPTH_EXCEEDED", 1.0, offset=0)],
    )
    b.transition(
        depth_states[0], rparen, depth_states[0],
        emissions=[Emission("ERROR:UNBALANCED_CLOSE", 1.0, offset=0)],
    )
    for d in range(max_depth + 1):
        b.transition(
            depth_states[d], not_paren, depth_states[d],
            emissions=[Emission(f"DEPTH:{d}", 1.0, offset=0)],
        )
    b.transition(
        overflow, Always(), overflow,
        emissions=[Emission("DEPTH:OVERFLOW", 1.0, offset=0)],
    )
    return b.build()


# --- Per-depth condition helpers ----------------------------------------------


def _d(d: int) -> HasLabel:
    return HasLabel(f"DEPTH:{d}")


def _mulop(d: int) -> And:
    return And((HasLabel("MULTIPLICATIVE"), _d(d)))


def _operand(d: int) -> FSM:
    """An operand at depth d: a NUM, or a whole depth-(d+1) group.

    The final consuming transition of each alternative writes the
    ``end`` capture register (overwrite), so after any operand match
    ``end`` holds its last slot.
    """
    end_cap = Capture("end", kind="index")
    num = literal(And((HasLabel("NUM"), _d(d))), captures=[end_cap])
    if d >= MAX_DEPTH:
        return num
    group = concat(
        literal(HasLabel(f"GROUP_START:{d + 1}")),
        star(literal(Not(HasLabel(f"GROUP_END:{d + 1}")))),
        literal(HasLabel(f"GROUP_END:{d + 1}"), captures=[end_cap]),
    )
    return alt(num, group)


def _chain(d: int) -> FSM:
    """operand ( mulop operand )* — a multiplicative chain at depth d."""
    return concat(_operand(d), star(concat(literal(_mulop(d)), _operand(d))))


# --- Layer 3: term markers ------------------------------------------------------


def build_term_marker(d: int) -> FSM:
    """Mark maximal multiplicative chains: TERM_{d} / _START / _END.

    Maximality via boundary guards: the token before the chain must not
    be a depth-d multiplicative operator, NUM, or a closing inner-group
    paren (otherwise we started mid-chain); the token after must not be
    a depth-d multiplicative operator. BOF/EOF sentinels guarantee the
    guard tokens exist.
    """
    left_bad = [_mulop(d), And((HasLabel("NUM"), _d(d)))]
    if d < MAX_DEPTH:
        left_bad.append(HasLabel(f"GROUP_END:{d + 1}"))
    left_guard = Not(Or(tuple(left_bad)))
    right_guard = Not(_mulop(d))
    body = _decorate_group(_chain(d), f"TERM_{d}", 1.0)
    m = concat(literal(left_guard), body, literal(right_guard))
    m.name = f"term_marker@{d}"
    return m


# --- Layer 4: instruction emitters ----------------------------------------------


def build_push_emitter() -> FSM:
    m = literal(
        HasLabel("NUM"),
        emissions=[Emission("EXEC.0:PUSH(!{VAL})", 1.0, offset=0)],
    )
    m.name = "push_emitter"
    return m


def build_pair_emitter(d: int, op_label: str, instr: str) -> FSM:
    """operand <op> operand -> EXEC.1 at the right operand's end.

    Firing per adjacent pair is exactly left-associative RPN order; no
    maximality needed.
    """
    m = concat(
        _operand(d),
        literal(And((HasLabel(op_label), _d(d)))),
        _operand(d),
    )
    # attach the emission to every transition that can finish the rhs:
    # simplest correct form is an accept-side epsilon; reuse the group
    # envelope trick via a builder wrapper.
    m = _with_exit_emission(m, Emission(f"EXEC.1:{instr}", 1.0, anchor=CaptureAnchor("end")))
    m.name = f"{instr.lower()}_emitter@{d}"
    return m


def build_additive_emitter(d: int, op_label: str, instr: str) -> FSM:
    """<op> chain guard -> EXEC.2 at the chain's end.

    The guard token (anything but a depth-d multiplicative operator —
    EOF included) enforces that the chain is maximal, which is what
    makes the additive operator fire after its *entire* right term.
    """
    m = concat(
        literal(And((HasLabel(op_label), _d(d)))),
        _chain(d),
        literal(
            Not(_mulop(d)),
            emissions=[Emission(f"EXEC.2:{instr}", 1.0, anchor=CaptureAnchor("end"))],
        ),
    )
    m.name = f"{instr.lower()}_emitter@{d}"
    return m


def _with_exit_emission(machine: FSM, emission: Emission) -> FSM:
    """Wrap a machine so `emission` fires when it accepts (on_enter of a
    fresh exit state, the same envelope used by regex groups)."""
    from fsm_parser.combinators import _embed

    b = FSMBuilder(machine.name)
    sub_start, sub_accepts = _embed(b, machine)
    exit_state = b.state("exit")
    b.start(sub_start).accept(exit_state)
    for a in sub_accepts:
        b.epsilon(a, exit_state)
    b.state_info(exit_state, on_enter=(emission,))
    return b.build()


# --- Pipeline -------------------------------------------------------------------


@dataclass
class Instruction:
    op: str            # PUSH | ADD | SUB | MUL | DIV
    operand: float | None
    slot_id: str
    rank: int

    def __str__(self) -> str:
        if self.operand is not None:
            g = int(self.operand)
            return f"PUSH {g}" if g == self.operand else f"PUSH {self.operand}"
        return self.op


@dataclass
class CompileResult:
    state: ParserState       # the label field
    program: list[Instruction]
    errors: list[str]        # distinct ERROR:* labels present in the field


_EXEC = re.compile(r"EXEC\.(\d+):([A-Z]+)(?:\((.*)\))?$")


def _resolve_operand(slot: Slot, ref: str) -> float:
    if ref != "!{VAL}":
        raise ValueError(f"unsupported operand reference: {ref!r}")
    vals = sorted(
        ((w, lab) for lab, w in slot.labels.items() if lab.startswith("VAL:")),
        reverse=True,
    )
    if not vals:
        raise ValueError(f"no VAL label on {slot.id} for operand reference")
    # instructions.yaml resolution policy: argmax with a 0.5x margin.
    if len(vals) > 1 and vals[1][0] >= 0.5 * vals[0][0]:
        raise ValueError(f"ambiguous VAL on {slot.id}: {vals[:2]}")
    return float(vals[0][1].split(":", 1)[1])


@lru_cache(maxsize=4)
def _machines_for(max_depth: int) -> tuple[FSM, tuple[FSM, ...]]:
    """Machines are input-independent; build once per depth limit."""
    layer: list[FSM] = []
    for d in range(max_depth, -1, -1):
        layer.append(build_term_marker(d))
        layer.append(build_pair_emitter(d, "OP:MUL", "MUL"))
        layer.append(build_pair_emitter(d, "OP:DIV", "DIV"))
        layer.append(build_additive_emitter(d, "OP:ADD", "ADD"))
        layer.append(build_additive_emitter(d, "OP:SUB", "SUB"))
    layer.append(build_push_emitter())
    return build_depth_tracker(max_depth), tuple(layer)


def compile_expression(text: str, *, max_depth: int = MAX_DEPTH) -> CompileResult:
    state = initialize(text)
    scanner = FSMScanner()
    depth_tracker, layer_machines = _machines_for(max_depth)

    # depth pass (anchored, the only global machine)
    deltas = scanner.transduce(depth_tracker, state, anchored=True)
    apply_deltas(state, deltas)
    # runner-level end check: more opens than closes => unclosed group
    opens = sum(
        1 for s in state.tokens for lab in s.labels.weights if lab.startswith("GROUP_START:")
    )
    closes = sum(
        1 for s in state.tokens for lab in s.labels.weights if lab.startswith("GROUP_END:")
    )
    real = [s for s in state.tokens if s.kind == "token"]
    if opens > closes and real:
        apply_deltas(
            state,
            [LabelDelta(slot_id=real[-1].id, label="ERROR:UNBALANCED_OPEN",
                        weight=1.0, source="depth_tracker")],
        )

    # term markers + emitters, deepest depth first
    layer_deltas: list[LabelDelta] = []
    for m in layer_machines:
        layer_deltas.extend(scanner.transduce(m, state))
    apply_deltas(state, layer_deltas)

    # projection: EXEC labels in (token order, rank) order
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
            operand = _resolve_operand(slot, arg) if arg else None
            program.append(Instruction(op=op, operand=operand, slot_id=slot.id, rank=rank))

    errors = sorted(
        {
            lab
            for s in state.tokens
            for lab in s.labels.weights
            if lab.startswith("ERROR:")
        }
    )
    return CompileResult(state=state, program=program, errors=errors)


# --- Stack VM (instructions.yaml semantics) --------------------------------------


@dataclass
class RunResult:
    stack: list[float]
    valid: bool          # validity condition 1: exactly one value remains

    @property
    def value(self) -> float | None:
        return self.stack[0] if self.valid else None


def run_program(program: list[Instruction]) -> RunResult:
    stack: list[float] = []
    for ins in program:
        if ins.op == "PUSH":
            stack.append(ins.operand)  # type: ignore[arg-type]
            continue
        if len(stack) < 2:
            return RunResult(stack=stack, valid=False)
        b, a = stack.pop(), stack.pop()
        if ins.op == "ADD":
            stack.append(a + b)
        elif ins.op == "SUB":
            stack.append(a - b)
        elif ins.op == "MUL":
            stack.append(a * b)
        elif ins.op == "DIV":
            stack.append(a / b)
        else:
            raise ValueError(f"unknown instruction {ins.op}")
    return RunResult(stack=stack, valid=len(stack) == 1)


def evaluate(text: str) -> float | None:
    """Compile, run, return the value.

    None if the field carries ERROR labels or the program leaves the
    stack in an invalid state — the two halves of the validity story
    (instructions.yaml condition 4 and condition 1 respectively).
    """
    result = compile_expression(text)
    if result.errors:
        return None
    return run_program(result.program).value

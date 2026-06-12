"""Runner for the JavaScript subset (languages/jssub/).

The pipeline's new stage is retokenization: tokenize naively (every
'/' is an ambiguous SLASH), run the slash story machine to decide
division vs regex literal, then MERGE each REGEX_START..REGEX_END span
into one synthesized REGEX slot before any structural machinery runs.
Token boundaries are downstream of story state — context-sensitive
tokenization as accretion.

Everything after retokenization is imported from imp unchanged:
bracket tracker, minus story, scope checkers, expression emitters,
statement emitters, and the VM. New code: the naive lexer, the slash
story machine, the retokenizer, regex values, one push emitter.

The slash story keys on the OPERAND_END *event* label (emitted by the
lexer on NUM/IDENT/RPAREN and by the retokenizer on REGEX slots) — the
first tier-1 story-event consumer (notes/story_machines.md). imp's
imported minus story still keys on token classes and therefore cannot
learn that REGEX completes an operand: `/a/ - 2` mislabels the minus
(documented, test-pinned). The recorded refactor is to migrate
minus_story to OPERAND_END.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from fsm_parser.combinators import literal
from fsm_parser.fsm import (
    FSM,
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
    _expression_emitters,
    _statement_emitters,
    build_bracket_tracker,
    build_minus_story,
    build_scope_checker,
    run_program,  # noqa: F401  (re-exported: jssub's VM is imp's)
)
from fsm_parser.labels import LabelDelta
from fsm_parser.normalization import apply_deltas
from fsm_parser.slots import ProvenanceEdge, Slot, SourceSpan
from fsm_parser.tokens import ParserState

_TOKEN = re.compile(r"==|[(){};=+\-*/<>]|\d+|[A-Za-z_]\w*|\S")
_KEYWORDS = {"let": "LET", "if": "IF", "print": "PRINT_KW"}
_PUNCT = {
    "=": "ASSIGN", "==": "EQ_OP", ">": "GT_OP", "<": "LT_OP",
    "+": "ADD_OP", "-": "SUB_OP", "*": "MUL_OP", "/": "SLASH",
    "(": "LPAREN", ")": "RPAREN", "{": "LBRACE", "}": "RBRACE", ";": "SEMI",
}
_SUPER = {
    "EQ_OP": "CMP_OP", "GT_OP": "CMP_OP", "LT_OP": "CMP_OP",
    "ADD_OP": "ADDITIVE", "SUB_OP": "ADDITIVE", "MUL_OP": "MULTIPLICATIVE",
}
_OPERAND_END_CLASSES = {"NUM", "IDENT", "RPAREN"}


@dataclass(frozen=True)
class RegexVal:
    pattern: str

    def __str__(self) -> str:
        return f"/{self.pattern}/"


# --- Layer 0: naive tokenization --------------------------------------------------


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
            if cls in _OPERAND_END_CLASSES:
                slot.labels.add("OPERAND_END", 1.0)
        elif raw.isdigit():
            slot.labels.add("NUM", 1.0)
            slot.labels.add(f"VAL:{raw}", 1.0)
            slot.labels.add("OPERAND_END", 1.0)
        elif re.fullmatch(r"[A-Za-z_]\w*", raw):
            slot.labels.add("IDENT", 1.0)
            slot.labels.add(f"VAL:{raw}", 1.0)
            slot.labels.add("OPERAND_END", 1.0)
        else:
            slot.labels.add("ERROR:UNKNOWN_TOKEN", 1.0)
        state.add_slot("token", slot)
        i += 1
    eof = Slot(id="meta:eof", kind="meta", stream="token", order=float(i), text="")
    eof.labels.add("EOF", 1.0)
    state.add_slot("token", eof)
    return state


# --- Layer 1: slash story machine ---------------------------------------------------


def build_slash_story() -> FSM:
    """Three-state story machine deciding division vs regex literal.

    Keys on the OPERAND_END event label, not token classes — the
    adapter (lexer/retokenizer) decides what completes an operand.
    """
    b = FSMBuilder("slash_story")
    eo = b.state("expect_operand")
    ep = b.state("expect_operator")
    ir = b.state("in_regex")
    b.start(eo)
    b.accept(eo, ep)  # ending in in_regex => unterminated (runner check)

    slash = HasLabel("SLASH")
    opend = HasLabel("OPERAND_END")
    other = Not(Or((slash, opend)))

    b.transition(eo, slash, ir, emissions=[Emission("REGEX_START", 1.0, offset=0)])
    b.transition(eo, opend, ep)
    b.transition(eo, other, eo)

    b.transition(ep, slash, eo,
                 emissions=[Emission("DIV_OP", 1.0, offset=0),
                            Emission("MULTIPLICATIVE", 1.0, offset=0)])
    b.transition(ep, opend, ep)
    b.transition(ep, other, eo)

    b.transition(ir, slash, ep, emissions=[Emission("REGEX_END", 1.0, offset=0)])
    b.transition(ir, Not(slash), ir)
    return b.build()


# --- Layer 1b: retokenization ---------------------------------------------------------


def retokenize(text: str, state: ParserState) -> ParserState:
    """Merge REGEX_START..REGEX_END spans into synthesized REGEX slots.

    The merged slot's pattern is recovered exactly from source spans
    (whitespace preserved); provenance edges point at the raw tokens it
    replaced. Unmatched REGEX_START spans are left unmerged.
    """
    new = ParserState()
    slots = state.stream("token")
    order = 0.0
    regex_n = 0
    i = 0
    while i < len(slots):
        slot = slots[i]
        if "REGEX_START" in slot.labels:
            j = i + 1
            while j < len(slots) and "REGEX_END" not in slots[j].labels:
                j += 1
            if j < len(slots):  # matched: merge slots[i..j]
                start, end = slot, slots[j]
                pattern = text[start.source_span.end:end.source_span.start]
                merged = Slot(
                    id=f"regex:{regex_n}", kind="token", stream="token",
                    order=order,
                    text=text[start.source_span.start:end.source_span.end],
                    source_span=SourceSpan(start.source_span.start,
                                           end.source_span.end),
                    parents=tuple(
                        ProvenanceEdge("derived_from", s.id)
                        for s in slots[i:j + 1]
                    ),
                )
                regex_n += 1
                merged.labels.add("REGEX", 1.0)
                merged.labels.add("OPERAND_END", 1.0)
                merged.labels.add(f"VAL:{pattern}", 1.0)
                new.add_slot("token", merged)
                order += 1.0
                i = j + 1
                continue
        slot.order = order
        order += 1.0
        new.add_slot("token", slot)
        i += 1
    return new


# --- Compile -----------------------------------------------------------------------------


def _push_regex() -> FSM:
    m = literal(HasLabel("REGEX"),
                emissions=[Emission("EXEC.0:PUSH(!{VAL})", 1.0, offset=0)])
    m.name = "push_regex"
    return m


@lru_cache(maxsize=2)
def _static_machines() -> tuple[FSM, FSM, FSM, tuple[FSM, ...]]:
    return (
        build_slash_story(),
        build_bracket_tracker(MAX_DEPTH),
        build_minus_story(),
        tuple(_expression_emitters(MAX_DEPTH) + _statement_emitters()
              + [_push_regex()]),
    )


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
    if "REGEX" in target.labels:
        return RegexVal(raw)
    return int(raw) if "NUM" in target.labels else raw


def compile_program(text: str) -> CompileResult:
    state = initialize(text)
    scanner = FSMScanner()
    slash_story, tracker, minus_story, emitters = _static_machines()

    # decide every '/' on the naive stream, then fix token boundaries
    apply_deltas(state, scanner.transduce(slash_story, state, anchored=True))
    starts = sum(1 for s in state.tokens for lab in s.labels.weights
                 if lab == "REGEX_START")
    ends = sum(1 for s in state.tokens for lab in s.labels.weights
               if lab == "REGEX_END")
    state = retokenize(text, state)
    real = [s for s in state.tokens if s.kind == "token"]
    if starts > ends and real:
        apply_deltas(state, [LabelDelta(slot_id=real[-1].id,
                                        label="ERROR:UNTERMINATED_REGEX",
                                        weight=1.0, source="slash_story")])

    # everything below is imp's pipeline, on the retokenized stream
    apply_deltas(state, scanner.transduce(tracker, state, anchored=True))
    opens = sum(1 for s in state.tokens for lab in s.labels.weights
                if lab.startswith("GROUP_START:"))
    closes = sum(1 for s in state.tokens for lab in s.labels.weights
                 if lab.startswith("GROUP_END:"))
    if opens > closes and real:
        apply_deltas(state, [LabelDelta(slot_id=real[-1].id,
                                        label="ERROR:UNBALANCED_OPEN",
                                        weight=1.0, source="bracket_tracker")])
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


def execute(text: str):
    result = compile_program(text)
    if result.errors:
        return None
    return run_program(result.program)

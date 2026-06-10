"""Character-stream blocks: classification and char-to-token reduction.

These are the first shape-changing blocks. ``CharClassBlock`` is an
annotating transducer over the ``"char"`` stream; ``SimpleCharToTokenReducer``
is a reducing transducer that emits ``AddSlot`` deltas into a target
token stream while leaving the char stream untouched.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from fsm_parser.labels import (
    AddSlot,
    LabelBag,
    LabelDelta,
    RepresentationDelta,
)
from fsm_parser.slots import ProvenanceEdge, Slot, SourceSpan
from fsm_parser.tokens import ParserState

_OPERATOR_LABELS = {
    "+": "TOKEN:PLUS",
    "-": "TOKEN:MINUS",
    "*": "TOKEN:STAR",
    "/": "TOKEN:SLASH",
    "%": "TOKEN:PERCENT",
    "=": "TOKEN:EQ",
    "<": "TOKEN:LT",
    ">": "TOKEN:GT",
    "(": "TOKEN:LPAREN",
    ")": "TOKEN:RPAREN",
    "[": "TOKEN:LBRACKET",
    "]": "TOKEN:RBRACKET",
    "{": "TOKEN:LBRACE",
    "}": "TOKEN:RBRACE",
    ",": "TOKEN:COMMA",
    ";": "TOKEN:SEMICOLON",
    ".": "TOKEN:DOT",
    ":": "TOKEN:COLON",
}


@dataclass
class CharClassBlock:
    """Annotate char-stream slots with character-class labels."""

    name: str = "char_classes"
    consumes: str = "char"
    emits_to: str = "char"

    def apply(self, state: ParserState) -> list[RepresentationDelta]:
        deltas: list[RepresentationDelta] = []
        for slot in state.stream(self.consumes):
            ch = slot.text or ""
            if not ch:
                continue
            if ch.isalpha():
                deltas.append(LabelDelta(slot_id=slot.id, label="CHAR:LETTER", weight=1.0, source=self.name))
            if ch.isdigit():
                deltas.append(LabelDelta(slot_id=slot.id, label="CHAR:DIGIT", weight=1.0, source=self.name))
            if ch.isspace():
                deltas.append(LabelDelta(slot_id=slot.id, label="CHAR:WHITESPACE", weight=1.0, source=self.name))
            if ch in _OPERATOR_LABELS:
                deltas.append(LabelDelta(slot_id=slot.id, label="CHAR:OPERATOR", weight=1.0, source=self.name))
            if ch == "_":
                deltas.append(LabelDelta(slot_id=slot.id, label="CHAR:UNDERSCORE", weight=1.0, source=self.name))
            if ch in "([{":
                deltas.append(LabelDelta(slot_id=slot.id, label="CHAR:OPEN_DELIM", weight=1.0, source=self.name))
            if ch in ")]}":
                deltas.append(LabelDelta(slot_id=slot.id, label="CHAR:CLOSE_DELIM", weight=1.0, source=self.name))
            if ch in "\"'":
                deltas.append(LabelDelta(slot_id=slot.id, label="CHAR:QUOTE", weight=1.0, source=self.name))
        return deltas


def _is_ident_start(ch: str) -> bool:
    return ch.isalpha() or ch == "_"


def _is_ident_continue(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


@dataclass
class SimpleCharToTokenReducer:
    """Reduce runs of char slots into token slots in the target stream.

    Recognized atoms:

    - identifier runs (``letter|_``, then ``letter|digit|_``)
    - digit runs (NUMBER)
    - single-character operators / delimiters listed in ``_OPERATOR_LABELS``
    - whitespace (skipped by default; preserve with ``emit_whitespace=True``)

    The reducer leaves char slots intact. Each new token slot carries a
    ``derived_from`` provenance edge per contributing char slot and a
    ``SourceSpan`` covering the character range.
    """

    name: str = "char_to_token"
    consumes: str = "char"
    emits_to: str = "token"
    emit_whitespace: bool = False

    def apply(self, state: ParserState) -> list[RepresentationDelta]:
        chars = state.stream(self.consumes)
        deltas: list[RepresentationDelta] = []
        i = 0
        while i < len(chars):
            slot = chars[i]
            ch = slot.text or ""
            if not ch:
                i += 1
                continue

            if ch.isspace():
                if self.emit_whitespace:
                    deltas.append(self._make_token(state, [slot], "TOKEN:WHITESPACE"))
                i += 1
                continue

            if _is_ident_start(ch):
                start = i
                while i < len(chars) and _is_ident_continue(chars[i].text or ""):
                    i += 1
                deltas.append(self._make_token(state, chars[start:i], "TOKEN:IDENT"))
                continue

            if ch.isdigit():
                start = i
                while i < len(chars) and (chars[i].text or "").isdigit():
                    i += 1
                deltas.append(self._make_token(state, chars[start:i], "TOKEN:NUMBER"))
                continue

            label = _OPERATOR_LABELS.get(ch, "TOKEN:UNKNOWN")
            deltas.append(self._make_token(state, [slot], label))
            i += 1

        return deltas

    # -- internals -----------------------------------------------------

    def _make_token(
        self,
        state: ParserState,
        parent_slots: Iterable[Slot],
        token_label: str,
    ) -> AddSlot:
        parent_slots = list(parent_slots)
        text = "".join((s.text or "") for s in parent_slots)
        first = parent_slots[0]
        last = parent_slots[-1]
        span = None
        if first.source_span is not None and last.source_span is not None:
            span = SourceSpan(first.source_span.start, last.source_span.end)
        slot_id = state.next_id(self.emits_to)
        labels = LabelBag()
        labels.add(token_label, 1.0)
        labels.add(f"TEXT:{text}", 1.0)
        labels.add(f"LOWER:{text.lower()}", 1.0)
        labels.add("TOKEN", 1.0)
        token = Slot(
            id=slot_id,
            kind="token",
            stream=self.emits_to,
            order=first.order,
            text=text,
            source_span=span,
            parents=tuple(
                ProvenanceEdge("derived_from", s.id) for s in parent_slots
            ),
            labels=labels,
        )
        return AddSlot(stream=self.emits_to, slot=token, source=self.name)


@dataclass
class AmbiguousShiftRightReducer:
    """Demonstrate overlapping token candidates for the ``>>`` problem.

    Whenever two consecutive ``>`` characters are seen, this reducer
    emits three token candidates whose source spans overlap:

    - ``TOKEN:SHIFT_RIGHT`` covering both characters
    - ``TOKEN:GT`` for the first character
    - ``TOKEN:GT`` for the second character

    The two single-``>`` candidates carry an ``alternate_to`` edge back
    to the combined candidate so projections can choose one
    interpretation.
    """

    name: str = "ambiguous_shift_right"
    consumes: str = "char"
    emits_to: str = "token"

    def apply(self, state: ParserState) -> list[RepresentationDelta]:
        chars = state.stream(self.consumes)
        deltas: list[RepresentationDelta] = []
        i = 0
        while i < len(chars) - 1:
            a = chars[i]
            b = chars[i + 1]
            if (a.text or "") == ">" and (b.text or "") == ">":
                shift_id = state.next_id(self.emits_to)
                shift_span = None
                if a.source_span and b.source_span:
                    shift_span = SourceSpan(a.source_span.start, b.source_span.end)
                shift = Slot(
                    id=shift_id,
                    kind="token",
                    stream=self.emits_to,
                    order=a.order,
                    text=">>",
                    source_span=shift_span,
                    parents=(
                        ProvenanceEdge("derived_from", a.id),
                        ProvenanceEdge("derived_from", b.id),
                    ),
                    labels=LabelBag(),
                )
                shift.labels.add("TOKEN:SHIFT_RIGHT", 0.6)
                shift.labels.add("TEXT:>>", 1.0)

                gt1_id = state.next_id(self.emits_to)
                gt1 = Slot(
                    id=gt1_id,
                    kind="token",
                    stream=self.emits_to,
                    order=a.order,
                    text=">",
                    source_span=a.source_span,
                    parents=(
                        ProvenanceEdge("derived_from", a.id),
                        ProvenanceEdge("alternate_to", shift_id),
                    ),
                    labels=LabelBag(),
                )
                gt1.labels.add("TOKEN:GT", 0.55)
                gt1.labels.add("TEXT:>", 1.0)

                gt2_id = state.next_id(self.emits_to)
                gt2 = Slot(
                    id=gt2_id,
                    kind="token",
                    stream=self.emits_to,
                    order=b.order,
                    text=">",
                    source_span=b.source_span,
                    parents=(
                        ProvenanceEdge("derived_from", b.id),
                        ProvenanceEdge("alternate_to", shift_id),
                    ),
                    labels=LabelBag(),
                )
                gt2.labels.add("TOKEN:GT", 0.55)
                gt2.labels.add("TEXT:>", 1.0)

                deltas.append(AddSlot(self.emits_to, shift, self.name))
                deltas.append(AddSlot(self.emits_to, gt1, self.name))
                deltas.append(AddSlot(self.emits_to, gt2, self.name))
                i += 2
                continue
            i += 1
        return deltas

"""Parser blocks. Every block declares which stream it consumes / writes to."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from fsm_parser.fsm import FSM, FSMScanner
from fsm_parser.labels import LabelDelta, RepresentationDelta
from fsm_parser.tokens import ParserState


class ParserBlock(Protocol):
    name: str
    consumes: str
    emits_to: str

    def apply(self, state: ParserState) -> list[RepresentationDelta]: ...


@dataclass
class LexicalBlock:
    """Map slot ``text`` to weighted labels via a dictionary."""

    name: str
    entries: dict[str, dict[str, float]]
    consumes: str = "token"
    emits_to: str = "token"

    def apply(self, state: ParserState) -> list[RepresentationDelta]:
        deltas: list[RepresentationDelta] = []
        for slot in state.stream(self.consumes):
            text = slot.text or ""
            key = text.lower()
            for label, weight in self.entries.get(key, {}).items():
                deltas.append(LabelDelta(slot_id=slot.id, label=label, weight=weight, source=self.name))
        return deltas


@dataclass
class FSMBlock:
    name: str
    fsms: list[FSM]
    consumes: str = "token"
    emits_to: str = "token"
    scanner: FSMScanner = field(default_factory=FSMScanner)

    def apply(self, state: ParserState) -> list[RepresentationDelta]:
        deltas: list[RepresentationDelta] = []
        for fsm in self.fsms:
            deltas.extend(self.scanner.scan(fsm, state, stream=self.consumes))
        return deltas

    def add(self, fsm: FSM) -> "FSMBlock":
        self.fsms.append(fsm)
        return self


@dataclass
class CallableBlock:
    """Adapter wrapping any function as a ``ParserBlock``."""

    name: str
    fn: object
    consumes: str = "token"
    emits_to: str = "token"

    def apply(self, state: ParserState) -> list[RepresentationDelta]:
        result = self.fn(state)  # type: ignore[operator]
        return list(result)

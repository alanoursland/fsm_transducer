"""Parser blocks: the units a pipeline composes.

Every block consumes a ``ParserState`` and returns ``LabelDelta``s. Blocks
do not mutate state directly; the engine applies deltas after all blocks
in a layer have run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol

from fsm_parser.fsm import FSM, FSMScanner
from fsm_parser.labels import LabelDelta
from fsm_parser.tokens import ParserState


class ParserBlock(Protocol):
    name: str

    def apply(self, state: ParserState) -> list[LabelDelta]: ...


@dataclass
class LexicalBlock:
    """One-token map from lowercase text to weighted labels.

    Equivalent to a collection of two-state FSMs that each match a single
    token. Implemented directly for simplicity and speed; a future
    refactor can route it through ``FSMBlock`` without changing the
    interface.
    """

    name: str
    entries: dict[str, dict[str, float]]

    def apply(self, state: ParserState) -> list[LabelDelta]:
        deltas: list[LabelDelta] = []
        for token in state.tokens:
            key = token.text.lower()
            for label, weight in self.entries.get(key, {}).items():
                deltas.append(LabelDelta(token.index, label, weight, self.name))
        return deltas


@dataclass
class FSMBlock:
    """Run a collection of FSMs through the scanner and gather deltas."""

    name: str
    fsms: list[FSM]
    scanner: FSMScanner = field(default_factory=FSMScanner)

    def apply(self, state: ParserState) -> list[LabelDelta]:
        deltas: list[LabelDelta] = []
        for fsm in self.fsms:
            deltas.extend(self.scanner.scan(fsm, state))
        return deltas

    def add(self, fsm: FSM) -> "FSMBlock":
        self.fsms.append(fsm)
        return self


@dataclass
class CallableBlock:
    """Adapter wrapping any function as a ``ParserBlock``."""

    name: str
    fn: object  # Callable[[ParserState], Iterable[LabelDelta]]

    def apply(self, state: ParserState) -> list[LabelDelta]:
        result = self.fn(state)  # type: ignore[operator]
        return list(result)

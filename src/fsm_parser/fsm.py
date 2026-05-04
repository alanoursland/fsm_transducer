"""Weighted finite-state machine core.

A real FSM is built from explicit states and transitions. The scanner runs
each FSM at every starting position over a token sequence and tracks active
paths NFA-style. Emissions buffered along a path are realized as
``LabelDelta``s when the path reaches an accept state.

Pattern-rule shortcuts (linear chains of conditions) are provided as a
helper that compiles into the same FSM structure, so callers and the
scanner are uniform regardless of how the machine was built.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass, field
from typing import Callable, Iterable, Protocol, Sequence

from fsm_parser.labels import LabelDelta
from fsm_parser.tokens import ParserState, Token


@dataclass(frozen=True)
class StateId:
    value: int
    name: str | None = None

    def __repr__(self) -> str:
        if self.name:
            return f"State({self.value}:{self.name})"
        return f"State({self.value})"


@dataclass(frozen=True)
class Emission:
    """A label to add when the carrying path accepts.

    ``offset`` is relative to the token whose consumption fired the
    transition that produced this emission. ``offset=0`` targets that
    token; ``offset=-1`` targets the previous token.
    """

    label: str
    weight: float
    offset: int = 0


class Condition(Protocol):
    def matches(self, frame: Token) -> bool: ...


@dataclass(frozen=True)
class HasLabel:
    label: str
    min_weight: float = 0.0

    def matches(self, frame: Token) -> bool:
        return frame.labels.get(self.label) > self.min_weight


@dataclass(frozen=True)
class HasAnyLabel:
    labels: tuple[str, ...]
    min_weight: float = 0.0

    def matches(self, frame: Token) -> bool:
        return any(frame.labels.get(l) > self.min_weight for l in self.labels)


@dataclass(frozen=True)
class HasAllLabels:
    labels: tuple[str, ...]
    min_weight: float = 0.0

    def matches(self, frame: Token) -> bool:
        return all(frame.labels.get(l) > self.min_weight for l in self.labels)


@dataclass(frozen=True)
class Always:
    def matches(self, frame: Token) -> bool:  # noqa: ARG002
        return True


@dataclass(frozen=True)
class Transition:
    target: StateId
    condition: Condition
    weight: float = 1.0
    emissions: tuple[Emission, ...] = ()

    def matches(self, frame: Token) -> bool:
        return self.condition.matches(frame)


@dataclass
class FSM:
    name: str
    start: StateId
    transitions: dict[StateId, list[Transition]] = field(default_factory=dict)
    accept: frozenset[StateId] = field(default_factory=frozenset)

    def transitions_from(self, state: StateId) -> Sequence[Transition]:
        return self.transitions.get(state, ())

    def is_accept(self, state: StateId) -> bool:
        return state in self.accept

    def states(self) -> set[StateId]:
        seen: set[StateId] = {self.start}
        seen.update(self.accept)
        for src, trs in self.transitions.items():
            seen.add(src)
            for tr in trs:
                seen.add(tr.target)
        return seen


class FSMBuilder:
    """Ergonomic builder for hand-constructing FSMs."""

    def __init__(self, name: str):
        self.name = name
        self._counter = 0
        self._start: StateId | None = None
        self._accept: set[StateId] = set()
        self._transitions: dict[StateId, list[Transition]] = {}

    def state(self, name: str | None = None) -> StateId:
        s = StateId(self._counter, name)
        self._counter += 1
        return s

    def start(self, state: StateId) -> "FSMBuilder":
        self._start = state
        return self

    def accept(self, *states: StateId) -> "FSMBuilder":
        self._accept.update(states)
        return self

    def transition(
        self,
        src: StateId,
        condition: Condition,
        target: StateId,
        *,
        weight: float = 1.0,
        emissions: Iterable[Emission] = (),
    ) -> "FSMBuilder":
        tr = Transition(
            target=target,
            condition=condition,
            weight=weight,
            emissions=tuple(emissions),
        )
        self._transitions.setdefault(src, []).append(tr)
        return self

    def build(self) -> FSM:
        if self._start is None:
            raise ValueError(f"FSM {self.name!r} has no start state")
        if not self._accept:
            raise ValueError(f"FSM {self.name!r} has no accept states")
        return FSM(
            name=self.name,
            start=self._start,
            transitions=self._transitions,
            accept=frozenset(self._accept),
        )


def compile_linear(
    name: str,
    conditions: Sequence[Condition],
    emissions: Sequence[Emission],
) -> FSM:
    """Compile a flat condition sequence into a linear FSM.

    Each condition consumes one token. Emissions are attached to the final
    transition (so they only fire when every condition matches).
    """
    if not conditions:
        raise ValueError("compile_linear requires at least one condition")
    builder = FSMBuilder(name)
    states = [builder.state(f"q{i}") for i in range(len(conditions) + 1)]
    builder.start(states[0])
    builder.accept(states[-1])
    for i, cond in enumerate(conditions):
        ems = tuple(emissions) if i == len(conditions) - 1 else ()
        builder.transition(states[i], cond, states[i + 1], emissions=ems)
    return builder.build()


# --- Scanner -----------------------------------------------------------------

CombineFn = Callable[[float, float], float]


@dataclass
class _Path:
    state: StateId
    weight: float
    pending: tuple[tuple[int, Emission], ...]  # (anchor_token_index, emission)


@dataclass
class FSMScanner:
    """Run an FSM at every starting position and emit deltas on accept."""

    combine: CombineFn = operator.mul

    def scan(self, fsm: FSM, state: ParserState) -> list[LabelDelta]:
        deltas: list[LabelDelta] = []
        n = len(state.tokens)
        for start in range(n):
            deltas.extend(self._scan_from(fsm, state.tokens, start))
        return deltas

    def _scan_from(
        self,
        fsm: FSM,
        tokens: list[Token],
        start: int,
    ) -> list[LabelDelta]:
        n = len(tokens)
        deltas: list[LabelDelta] = []
        active: list[_Path] = [_Path(fsm.start, 1.0, ())]

        # accept at start before consuming any token
        for path in active:
            if fsm.is_accept(path.state):
                deltas.extend(self._emit(path, fsm.name, n))

        pos = start
        while active and pos < n:
            frame = tokens[pos]
            next_active: list[_Path] = []
            for path in active:
                for tr in fsm.transitions_from(path.state):
                    if not tr.matches(frame):
                        continue
                    new_pending = path.pending + tuple(
                        (pos, em) for em in tr.emissions
                    )
                    new_weight = self.combine(path.weight, tr.weight)
                    next_active.append(_Path(tr.target, new_weight, new_pending))
            active = next_active
            pos += 1
            for path in active:
                if fsm.is_accept(path.state):
                    deltas.extend(self._emit(path, fsm.name, n))
        return deltas

    def _emit(self, path: _Path, source: str, n: int) -> list[LabelDelta]:
        out: list[LabelDelta] = []
        for anchor, em in path.pending:
            target = anchor + em.offset
            if 0 <= target < n:
                out.append(
                    LabelDelta(
                        token_index=target,
                        label=em.label,
                        weight=self.combine(path.weight, em.weight),
                        source=source,
                    )
                )
        return out

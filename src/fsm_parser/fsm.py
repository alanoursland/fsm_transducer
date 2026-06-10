"""Weighted finite-state machine core (v2).

Adds, over the original implementation:

* explicit epsilon transitions
* captures (per-path register file) and capture-anchored emissions
* template-string label interpolation (``"SUBJECT_OF:{verb}"``)
* composable conditions (``Not``, ``And``, ``Or``) plus positional and
  weight-threshold guards
* state-level emissions (``on_enter``, ``on_accept``)
* semiring-based weight algebra with NFA-style path merging by
  ``(state, captures, pending)``

The original public surface (``HasLabel``, ``HasAnyLabel``, ``Always``,
``compile_linear``, ``FSMBuilder``, ``FSMScanner``, ``Emission`` with the
``offset=`` keyword) is preserved.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Protocol, Sequence

from fsm_parser.labels import LabelDelta
from fsm_parser.semirings import LegacyMul, ProductReal, Semiring
from fsm_parser.slots import Slot, SlotId
from fsm_parser.tokens import ParserState, Token

# --- States, captures, emissions, anchors -----------------------------------


@dataclass(frozen=True)
class StateId:
    value: int
    name: str | None = None

    def __repr__(self) -> str:
        if self.name:
            return f"State({self.value}:{self.name})"
        return f"State({self.value})"


@dataclass(frozen=True)
class CaptureValue:
    """A captured value plus the position and slot id it came from.

    ``value`` is what gets interpolated into emission label templates;
    its meaning depends on ``kind``. ``pos`` and ``slot_id`` record where
    the capture happened so emission anchors can resolve relative
    offsets and exact targets independently of how the user wants the
    template to render.
    """

    kind: str
    value: Any  # int for "index", str for "slot_id"/"top_label", SourceSpan, ...
    pos: int | None = None
    slot_id: SlotId | None = None


@dataclass(frozen=True)
class Capture:
    """Bind a name to information about the slot a transition consumes.

    ``mode="overwrite"`` (default) replaces the register on every firing;
    ``mode="first"`` sets it only if absent, so loops keep the earliest
    value (used for group-start tagging).
    """

    name: str
    kind: str = "index"  # "index" | "slot_id" | "top_label" | "source_span"
    mode: str = "overwrite"  # "overwrite" | "first"


@dataclass
class ScanContext:
    """View of the current scan state passed to conditions and anchors."""

    scan_start: int
    n: int
    pos: int | None = None
    last_consumed: int | None = None
    captures: dict[str, CaptureValue] = field(default_factory=dict)


# Emission anchors -----------------------------------------------------------


class EmissionAnchor(Protocol):
    def resolve(
        self,
        captures: dict[str, CaptureValue],
        firing_pos: int | None,
        scan_start: int,
        slots: "Sequence[Slot]",
    ) -> SlotId | None: ...


def _slot_id_at(slots: "Sequence[Slot]", pos: int) -> SlotId | None:
    if 0 <= pos < len(slots):
        return slots[pos].id
    return None


@dataclass(frozen=True)
class FiringOffset:
    offset: int = 0

    def resolve(self, captures, firing_pos, scan_start, slots):  # noqa: ARG002
        if firing_pos is None:
            return None
        return _slot_id_at(slots, firing_pos + self.offset)


@dataclass(frozen=True)
class CaptureAnchor:
    name: str
    offset: int = 0

    def resolve(self, captures, firing_pos, scan_start, slots):  # noqa: ARG002
        cap = captures.get(self.name)
        if cap is None:
            return None
        # offset 0 with a known slot id: use it directly (stable target).
        if self.offset == 0 and cap.slot_id is not None:
            return cap.slot_id
        if cap.pos is None:
            return None
        return _slot_id_at(slots, cap.pos + self.offset)


@dataclass(frozen=True)
class ScanStart:
    offset: int = 0

    def resolve(self, captures, firing_pos, scan_start, slots):  # noqa: ARG002
        return _slot_id_at(slots, scan_start + self.offset)


@dataclass(frozen=True)
class ScanEnd:
    """Anchor at the most recently consumed slot in the scan."""

    offset: int = 0

    def resolve(self, captures, firing_pos, scan_start, slots):  # noqa: ARG002
        if firing_pos is None:
            return None
        return _slot_id_at(slots, firing_pos + self.offset)


_DEFAULT_ANCHOR = FiringOffset(0)


@dataclass(frozen=True, init=False)
class Emission:
    label: str
    weight: float
    anchor: EmissionAnchor

    def __init__(
        self,
        label: str,
        weight: float,
        anchor: EmissionAnchor | None = None,
        *,
        offset: int | None = None,
    ) -> None:
        if anchor is not None and offset is not None:
            raise ValueError("specify either anchor or offset, not both")
        if anchor is None:
            anchor = FiringOffset(offset) if offset is not None else _DEFAULT_ANCHOR
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "weight", weight)
        object.__setattr__(self, "anchor", anchor)


@dataclass(frozen=True)
class StateInfo:
    on_enter: tuple[Emission, ...] = ()
    on_accept: tuple[Emission, ...] = ()


# --- Conditions -------------------------------------------------------------


class Condition(Protocol):
    def matches(self, frame: Token, ctx: "ScanContext | None" = None) -> bool: ...


@dataclass(frozen=True)
class Always:
    def matches(self, frame: Token, ctx: ScanContext | None = None) -> bool:  # noqa: ARG002
        return True


@dataclass(frozen=True)
class Never:
    def matches(self, frame: Token, ctx: ScanContext | None = None) -> bool:  # noqa: ARG002
        return False


@dataclass(frozen=True)
class HasLabel:
    label: str
    min_weight: float = 0.0

    def matches(self, frame: Token, ctx: ScanContext | None = None) -> bool:  # noqa: ARG002
        return frame.labels.get(self.label) > self.min_weight


@dataclass(frozen=True)
class HasAnyLabel:
    labels: tuple[str, ...]
    min_weight: float = 0.0

    def matches(self, frame: Token, ctx: ScanContext | None = None) -> bool:  # noqa: ARG002
        return any(frame.labels.get(l) > self.min_weight for l in self.labels)


@dataclass(frozen=True)
class HasAllLabels:
    labels: tuple[str, ...]
    min_weight: float = 0.0

    def matches(self, frame: Token, ctx: ScanContext | None = None) -> bool:  # noqa: ARG002
        return all(frame.labels.get(l) > self.min_weight for l in self.labels)


@dataclass(frozen=True)
class WeightAbove:
    label: str
    threshold: float

    def matches(self, frame: Token, ctx: ScanContext | None = None) -> bool:  # noqa: ARG002
        return frame.labels.get(self.label) > self.threshold


@dataclass(frozen=True)
class WeightBelow:
    label: str
    threshold: float

    def matches(self, frame: Token, ctx: ScanContext | None = None) -> bool:  # noqa: ARG002
        return frame.labels.get(self.label) < self.threshold


@dataclass(frozen=True)
class Not:
    inner: Condition

    def matches(self, frame: Token, ctx: ScanContext | None = None) -> bool:
        return not self.inner.matches(frame, ctx)


@dataclass(frozen=True)
class And:
    parts: tuple[Condition, ...]

    def matches(self, frame: Token, ctx: ScanContext | None = None) -> bool:
        return all(p.matches(frame, ctx) for p in self.parts)


@dataclass(frozen=True)
class Or:
    parts: tuple[Condition, ...]

    def matches(self, frame: Token, ctx: ScanContext | None = None) -> bool:
        return any(p.matches(frame, ctx) for p in self.parts)


@dataclass(frozen=True)
class AtSentenceStart:
    """True only at the first token of the input."""

    def matches(self, frame: Token, ctx: ScanContext | None = None) -> bool:  # noqa: ARG002
        if ctx is None:
            return False
        return ctx.pos == 0


@dataclass(frozen=True)
class AtSentenceEnd:
    """True only at the last token of the input."""

    def matches(self, frame: Token, ctx: ScanContext | None = None) -> bool:  # noqa: ARG002
        if ctx is None:
            return False
        return ctx.pos is not None and ctx.pos == ctx.n - 1


@dataclass(frozen=True)
class LabelPredicate:
    """Match if any label in the bag satisfies a string predicate."""

    predicate: Callable[[str], bool]
    min_weight: float = 0.0

    def matches(self, frame: Token, ctx: ScanContext | None = None) -> bool:  # noqa: ARG002
        return any(
            self.predicate(label) and weight > self.min_weight
            for label, weight in frame.labels.items()
        )


# --- Transitions and FSMs ---------------------------------------------------


@dataclass(frozen=True)
class Transition:
    target: StateId
    condition: Condition
    weight: float = 1.0
    emissions: tuple[Emission, ...] = ()
    captures: tuple[Capture, ...] = ()
    epsilon: bool = False
    priority: int = 0

    def matches(self, frame: Token, ctx: ScanContext | None = None) -> bool:
        return self.condition.matches(frame, ctx)


@dataclass
class FSM:
    name: str
    start: StateId
    transitions: dict[StateId, list[Transition]] = field(default_factory=dict)
    accept: frozenset[StateId] = field(default_factory=frozenset)
    state_info: dict[StateId, StateInfo] = field(default_factory=dict)

    def transitions_from(self, state: StateId) -> Sequence[Transition]:
        return self.transitions.get(state, ())

    def is_accept(self, state: StateId) -> bool:
        return state in self.accept

    def states(self) -> set[StateId]:
        seen: set[StateId] = {self.start}
        seen.update(self.accept)
        seen.update(self.state_info.keys())
        for src, trs in self.transitions.items():
            seen.add(src)
            for tr in trs:
                seen.add(tr.target)
        return seen


class FSMBuilder:
    """Low-level builder for hand-constructing FSMs.

    Used internally by the combinator layer and available for direct use
    when the combinators do not fit.
    """

    def __init__(self, name: str):
        self.name = name
        self._counter = 0
        self._start: StateId | None = None
        self._accept: set[StateId] = set()
        self._transitions: dict[StateId, list[Transition]] = {}
        self._state_info: dict[StateId, StateInfo] = {}

    def state(self, name: str | None = None) -> StateId:
        s = StateId(self._counter, name)
        self._counter += 1
        return s

    def fresh(self, count: int, prefix: str = "q") -> list[StateId]:
        return [self.state(f"{prefix}{i}") for i in range(count)]

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
        captures: Iterable[Capture] = (),
        priority: int = 0,
    ) -> "FSMBuilder":
        tr = Transition(
            target=target,
            condition=condition,
            weight=weight,
            emissions=tuple(emissions),
            captures=tuple(captures),
            epsilon=False,
            priority=priority,
        )
        self._transitions.setdefault(src, []).append(tr)
        return self

    def epsilon(
        self,
        src: StateId,
        target: StateId,
        *,
        weight: float = 1.0,
        emissions: Iterable[Emission] = (),
        priority: int = 0,
    ) -> "FSMBuilder":
        tr = Transition(
            target=target,
            condition=Always(),
            weight=weight,
            emissions=tuple(emissions),
            captures=(),
            epsilon=True,
            priority=priority,
        )
        self._transitions.setdefault(src, []).append(tr)
        return self

    def state_info(
        self,
        state: StateId,
        *,
        on_enter: Iterable[Emission] = (),
        on_accept: Iterable[Emission] = (),
    ) -> "FSMBuilder":
        existing = self._state_info.get(state, StateInfo())
        self._state_info[state] = StateInfo(
            on_enter=tuple(existing.on_enter) + tuple(on_enter),
            on_accept=tuple(existing.on_accept) + tuple(on_accept),
        )
        return self

    def build(self) -> FSM:
        if self._start is None:
            raise ValueError(f"FSM {self.name!r} has no start state")
        if not self._accept:
            raise ValueError(f"FSM {self.name!r} has no accept states")
        return FSM(
            name=self.name,
            start=self._start,
            transitions=dict(self._transitions),
            accept=frozenset(self._accept),
            state_info=dict(self._state_info),
        )


def compile_linear(
    name: str,
    conditions: Sequence[Condition],
    emissions: Sequence[Emission],
) -> FSM:
    """Compile a flat condition sequence into a linear FSM (compat helper)."""
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


# --- Path state and template interpolation ----------------------------------


_TEMPLATE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _interpolate(label: str, captures: dict[str, CaptureValue]) -> str:
    if "{" not in label:
        return label

    def repl(m: re.Match) -> str:
        name = m.group(1)
        cap = captures.get(name)
        if cap is None:
            return m.group(0)  # leave placeholder as-is if unknown
        return str(cap.value)

    return _TEMPLATE.sub(repl, label)


@dataclass
class _Path:
    state: StateId
    weight: float
    captures: dict[str, CaptureValue]
    last_consumed: int | None = None
    scan_start: int = 0

    def captures_sig(self) -> tuple[tuple[str, CaptureValue], ...]:
        return tuple(sorted(self.captures.items()))

    def merge_key(self) -> tuple:
        return (self.scan_start, self.state, self.captures_sig())


def _capture_from_slot(cap: Capture, slot: Slot, pos: int) -> CaptureValue:
    if cap.kind == "index":
        # Legacy: value is the position in the scanned stream.
        return CaptureValue("index", pos, pos=pos, slot_id=slot.id)
    if cap.kind == "slot_id":
        return CaptureValue("slot_id", slot.id, pos=pos, slot_id=slot.id)
    if cap.kind == "top_label":
        top = slot.labels.top_k(1)
        value = top[0][0] if top else ""
        return CaptureValue("top_label", value, pos=pos, slot_id=slot.id)
    if cap.kind == "source_span":
        return CaptureValue("source_span", slot.source_span, pos=pos, slot_id=slot.id)
    raise ValueError(f"unsupported capture kind: {cap.kind!r}")


# --- Scanner ----------------------------------------------------------------


@dataclass
class FSMScanner:
    """Run an FSM at every starting position with epsilon closure and merging.

    Emissions fire eagerly: transition emissions when the transition is
    taken, state ``on_enter`` / ``on_accept`` emissions when a path
    arrives at the state during epsilon closure. Either ``semiring`` or
    the legacy ``combine`` callable may be supplied.
    """

    semiring: Semiring = field(default_factory=ProductReal)
    combine: Callable[[float, float], float] | None = None

    def __post_init__(self) -> None:
        if self.combine is not None:
            shim = LegacyMul()
            user_combine = self.combine

            class _CallableShim:
                one = 1.0
                zero = 0.0

                def times(self_inner, a, b):  # noqa: ARG002, N805
                    return user_combine(a, b)

                def plus(self_inner, a, b):  # noqa: ARG002, N805
                    return shim.plus(a, b)

            self.semiring = _CallableShim()  # type: ignore[assignment]

    def scan(
        self,
        fsm: FSM,
        state: ParserState,
        *,
        stream: str = "token",
        slot_filter: Callable[[Slot], bool] | None = None,
    ) -> list[LabelDelta]:
        deltas: list[LabelDelta] = []
        slots = state.stream(stream)
        if slot_filter is not None:
            slots = [s for s in slots if slot_filter(s)]
        n = len(slots)
        for start in range(n):
            self._scan_from(fsm, slots, start, n, deltas)
        return deltas

    def transduce(
        self,
        fsm: FSM,
        state: ParserState,
        *,
        stream: str = "token",
        slot_filter: Callable[[Slot], bool] | None = None,
    ) -> list[LabelDelta]:
        """Single left-to-right pass covering all start offsets.

        Equivalent to ``scan()`` up to delta ordering: at each position a
        fresh start-state path is injected into the live frontier, so every
        start offset is still explored, but the input is traversed once and
        dead paths are dropped as soon as they fail.

        Bound: paths merge on ``(scan_start, state, captures)``, so the
        frontier after position ``i`` holds at most
        ``(i + 1) * |Q| * |capture signatures|`` paths; for capture-free
        machines whose live paths die within ``k`` positions (every acyclic
        machine; any machine whose conditions eventually reject), the
        frontier is ``O(k * |Q|)`` — independent of input length.
        """
        deltas: list[LabelDelta] = []
        slots = state.stream(stream)
        if slot_filter is not None:
            slots = [s for s in slots if slot_filter(s)]
        n = len(slots)
        frontier: list[_Path] = []
        for pos in range(n):
            initial = _Path(
                state=fsm.start,
                weight=self.semiring.one,
                captures={},
                last_consumed=None,
                scan_start=pos,
            )
            frontier = frontier + self._epsilon_close(
                [initial], fsm, deltas, slots=slots
            )
            frame = slots[pos]
            successors: list[_Path] = []
            for path in frontier:
                ctx = ScanContext(
                    scan_start=path.scan_start,
                    n=n,
                    pos=pos,
                    last_consumed=path.last_consumed,
                    captures=path.captures,
                )
                for tr in fsm.transitions_from(path.state):
                    if tr.epsilon:
                        continue
                    if not tr.matches(frame, ctx):
                        continue
                    new_captures = dict(path.captures)
                    for cap in tr.captures:
                        if cap.mode == "first" and cap.name in new_captures:
                            continue
                        new_captures[cap.name] = _capture_from_slot(cap, frame, pos)
                    new_weight = self.semiring.times(path.weight, tr.weight)
                    for em in tr.emissions:
                        self._fire(
                            em,
                            new_captures,
                            firing_pos=pos,
                            path_weight=new_weight,
                            scan_start=path.scan_start,
                            slots=slots,
                            source=fsm.name,
                            deltas=deltas,
                        )
                    successors.append(
                        _Path(
                            state=tr.target,
                            weight=new_weight,
                            captures=new_captures,
                            last_consumed=pos,
                            scan_start=path.scan_start,
                        )
                    )
            successors = self._merge(successors)
            frontier = self._epsilon_close(successors, fsm, deltas, slots=slots)
        return deltas

    # -- internals -----------------------------------------------------------

    def _fire(
        self,
        em: Emission,
        captures: dict[str, CaptureValue],
        *,
        firing_pos: int | None,
        path_weight: float,
        scan_start: int,
        slots: "Sequence[Slot]",
        source: str,
        deltas: list[LabelDelta],
    ) -> None:
        target_id = em.anchor.resolve(captures, firing_pos, scan_start, slots)
        if target_id is None:
            return
        label = _interpolate(em.label, captures)
        deltas.append(
            LabelDelta(
                slot_id=target_id,
                label=label,
                weight=self.semiring.times(path_weight, em.weight),
                source=source,
            )
        )

    def _scan_from(
        self,
        fsm: FSM,
        slots: "Sequence[Slot]",
        start: int,
        n: int,
        deltas: list[LabelDelta],
    ) -> None:
        ctx = ScanContext(scan_start=start, n=n, pos=start)
        initial = _Path(
            state=fsm.start,
            weight=self.semiring.one,
            captures={},
            last_consumed=None,
            scan_start=start,
        )
        frontier = self._epsilon_close([initial], fsm, deltas, slots=slots)

        for pos in range(start, n):
            ctx.pos = pos
            frame = slots[pos]
            successors: list[_Path] = []
            for path in frontier:
                ctx.captures = path.captures
                for tr in fsm.transitions_from(path.state):
                    if tr.epsilon:
                        continue
                    if not tr.matches(frame, ctx):
                        continue
                    new_captures = dict(path.captures)
                    for cap in tr.captures:
                        if cap.mode == "first" and cap.name in new_captures:
                            continue
                        new_captures[cap.name] = _capture_from_slot(cap, frame, pos)
                    new_weight = self.semiring.times(path.weight, tr.weight)
                    for em in tr.emissions:
                        self._fire(
                            em,
                            new_captures,
                            firing_pos=pos,
                            path_weight=new_weight,
                            scan_start=start,
                            slots=slots,
                            source=fsm.name,
                            deltas=deltas,
                        )
                    successors.append(
                        _Path(
                            state=tr.target,
                            weight=new_weight,
                            captures=new_captures,
                            last_consumed=pos,
                            scan_start=start,
                        )
                    )
            successors = self._merge(successors)
            frontier = self._epsilon_close(successors, fsm, deltas, slots=slots)
            if not frontier:
                break

    def _epsilon_close(
        self,
        paths: list[_Path],
        fsm: FSM,
        deltas: list[LabelDelta],
        *,
        slots: "Sequence[Slot]",
    ) -> list[_Path]:
        seen: set[tuple] = set()
        result: list[_Path] = []
        worklist = list(paths)
        while worklist:
            path = worklist.pop(0)
            key = path.merge_key()
            if key in seen:
                continue
            seen.add(key)
            info = fsm.state_info.get(path.state)
            if info is not None:
                for em in info.on_enter:
                    self._fire(
                        em,
                        path.captures,
                        firing_pos=path.last_consumed,
                        path_weight=path.weight,
                        scan_start=path.scan_start,
                        slots=slots,
                        source=fsm.name,
                        deltas=deltas,
                    )
                if fsm.is_accept(path.state):
                    for em in info.on_accept:
                        self._fire(
                            em,
                            path.captures,
                            firing_pos=path.last_consumed,
                            path_weight=path.weight,
                            scan_start=path.scan_start,
                            slots=slots,
                            source=fsm.name,
                            deltas=deltas,
                        )
            result.append(path)
            for tr in fsm.transitions_from(path.state):
                if not tr.epsilon:
                    continue
                new_weight = self.semiring.times(path.weight, tr.weight)
                for em in tr.emissions:
                    self._fire(
                        em,
                        path.captures,
                        firing_pos=path.last_consumed,
                        path_weight=new_weight,
                        scan_start=path.scan_start,
                        slots=slots,
                        source=fsm.name,
                        deltas=deltas,
                    )
                worklist.append(
                    _Path(
                        state=tr.target,
                        weight=new_weight,
                        captures=dict(path.captures),
                        last_consumed=path.last_consumed,
                        scan_start=path.scan_start,
                    )
                )
        return self._merge(result)

    def _merge(self, paths: list[_Path]) -> list[_Path]:
        if not paths:
            return paths
        by_key: dict[tuple, _Path] = {}
        for p in paths:
            key = p.merge_key()
            if key in by_key:
                existing = by_key[key]
                by_key[key] = _Path(
                    state=p.state,
                    weight=self.semiring.plus(existing.weight, p.weight),
                    captures=p.captures,
                    last_consumed=p.last_consumed,
                )
            else:
                by_key[key] = p
        return list(by_key.values())

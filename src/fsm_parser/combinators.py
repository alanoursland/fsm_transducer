"""Thompson-style combinators for building FSMs compositionally.

Each combinator returns a fresh FSM with a single start state and a
single accept state, joined to its arguments by epsilon transitions.
The result still satisfies the ``FSM`` protocol the scanner consumes.
"""

from __future__ import annotations

from typing import Iterable

from fsm_parser.fsm import (
    FSM,
    Capture,
    Condition,
    Emission,
    FSMBuilder,
    StateId,
    Transition,
)


def _embed(builder: FSMBuilder, machine: FSM) -> tuple[StateId, frozenset[StateId]]:
    """Copy machine's states and transitions into builder, returning the
    new start state and accept state set."""
    mapping: dict[StateId, StateId] = {}
    for s in machine.states():
        mapping[s] = builder.state(s.name)
    for src, trs in machine.transitions.items():
        new_src = mapping[src]
        bucket = builder._transitions.setdefault(new_src, [])
        for tr in trs:
            bucket.append(
                Transition(
                    target=mapping[tr.target],
                    condition=tr.condition,
                    weight=tr.weight,
                    emissions=tr.emissions,
                    captures=tr.captures,
                    epsilon=tr.epsilon,
                    priority=tr.priority,
                )
            )
    for s, info in machine.state_info.items():
        builder._state_info[mapping[s]] = info
    return mapping[machine.start], frozenset(mapping[s] for s in machine.accept)


def literal(
    condition: Condition,
    *,
    emissions: Iterable[Emission] = (),
    captures: Iterable[Capture] = (),
    weight: float = 1.0,
    name: str | None = None,
) -> FSM:
    """A two-state FSM that consumes one token matching ``condition``."""
    b = FSMBuilder(name or "literal")
    s0 = b.state("q0")
    s1 = b.state("q1")
    b.start(s0).accept(s1)
    b.transition(
        s0,
        condition,
        s1,
        weight=weight,
        emissions=emissions,
        captures=captures,
    )
    return b.build()


def epsilon(*, emissions: Iterable[Emission] = (), name: str | None = None) -> FSM:
    """A two-state FSM joined only by an epsilon transition."""
    b = FSMBuilder(name or "epsilon")
    s0 = b.state("q0")
    s1 = b.state("q1")
    b.start(s0).accept(s1)
    b.epsilon(s0, s1, emissions=emissions)
    return b.build()


def concat(*machines: FSM, name: str | None = None) -> FSM:
    if not machines:
        return epsilon(name=name)
    b = FSMBuilder(name or "concat")
    new_start = b.state("start")
    new_accept = b.state("accept")
    b.start(new_start).accept(new_accept)
    prev_exits: list[StateId] = [new_start]
    for i, m in enumerate(machines):
        sub_start, sub_accepts = _embed(b, m)
        for exit_state in prev_exits:
            b.epsilon(exit_state, sub_start)
        if i == len(machines) - 1:
            for a in sub_accepts:
                b.epsilon(a, new_accept)
        else:
            prev_exits = list(sub_accepts)
    return b.build()


def alt(*machines: FSM, name: str | None = None) -> FSM:
    if not machines:
        return epsilon(name=name)
    if len(machines) == 1:
        return _rebuild(machines[0], name=name or machines[0].name)
    b = FSMBuilder(name or "alt")
    new_start = b.state("start")
    new_accept = b.state("accept")
    b.start(new_start).accept(new_accept)
    for m in machines:
        sub_start, sub_accepts = _embed(b, m)
        b.epsilon(new_start, sub_start)
        for a in sub_accepts:
            b.epsilon(a, new_accept)
    return b.build()


def star(machine: FSM, *, name: str | None = None) -> FSM:
    b = FSMBuilder(name or "star")
    new_start = b.state("start")
    new_accept = b.state("accept")
    b.start(new_start).accept(new_accept)
    sub_start, sub_accepts = _embed(b, machine)
    b.epsilon(new_start, new_accept)  # zero matches
    b.epsilon(new_start, sub_start)
    for a in sub_accepts:
        b.epsilon(a, new_accept)
        b.epsilon(a, sub_start)  # loop
    return b.build()


def plus(machine: FSM, *, name: str | None = None) -> FSM:
    return concat(_rebuild(machine), star(_rebuild(machine)), name=name or "plus")


def optional(machine: FSM, *, name: str | None = None) -> FSM:
    return alt(epsilon(), _rebuild(machine), name=name or "optional")


def repeat(
    machine: FSM, min_n: int, max_n: int | None, *, name: str | None = None
) -> FSM:
    if min_n < 0:
        raise ValueError("min_n must be non-negative")
    if max_n is not None and max_n < min_n:
        raise ValueError("max_n must be >= min_n")
    parts: list[FSM] = [_rebuild(machine) for _ in range(min_n)]
    if max_n is None:
        parts.append(star(_rebuild(machine)))
    else:
        for _ in range(max_n - min_n):
            parts.append(optional(_rebuild(machine)))
    return concat(*parts, name=name or "repeat")


def call(machine: FSM, *, name: str | None = None) -> FSM:
    """Wrap a machine with fresh start/accept states (subroutine-like).

    Behaviorally identical to running the inner machine, but creates a
    new state envelope so callers can attach state info or compose
    further without polluting the inner state space.
    """
    b = FSMBuilder(name or f"call({machine.name})")
    new_start = b.state("start")
    new_accept = b.state("accept")
    b.start(new_start).accept(new_accept)
    sub_start, sub_accepts = _embed(b, machine)
    b.epsilon(new_start, sub_start)
    for a in sub_accepts:
        b.epsilon(a, new_accept)
    return b.build()


def _rebuild(machine: FSM, *, name: str | None = None) -> FSM:
    """Clone a machine with fresh state IDs to keep state ownership clean."""
    b = FSMBuilder(name or machine.name)
    sub_start, sub_accepts = _embed(b, machine)
    b._start = sub_start
    b._accept = set(sub_accepts)
    return b.build()

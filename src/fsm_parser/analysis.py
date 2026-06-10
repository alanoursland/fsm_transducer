"""Bounds, acceptance, determinization, and minimization for FSMs.

This is the "provable bounds" toolkit:

* :func:`accepts` — plain NFA acceptance over a slot sequence.
* :func:`determinize` — subset construction for plain machines (no
  captures, no emissions), over a *minterm* alphabet: since transition
  conditions are predicates that may overlap, the deterministic alphabet
  is the set of boolean combinations (minterms) of the distinct
  conditions appearing in the machine. Exponential in the number of
  distinct conditions, so guarded by ``max_conditions``.
* :func:`minimize` — partition-refinement (Moore) minimization of a
  determinized machine. Ported in spirit from the ``regex_transformer``
  project's ``_minimize_dfa``.
* :func:`analyze` — a complexity certificate for any machine: state and
  transition counts, capture/emission inventory, whether the machine is
  determinizable, and the scanner frontier bound with its argument.
"""

from __future__ import annotations

from dataclasses import dataclass

from fsm_parser.fsm import (
    FSM,
    And,
    Condition,
    FSMBuilder,
    Not,
    ScanContext,
    StateId,
    Transition,
)
from fsm_parser.slots import Slot

# --- Acceptance --------------------------------------------------------------


def _epsilon_close_states(fsm: FSM, states: frozenset[StateId]) -> frozenset[StateId]:
    seen = set(states)
    work = list(states)
    while work:
        s = work.pop()
        for tr in fsm.transitions_from(s):
            if tr.epsilon and tr.target not in seen:
                seen.add(tr.target)
                work.append(tr.target)
    return frozenset(seen)


def accepts(fsm: FSM, slots: list[Slot]) -> bool:
    """True iff the machine accepts the *whole* slot sequence from its start.

    Weight- and emission-free NFA simulation; used by oracle tests to
    compare against Python ``re`` and by :func:`determinize` validation.
    """
    n = len(slots)
    current = _epsilon_close_states(fsm, frozenset([fsm.start]))
    for pos, frame in enumerate(slots):
        ctx = ScanContext(scan_start=0, n=n, pos=pos)
        nxt: set[StateId] = set()
        for s in current:
            for tr in fsm.transitions_from(s):
                if not tr.epsilon and tr.matches(frame, ctx):
                    nxt.add(tr.target)
        current = _epsilon_close_states(fsm, frozenset(nxt))
        if not current:
            return False
    return any(fsm.is_accept(s) for s in current)


# --- Plainness check ---------------------------------------------------------


def _consuming_transitions(fsm: FSM) -> list[tuple[StateId, Transition]]:
    out = []
    for src, trs in fsm.transitions.items():
        for tr in trs:
            if not tr.epsilon:
                out.append((src, tr))
    return out


def is_plain(fsm: FSM) -> bool:
    """No captures, no emissions, unit weights: a pure acceptor."""
    for _, tr in _consuming_transitions(fsm):
        if tr.captures or tr.emissions or tr.weight != 1.0:
            return False
    for src, trs in fsm.transitions.items():
        for tr in trs:
            if tr.epsilon and (tr.emissions or tr.weight != 1.0):
                return False
    return not any(
        info.on_enter or info.on_accept for info in fsm.state_info.values()
    )


# --- Determinization ---------------------------------------------------------


@dataclass(frozen=True)
class _Minterm:
    """A sign assignment over the machine's distinct conditions.

    ``positives[i]`` says whether condition ``i`` is asserted. The
    corresponding predicate is the conjunction of each condition or its
    negation; minterms partition the input space, which is what makes
    subset construction sound for overlapping predicates.
    """

    signs: tuple[bool, ...]

    def condition(self, conditions: tuple[Condition, ...]) -> Condition:
        parts = tuple(
            c if sign else Not(c) for c, sign in zip(conditions, self.signs)
        )
        return parts[0] if len(parts) == 1 else And(parts)


def determinize(fsm: FSM, *, max_conditions: int = 10) -> FSM:
    """Subset construction for a plain machine, over minterm symbols.

    Raises ``ValueError`` if the machine has captures, emissions,
    non-unit weights, or more than ``max_conditions`` distinct
    conditions (the minterm alphabet is ``2**k``).
    """
    if not is_plain(fsm):
        raise ValueError(
            f"FSM {fsm.name!r} is not a plain acceptor "
            "(captures/emissions/weights present); determinization would "
            "not preserve transduction semantics"
        )
    conditions: list[Condition] = []
    for _, tr in _consuming_transitions(fsm):
        if tr.condition not in conditions:
            conditions.append(tr.condition)
    k = len(conditions)
    if k > max_conditions:
        raise ValueError(
            f"FSM {fsm.name!r} has {k} distinct conditions; "
            f"minterm alphabet 2**{k} exceeds max_conditions={max_conditions}"
        )
    cond_tuple = tuple(conditions)
    minterms = [
        _Minterm(tuple((i >> b) & 1 == 1 for b in range(k)))
        for i in range(2**k)
    ]

    b = FSMBuilder(f"det({fsm.name})")
    start_set = _epsilon_close_states(fsm, frozenset([fsm.start]))
    dfa_states: dict[frozenset[StateId], StateId] = {}

    def get_state(nfa_set: frozenset[StateId]) -> StateId:
        if nfa_set not in dfa_states:
            dfa_states[nfa_set] = b.state()
        return dfa_states[nfa_set]

    work = [start_set]
    seen = {start_set}
    accepts_sets = []
    while work:
        cur = work.pop()
        src = get_state(cur)
        if any(fsm.is_accept(s) for s in cur):
            accepts_sets.append(src)
        for mt in minterms:
            # A slot matching this minterm satisfies exactly the positive
            # conditions, so it triggers exactly those transitions.
            targets: set[StateId] = set()
            for s in cur:
                for tr in fsm.transitions_from(s):
                    if tr.epsilon:
                        continue
                    idx = conditions.index(tr.condition)
                    if mt.signs[idx]:
                        targets.add(tr.target)
            if not targets:
                continue
            closed = _epsilon_close_states(fsm, frozenset(targets))
            b.transition(src, mt.condition(cond_tuple), get_state(closed))
            if closed not in seen:
                seen.add(closed)
                work.append(closed)

    b.start(get_state(start_set))
    if not accepts_sets:
        # Degenerate machine accepting nothing; keep builder happy with an
        # unreachable accept state.
        accepts_sets.append(b.state("dead_accept"))
    b.accept(*accepts_sets)
    return b.build()


# --- Minimization ------------------------------------------------------------


def minimize(dfa: FSM) -> FSM:
    """Moore partition refinement on a deterministic, epsilon-free machine.

    Two states are merged when they agree on acceptance and, for every
    condition, transition into the same block. Missing transitions are
    treated as a transition to an implicit dead block.
    """
    states = sorted(dfa.states(), key=lambda s: s.value)
    for s in states:
        for tr in dfa.transitions_from(s):
            if tr.epsilon:
                raise ValueError("minimize requires an epsilon-free machine")
    symbols: list[Condition] = []
    for s in states:
        for tr in dfa.transitions_from(s):
            if tr.condition not in symbols:
                symbols.append(tr.condition)

    block: dict[StateId, int] = {
        s: (1 if dfa.is_accept(s) else 0) for s in states
    }
    while True:
        signatures: dict[StateId, tuple] = {}
        for s in states:
            row = []
            for sym in symbols:
                target = None
                for tr in dfa.transitions_from(s):
                    if tr.condition == sym:
                        target = tr.target
                        break
                row.append(-1 if target is None else block[target])
            signatures[s] = (block[s], tuple(row))
        sig_to_block: dict[tuple, int] = {}
        new_block: dict[StateId, int] = {}
        for s in states:
            sig = signatures[s]
            if sig not in sig_to_block:
                sig_to_block[sig] = len(sig_to_block)
            new_block[s] = sig_to_block[sig]
        if new_block == block:
            break
        block = new_block

    b = FSMBuilder(f"min({dfa.name})")
    block_states: dict[int, StateId] = {}
    for s in states:
        block_states.setdefault(block[s], b.state())
    added: set[tuple[int, Condition]] = set()
    accept_blocks = set()
    for s in states:
        if dfa.is_accept(s):
            accept_blocks.add(block[s])
        for tr in dfa.transitions_from(s):
            key = (block[s], tr.condition)
            if key in added:
                continue
            added.add(key)
            b.transition(
                block_states[block[s]], tr.condition, block_states[block[tr.target]]
            )
    b.start(block_states[block[dfa.start]])
    b.accept(*[block_states[blk] for blk in accept_blocks])
    return b.build()


# --- Analysis report ---------------------------------------------------------


@dataclass(frozen=True)
class FSMAnalysis:
    name: str
    n_states: int
    n_consuming: int
    n_epsilon: int
    n_conditions: int
    has_captures: bool
    has_emissions: bool
    plain: bool
    determinizable: bool
    frontier_bound: str

    def report(self) -> str:
        lines = [
            f"FSM {self.name!r}:",
            f"  states:                {self.n_states}",
            f"  consuming transitions: {self.n_consuming}",
            f"  epsilon transitions:   {self.n_epsilon}",
            f"  distinct conditions:   {self.n_conditions}",
            f"  captures:              {'yes' if self.has_captures else 'no'}",
            f"  emissions:             {'yes' if self.has_emissions else 'no'}",
            f"  plain acceptor:        {'yes' if self.plain else 'no'}",
            f"  determinizable:        {'yes' if self.determinizable else 'no'}",
            f"  scanner frontier bound: {self.frontier_bound}",
        ]
        return "\n".join(lines)


def analyze(fsm: FSM, *, max_conditions: int = 10) -> FSMAnalysis:
    states = fsm.states()
    consuming = _consuming_transitions(fsm)
    n_eps = sum(
        1 for trs in fsm.transitions.values() for tr in trs if tr.epsilon
    )
    conditions: list[Condition] = []
    for _, tr in consuming:
        if tr.condition not in conditions:
            conditions.append(tr.condition)
    has_captures = any(tr.captures for _, tr in consuming)
    has_emissions = any(tr.emissions for _, tr in consuming) or any(
        info.on_enter or info.on_accept for info in fsm.state_info.values()
    ) or any(
        tr.emissions
        for trs in fsm.transitions.values()
        for tr in trs
        if tr.epsilon
    )
    plain = is_plain(fsm)
    q = len(states)
    if has_captures:
        # Each capture register holds one value per consumed position, so
        # signatures are bounded by n^(#capture names) for an input of
        # length n.
        names = sorted({c.name for _, tr in consuming for c in tr.captures})
        bound = (
            f"per start offset: |Q| * |capture signatures| "
            f"<= {q} * n^{len(names)} (registers: {', '.join(names)})"
        )
    else:
        bound = f"per start offset: |Q| = {q} (capture-free: paths merge by state)"
    return FSMAnalysis(
        name=fsm.name,
        n_states=q,
        n_consuming=len(consuming),
        n_epsilon=n_eps,
        n_conditions=len(conditions),
        has_captures=has_captures,
        has_emissions=has_emissions,
        plain=plain,
        determinizable=plain and len(conditions) <= max_conditions,
        frontier_bound=bound,
    )


__all__ = [
    "FSMAnalysis",
    "accepts",
    "analyze",
    "determinize",
    "is_plain",
    "minimize",
]

"""Regex front-end: compile pattern strings into FSMs over label conditions.

The alphabet is label *conditions*, not characters, so the same compiler
serves token streams and character streams:

    <POS:DET> <POS:ADJ>* (?P<NP> <POS:NOUN>+)

Syntax
------
* ``<LABEL>``            atom: ``HasLabel("LABEL")``
* ``<LABEL@0.3>``        atom with ``min_weight=0.3``
* ``.``                  any slot (``Always``)
* juxtaposition          concatenation (whitespace insignificant)
* ``|``                  alternation
* ``*`` ``+`` ``?``      repetition (postfix)
* ``{m}`` ``{m,n}`` ``{m,}``  bounded repetition
* ``( ... )``            grouping (no emissions)
* ``(?P<name> ... )``    named group

Named groups do not name states — they tag *transitions* (tagged-NFA
style). Every consuming transition inside a group emits a membership
label ``name`` on the slot it consumes and records the group's first and
last consumed slots in hidden capture registers; on leaving the group,
``name_START`` and ``name_END`` are emitted onto exactly those slots. A
group that matches zero slots emits nothing. States stay anonymous;
emissions carry the names.

The grammar is regular (recursive descent, no backtracking), and the
construction is Thompson-style via :mod:`fsm_parser.combinators`, so the
resulting machine has O(len(pattern)) states.

This module was motivated by the regex->DFA machinery in the sibling
``regex_transformer`` project; the compile path is reimplemented (that
project's prefix-BFS compiler is depth-bounded and drops group structure).
"""

from __future__ import annotations

from dataclasses import dataclass

from fsm_parser.combinators import (
    _embed,
    alt,
    concat,
    literal,
    optional,
    plus,
    repeat,
    star,
)
from fsm_parser.fsm import (
    FSM,
    Always,
    Capture,
    CaptureAnchor,
    Condition,
    Emission,
    FSMBuilder,
    HasLabel,
    StateId,
    StateInfo,
    Transition,
)


class RegexError(ValueError):
    pass


# --- AST ---------------------------------------------------------------------


@dataclass(frozen=True)
class RxAtom:
    condition: Condition


@dataclass(frozen=True)
class RxConcat:
    parts: tuple


@dataclass(frozen=True)
class RxAlt:
    parts: tuple


@dataclass(frozen=True)
class RxRepeat:
    inner: object
    min_n: int
    max_n: int | None  # None = unbounded


@dataclass(frozen=True)
class RxGroup:
    name: str | None
    inner: object


# --- Parser ------------------------------------------------------------------


class _Parser:
    def __init__(self, pattern: str):
        self.s = pattern
        self.i = 0

    def error(self, msg: str) -> RegexError:
        return RegexError(f"{msg} at position {self.i} in {self.s!r}")

    def _skip_ws(self) -> None:
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    def peek(self) -> str | None:
        self._skip_ws()
        return self.s[self.i] if self.i < len(self.s) else None

    def parse(self):
        node = self.parse_alt()
        if self.peek() is not None:
            raise self.error(f"unexpected {self.s[self.i]!r}")
        return node

    def parse_alt(self):
        parts = [self.parse_concat()]
        while self.peek() == "|":
            self.i += 1
            parts.append(self.parse_concat())
        return parts[0] if len(parts) == 1 else RxAlt(tuple(parts))

    def parse_concat(self):
        parts = []
        while True:
            ch = self.peek()
            if ch is None or ch in "|)":
                break
            parts.append(self.parse_postfix())
        if not parts:
            raise self.error("empty expression")
        return parts[0] if len(parts) == 1 else RxConcat(tuple(parts))

    def parse_postfix(self):
        node = self.parse_atom()
        while True:
            ch = self.peek()
            if ch == "*":
                self.i += 1
                node = RxRepeat(node, 0, None)
            elif ch == "+":
                self.i += 1
                node = RxRepeat(node, 1, None)
            elif ch == "?":
                self.i += 1
                node = RxRepeat(node, 0, 1)
            elif ch == "{":
                node = RxRepeat(node, *self._parse_bounds())
            else:
                return node

    def _parse_bounds(self) -> tuple[int, int | None]:
        end = self.s.find("}", self.i)
        if end < 0:
            raise self.error("unterminated '{'")
        body = self.s[self.i + 1 : end].strip()
        self.i = end + 1
        try:
            if "," not in body:
                m = int(body)
                return m, m
            lo, hi = body.split(",", 1)
            return int(lo), (int(hi) if hi.strip() else None)
        except ValueError:
            raise self.error(f"bad repetition bounds {{{body}}}") from None

    def parse_atom(self):
        ch = self.peek()
        if ch == ".":
            self.i += 1
            return RxAtom(Always())
        if ch == "<":
            end = self.s.find(">", self.i)
            if end < 0:
                raise self.error("unterminated '<'")
            body = self.s[self.i + 1 : end]
            self.i = end + 1
            if not body:
                raise self.error("empty atom '<>'")
            min_weight = 0.0
            if "@" in body:
                body, raw_w = body.rsplit("@", 1)
                try:
                    min_weight = float(raw_w)
                except ValueError:
                    raise self.error(f"bad atom weight {raw_w!r}") from None
            return RxAtom(HasLabel(body, min_weight=min_weight))
        if ch == "(":
            self.i += 1
            name = None
            if self.s[self.i : self.i + 3] == "?P<":
                end = self.s.find(">", self.i + 3)
                if end < 0:
                    raise self.error("unterminated group name")
                name = self.s[self.i + 3 : end]
                if not name.isidentifier():
                    raise self.error(f"bad group name {name!r}")
                self.i = end + 1
            inner = self.parse_alt()
            if self.peek() != ")":
                raise self.error("expected ')'")
            self.i += 1
            return RxGroup(name, inner)
        raise self.error(f"unexpected {ch!r}" if ch else "unexpected end of pattern")


def parse_regex(pattern: str):
    """Parse a pattern into the regex AST (exposed for tests)."""
    return _Parser(pattern).parse()


# --- Group decoration --------------------------------------------------------


def _decorate_group(machine: FSM, name: str, weight: float) -> FSM:
    """Tag a group's span via hidden captures (Laurikari tagged-NFA style).

    Every consuming transition inside the group gains a membership
    emission ``name`` plus two hidden capture registers: a ``mode="first"``
    register holding the group's first consumed slot and an overwriting
    register holding its most recent (hence, on exit, last) consumed slot.
    The group is wrapped in a fresh exit state whose ``on_enter`` fires
    ``name_START`` / ``name_END`` anchored to those registers — so the
    span endpoints are exact even through loops, and a group that matched
    zero slots emits nothing (the anchors resolve to no slot).
    """
    first_reg = f"__g_{name}_first"
    last_reg = f"__g_{name}_last"
    group_caps = (
        Capture(first_reg, kind="index", mode="first"),
        Capture(last_reg, kind="index"),
    )
    new_transitions: dict[StateId, list[Transition]] = {}
    for src, trs in machine.transitions.items():
        bucket: list[Transition] = []
        for tr in trs:
            if tr.epsilon:
                bucket.append(tr)
                continue
            bucket.append(
                Transition(
                    target=tr.target,
                    condition=tr.condition,
                    weight=tr.weight,
                    emissions=tr.emissions + (Emission(name, weight, offset=0),),
                    captures=tr.captures + group_caps,
                    epsilon=tr.epsilon,
                    priority=tr.priority,
                )
            )
        new_transitions[src] = bucket
    tagged = FSM(
        name=machine.name,
        start=machine.start,
        transitions=new_transitions,
        accept=machine.accept,
        state_info=dict(machine.state_info),
    )

    b = FSMBuilder(machine.name)
    sub_start, sub_accepts = _embed(b, tagged)
    new_start = b.state("g_start")
    exit_state = b.state(f"g_exit_{name}")
    b.start(new_start).accept(exit_state)
    b.epsilon(new_start, sub_start)
    for a in sub_accepts:
        b.epsilon(a, exit_state)
    b.state_info(
        exit_state,
        on_enter=(
            Emission(f"{name}_START", weight, anchor=CaptureAnchor(first_reg)),
            Emission(f"{name}_END", weight, anchor=CaptureAnchor(last_reg)),
        ),
    )
    return b.build()


# --- Compiler ----------------------------------------------------------------


def _compile_node(node, group_weight: float) -> FSM:
    if isinstance(node, RxAtom):
        return literal(node.condition)
    if isinstance(node, RxConcat):
        return concat(*[_compile_node(p, group_weight) for p in node.parts])
    if isinstance(node, RxAlt):
        return alt(*[_compile_node(p, group_weight) for p in node.parts])
    if isinstance(node, RxRepeat):
        inner = _compile_node(node.inner, group_weight)
        if node.min_n == 0 and node.max_n is None:
            return star(inner)
        if node.min_n == 1 and node.max_n is None:
            return plus(inner)
        if node.min_n == 0 and node.max_n == 1:
            return optional(inner)
        return repeat(inner, node.min_n, node.max_n)
    if isinstance(node, RxGroup):
        inner = _compile_node(node.inner, group_weight)
        if node.name is None:
            return inner
        return _decorate_group(inner, node.name, group_weight)
    raise RegexError(f"unknown AST node: {node!r}")


def compile_regex(
    pattern: str,
    *,
    name: str | None = None,
    group_weight: float = 1.0,
    emit: tuple[Emission, ...] | list[Emission] = (),
) -> FSM:
    """Compile a pattern into an FSM ready for ``FSMScanner``.

    ``emit`` adds extra emissions fired when the whole pattern accepts
    (attached as ``on_accept`` to every accept state; the default anchor
    targets the last consumed slot).
    """
    ast = parse_regex(pattern)
    machine = _compile_node(ast, group_weight)
    machine.name = name or f"regex({pattern})"
    if emit:
        for acc in machine.accept:
            existing = machine.state_info.get(acc, StateInfo())
            machine.state_info[acc] = StateInfo(
                on_enter=existing.on_enter,
                on_accept=existing.on_accept + tuple(emit),
            )
    return machine


__all__ = [
    "RegexError",
    "compile_regex",
    "parse_regex",
    "RxAtom",
    "RxConcat",
    "RxAlt",
    "RxRepeat",
    "RxGroup",
]

"""Tokenization, character initialization, and multi-stream parser state.

The parser state is a dict of named streams, each an ordered list of
``Slot``. The ``"token"`` stream is the historical default; ``state.tokens``
is preserved as a property pointing at it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from fsm_parser.labels import LabelBag
from fsm_parser.slots import (
    ProvenanceEdge,
    Slot,
    SourceSpan,
    SlotId,
    Token,  # re-export
    slot_sort_key,
)


__all__ = [
    "Token",
    "Slot",
    "SourceSpan",
    "ProvenanceEdge",
    "ParserState",
    "tokenize",
    "initialize_state",
    "initialize_char_state",
]


_TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]")


@dataclass
class ParserState:
    streams: dict[str, list[Slot]] = field(default_factory=dict)
    layer: int = 0

    # Internal indexes; rebuilt lazily.
    _slots_by_id: dict[SlotId, Slot] = field(default_factory=dict)
    _id_counters: dict[str, int] = field(default_factory=dict)

    # ---- compatibility constructor ----------------------------------

    def __init__(
        self,
        tokens: list[Slot] | None = None,
        streams: dict[str, list[Slot]] | None = None,
        layer: int = 0,
    ) -> None:
        if streams is None:
            streams = {}
        # Accept the legacy ``ParserState(tokens=[...])`` form.
        if tokens is not None:
            streams = dict(streams)
            streams.setdefault("token", []).extend(tokens)
        self.streams = streams
        self.layer = layer
        self._slots_by_id = {}
        self._id_counters = {}
        self.reindex()

    # ---- index maintenance ------------------------------------------

    def reindex(self) -> None:
        """Rebuild slot-by-id lookup and ID counters from current streams."""
        self._slots_by_id = {}
        self._id_counters = {}
        for stream_name, slots in self.streams.items():
            for slot in slots:
                self._slots_by_id[slot.id] = slot
                # advance counter if id matches "<stream>:<n>"
                if slot.id.startswith(f"{stream_name}:"):
                    try:
                        n = int(slot.id.split(":", 1)[1])
                    except ValueError:
                        continue
                    cur = self._id_counters.get(stream_name, 0)
                    if n + 1 > cur:
                        self._id_counters[stream_name] = n + 1

    # ---- streams ----------------------------------------------------

    def stream(self, name: str) -> list[Slot]:
        return self.streams.setdefault(name, [])

    def stream_names(self) -> list[str]:
        return list(self.streams.keys())

    @property
    def tokens(self) -> list[Slot]:
        """Backwards-compat alias for ``stream("token")``."""
        return self.stream("token")

    # ---- slots ------------------------------------------------------

    def get_slot(self, slot_id: SlotId) -> Slot | None:
        return self._slots_by_id.get(slot_id)

    def add_slot(self, stream: str, slot: Slot) -> None:
        if slot.id in self._slots_by_id:
            raise ValueError(f"duplicate slot id: {slot.id}")
        if slot.stream != stream:
            raise ValueError(
                f"slot.stream {slot.stream!r} does not match target stream {stream!r}"
            )
        self.stream(stream).append(slot)
        self._slots_by_id[slot.id] = slot

    def next_id(self, stream: str) -> SlotId:
        n = self._id_counters.get(stream, 0)
        self._id_counters[stream] = n + 1
        return f"{stream}:{n}"

    def sort_stream(self, stream: str) -> None:
        slots = self.streams.get(stream)
        if slots is not None:
            slots.sort(key=slot_sort_key)


# ---- tokenization helpers ----------------------------------------------


def tokenize(text: str) -> list[str]:
    """Split text into word and punctuation tokens."""
    return _TOKEN_PATTERN.findall(text)


def _shape(text: str) -> str:
    parts = []
    for ch in text:
        if ch.isupper():
            parts.append("X")
        elif ch.islower():
            parts.append("x")
        elif ch.isdigit():
            parts.append("d")
        else:
            parts.append(ch)
    return "".join(parts)


def initialize_state(text: str) -> ParserState:
    """Tokenize text and assign initial identity labels in the token stream."""
    state = ParserState()
    cursor = 0
    for i, raw in enumerate(tokenize(text)):
        # Locate the surface position of this token in the original text.
        idx = text.find(raw, cursor)
        if idx < 0:
            idx = cursor
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
        slot.labels.add(f"LOWER:{raw.lower()}", 1.0)
        slot.labels.add(f"SHAPE:{_shape(raw)}", 1.0)
        slot.labels.add("TOKEN", 1.0)
        if not raw.isalnum():
            slot.labels.add("PUNCT", 1.0)
        state.add_slot("token", slot)
    state._id_counters["token"] = len(state.tokens)
    return state


def initialize_char_state(text: str) -> ParserState:
    """Create one character slot per character of ``text`` in the char stream."""
    state = ParserState()
    for i, ch in enumerate(text):
        slot = Slot(
            id=f"char:{i}",
            kind="char",
            stream="char",
            order=float(i),
            text=ch,
            source_span=SourceSpan(i, i + 1),
        )
        slot.labels.add("CHAR", 1.0)
        slot.labels.add(f"CHAR_LIT:{ch!r}", 1.0)
        state.add_slot("char", slot)
    state._id_counters["char"] = len(text)
    return state

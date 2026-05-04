"""Slot, SourceSpan, ProvenanceEdge — the generalized representational unit.

A ``Slot`` is the unit a parser block reads and writes. It generalizes
``Token`` so the same machinery handles characters, tokens, phrases,
semantic frames, and implied/gap units.

Slots live in named streams (``"token"``, ``"char"``, ``"phrase"``, etc.)
and carry stable string IDs of the form ``"<stream>:<n>"``. Provenance
edges link a slot back to the slots that produced it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from fsm_parser.labels import LabelBag


SlotId = str


@dataclass(frozen=True)
class SourceSpan:
    """Half-open interval into the original input (Python slicing)."""

    start: int
    end: int

    def length(self) -> int:
        return self.end - self.start


@dataclass(frozen=True)
class ProvenanceEdge:
    """An edge from a derived slot back to a contributing slot."""

    relation: str  # "derived_from", "alternate_to", "evidence_for", ...
    slot_id: SlotId


@dataclass
class Slot:
    """An ordered representational unit with a weighted label bag.

    Compared with the previous ``Token``: stable string ``id``, explicit
    ``stream`` and ``kind``, optional ``source_span`` and ``parents``.

    Backwards compatibility: ``Token`` is an alias for ``Slot``. The
    ``index`` property returns the integer suffix of token-stream IDs so
    existing code that reads ``token.index`` keeps working.
    """

    id: SlotId
    kind: str = "token"
    stream: str = "token"
    order: float = 0.0
    labels: LabelBag = field(default_factory=LabelBag)
    text: str | None = None
    source_span: SourceSpan | None = None
    parents: Tuple[ProvenanceEdge, ...] = ()

    @property
    def index(self) -> int:
        """Backwards-compat: integer suffix of an ID like ``"token:5"``."""
        if ":" in self.id:
            try:
                return int(self.id.rsplit(":", 1)[1])
            except ValueError:
                pass
        return -1


# Backwards-compat alias
Token = Slot


def slot_sort_key(slot: Slot) -> tuple:
    """Sort key for stream ordering."""
    span_start = slot.source_span.start if slot.source_span is not None else -1
    span_end = slot.source_span.end if slot.source_span is not None else -1
    return (slot.order, span_start, span_end, slot.id)

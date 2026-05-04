"""Optional projection of label-bag output into spans, edges, and clean
slot sequences.

Projection is read-only over a parser state. It does not mutate
``ParserState`` or its slots; it derives task-specific views from the
accumulated label evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

from fsm_parser.slots import Slot
from fsm_parser.tokens import ParserState


@dataclass(frozen=True)
class Span:
    label: str
    start: int           # stream position (or character index when source_span exists)
    end: int             # inclusive
    head: int | None = None


@dataclass(frozen=True)
class Edge:
    relation: str
    head: int
    dependent: int


def project_spans(
    state: ParserState,
    *,
    start_label: str,
    end_label: str,
    head_label: str | None = None,
    span_label: str = "SPAN",
    threshold: float = 0.1,
    stream: str = "token",
) -> list[Span]:
    """Pair start/end labels into spans within a stream."""
    slots = state.stream(stream)
    starts = [
        i for i, s in enumerate(slots) if s.labels.get(start_label) >= threshold
    ]
    ends = [
        i for i, s in enumerate(slots) if s.labels.get(end_label) >= threshold
    ]
    spans: list[Span] = []
    used_ends: set[int] = set()
    for s in starts:
        match_end = next(
            (e for e in ends if e >= s and e not in used_ends), None
        )
        if match_end is None:
            continue
        used_ends.add(match_end)
        head: int | None = None
        if head_label is not None:
            for i in range(s, match_end + 1):
                if slots[i].labels.get(head_label) >= threshold:
                    head = i
                    break
        spans.append(Span(label=span_label, start=s, end=match_end, head=head))
    return spans


def project_dependency_edges(
    state: ParserState,
    *,
    relation_prefix: str,
    threshold: float = 0.1,
    stream: str = "token",
) -> list[Edge]:
    """Read pointer-style labels like ``DEP:nsubj:5`` into edges.

    The resolved head index is the integer suffix encoded in the label,
    matching the legacy capture format. For new code that emits
    slot-id-shaped pointers, post-process the slot IDs separately.
    """
    edges: list[Edge] = []
    for pos, slot in enumerate(state.stream(stream)):
        for label, weight in slot.labels.items():
            if weight < threshold:
                continue
            if not label.startswith(relation_prefix):
                continue
            rest = label[len(relation_prefix) :]
            if ":" not in rest:
                continue
            relation, target = rest.rsplit(":", 1)
            try:
                head = int(target)
            except ValueError:
                continue
            edges.append(Edge(relation=relation, head=head, dependent=pos))
    return edges


def project_non_overlapping(
    state: ParserState,
    *,
    stream: str,
    score_label: str | None = None,
) -> list[Slot]:
    """Greedily pick a non-overlapping cover of slots from the stream.

    Slots without ``source_span`` are passed through unconditionally.
    For overlapping spans, the higher score wins; ties break by larger
    span first, then by stream order.
    """
    slots = list(state.stream(stream))

    def score(slot: Slot) -> float:
        if score_label is not None:
            return slot.labels.get(score_label)
        # Fall back to max non-FORGOTTEN weight
        items = [(l, w) for l, w in slot.labels.items() if l != "FORGOTTEN"]
        return max((w for _, w in items), default=0.0)

    spanned = [s for s in slots if s.source_span is not None]
    spanless = [s for s in slots if s.source_span is None]

    # Sort by start, then by descending span length, then by descending score.
    spanned.sort(
        key=lambda s: (
            s.source_span.start,
            -(s.source_span.end - s.source_span.start),
            -score(s),
        )
    )

    chosen: list[Slot] = []
    cursor = -1
    for s in spanned:
        if s.source_span.start < cursor:
            # Conflict with an already-chosen slot: prefer higher score.
            prev = chosen[-1]
            if score(s) > score(prev):
                chosen[-1] = s
                cursor = s.source_span.end
            continue
        chosen.append(s)
        cursor = s.source_span.end

    return chosen + spanless

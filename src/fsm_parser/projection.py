"""Optional projection of label-bag output into spans and dependencies."""

from __future__ import annotations

from dataclasses import dataclass

from fsm_parser.tokens import ParserState


@dataclass(frozen=True)
class Span:
    label: str
    start: int
    end: int  # inclusive
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
) -> list[Span]:
    """Pair start/end labels into spans, optionally noting head positions."""
    starts = [
        t.index for t in state.tokens if t.labels.get(start_label) >= threshold
    ]
    ends = [t.index for t in state.tokens if t.labels.get(end_label) >= threshold]
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
                if state.tokens[i].labels.get(head_label) >= threshold:
                    head = i
                    break
        spans.append(Span(label=span_label, start=s, end=match_end, head=head))
    return spans


def project_dependency_edges(
    state: ParserState,
    *,
    relation_prefix: str,
    threshold: float = 0.1,
) -> list[Edge]:
    """Read pointer-style labels like ``SUBJECT_OF:5`` into edges."""
    edges: list[Edge] = []
    for token in state.tokens:
        for label, weight in token.labels.items():
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
            edges.append(Edge(relation=relation, head=head, dependent=token.index))
    return edges

"""Inspection helpers: render slot streams and rule firing traces."""

from __future__ import annotations

from typing import Iterable

from fsm_parser.labels import AddSlot, LabelDelta, RepresentationDelta
from fsm_parser.pipeline import LayerTrace
from fsm_parser.tokens import ParserState


def render_state(
    state: ParserState,
    *,
    stream: str = "token",
    top_k: int = 5,
) -> str:
    """Multi-line table of the top labels per slot in a stream."""
    slots = state.stream(stream)
    lines = [f"Layer {state.layer} / stream {stream}"]
    width = max((len(s.text or "") for s in slots), default=4)
    for slot in slots:
        top = slot.labels.top_k(top_k)
        rendered = " ".join(f"{label}={weight:.2f}" for label, weight in top)
        text = slot.text or ""
        lines.append(f"{slot.id:<14} {text:<{width}}  {rendered}")
    return "\n".join(lines)


def _render_delta_one(d: RepresentationDelta) -> str:
    src = d.source or "?"
    if isinstance(d, LabelDelta):
        return f"  [{src}] add_label slot={d.slot_id} {d.label} += {d.weight:.3f}"
    if isinstance(d, AddSlot):
        return (
            f"  [{src}] add_slot stream={d.stream} id={d.slot.id} "
            f"text={d.slot.text!r} kind={d.slot.kind}"
        )
    return f"  [{src}] {d!r}"


def render_deltas(deltas: Iterable[RepresentationDelta]) -> str:
    deltas = list(deltas)
    if not deltas:
        return "  (no deltas)"
    return "\n".join(_render_delta_one(d) for d in deltas)


def render_trace(
    traces: list[LayerTrace],
    *,
    streams: Iterable[str] = ("token",),
    top_k: int = 5,
) -> str:
    """Render a full pipeline trace produced by ``parse_with_trace``."""
    out: list[str] = []
    streams = tuple(streams)
    for trace in traces:
        out.append(f"=== Layer {trace.layer} ({', '.join(trace.block_names)}) ===")
        if trace.deltas:
            out.append("Deltas:")
            out.append(render_deltas(trace.deltas))
        for s in streams:
            if s in trace.state.streams:
                out.append(render_state(trace.state, stream=s, top_k=top_k))
        out.append("")
    return "\n".join(out)

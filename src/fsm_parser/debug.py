"""Inspection helpers: render token-label tables and rule firing traces."""

from __future__ import annotations

from typing import Iterable

from fsm_parser.labels import LabelDelta
from fsm_parser.pipeline import LayerTrace
from fsm_parser.tokens import ParserState


def render_state(state: ParserState, *, top_k: int = 5) -> str:
    """Return a multi-line table showing the top labels per token."""
    lines = [f"Layer {state.layer}"]
    width = max((len(t.text) for t in state.tokens), default=4)
    for token in state.tokens:
        top = token.labels.top_k(top_k)
        rendered = " ".join(f"{label}={weight:.2f}" for label, weight in top)
        lines.append(f"{token.index:3d}  {token.text:<{width}}  {rendered}")
    return "\n".join(lines)


def render_deltas(deltas: Iterable[LabelDelta]) -> str:
    """Render deltas grouped by source for trace inspection."""
    lines: list[str] = []
    for d in deltas:
        src = d.source or "?"
        lines.append(f"  [{src}] tok={d.token_index} {d.label} += {d.weight:.3f}")
    return "\n".join(lines) if lines else "  (no deltas)"


def render_trace(traces: list[LayerTrace], *, top_k: int = 5) -> str:
    """Render a full pipeline trace produced by ``Parser.parse_with_trace``."""
    out: list[str] = []
    for trace in traces:
        out.append(f"=== Layer {trace.layer} ({', '.join(trace.block_names)}) ===")
        if trace.deltas:
            out.append("Deltas:")
            out.append(render_deltas(trace.deltas))
        out.append(render_state(trace.state, top_k=top_k))
        out.append("")
    return "\n".join(out)

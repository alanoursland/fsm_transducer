"""Decay, pruning, normalization, and delta application."""

from __future__ import annotations

from dataclasses import dataclass, field

from fsm_parser.labels import (
    AddSlot,
    FORGOTTEN,
    LabelBag,
    LabelDelta,
    RepresentationDelta,
)
from fsm_parser.tokens import ParserState


@dataclass(frozen=True)
class NormalizationConfig:
    decay: float = 1.0
    min_weight: float = 0.0
    max_labels: int = 64
    total_mass: float | None = None
    forgotten_label: str = FORGOTTEN


def apply_deltas(
    state: ParserState, deltas: list[RepresentationDelta]
) -> None:
    """Apply a list of deltas. Sorts streams whose membership changed."""
    touched_streams: set[str] = set()
    for d in deltas:
        if isinstance(d, LabelDelta):
            slot = state.get_slot(d.slot_id)
            if slot is not None:
                slot.labels.add(d.label, d.weight)
            continue
        if isinstance(d, AddSlot):
            if d.slot.stream != d.stream:
                raise ValueError(
                    f"AddSlot stream mismatch: delta={d.stream!r}, "
                    f"slot={d.slot.stream!r}"
                )
            state.add_slot(d.stream, d.slot)
            touched_streams.add(d.stream)
            continue
        raise TypeError(f"unknown delta type: {type(d).__name__}")
    for stream in touched_streams:
        state.sort_stream(stream)


def normalize(bag: LabelBag, config: NormalizationConfig) -> LabelBag:
    """Decay, prune to top-k, threshold-prune, and optionally rescale."""
    forgotten_label = config.forgotten_label

    forgotten_w = bag.weights.get(forgotten_label, 0.0) * config.decay
    decayed: list[tuple[str, float]] = []
    for label, weight in bag.weights.items():
        if label == forgotten_label:
            continue
        decayed.append((label, weight * config.decay))

    decayed.sort(key=lambda x: -x[1])

    keep: list[tuple[str, float]] = []
    dropped_mass = 0.0
    for label, weight in decayed:
        if len(keep) >= config.max_labels:
            dropped_mass += weight
            continue
        if weight < config.min_weight:
            dropped_mass += weight
            continue
        keep.append((label, weight))

    forgotten_w += dropped_mass

    if config.total_mass is not None:
        current = sum(w for _, w in keep) + forgotten_w
        if current > 0:
            scale = config.total_mass / current
            keep = [(l, w * scale) for l, w in keep]
            forgotten_w *= scale

    result = LabelBag()
    for label, weight in keep:
        result.weights[label] = weight
    if forgotten_w > 0:
        result.weights[forgotten_label] = forgotten_w
    return result


def normalize_state(
    state: ParserState,
    config: NormalizationConfig,
    *,
    stream_configs: dict[str, NormalizationConfig] | None = None,
) -> None:
    """Normalize every slot in every stream using the appropriate config."""
    stream_configs = stream_configs or {}
    for stream_name, slots in state.streams.items():
        cfg = stream_configs.get(stream_name, config)
        for slot in slots:
            slot.labels = normalize(slot.labels, cfg)

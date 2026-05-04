"""Decay, pruning, and normalization of label bags."""

from __future__ import annotations

from dataclasses import dataclass

from fsm_parser.labels import FORGOTTEN, LabelBag, LabelDelta
from fsm_parser.tokens import ParserState


@dataclass(frozen=True)
class NormalizationConfig:
    decay: float = 1.0
    min_weight: float = 0.0
    max_labels: int = 64
    total_mass: float | None = None
    forgotten_label: str = FORGOTTEN


def apply_deltas(state: ParserState, deltas: list[LabelDelta]) -> None:
    """Add each delta to its target token's label bag."""
    for d in deltas:
        if 0 <= d.token_index < len(state.tokens):
            state.tokens[d.token_index].labels.add(d.label, d.weight)


def normalize(bag: LabelBag, config: NormalizationConfig) -> LabelBag:
    """Apply decay, top-k and threshold pruning, and optional rescaling."""
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


def normalize_state(state: ParserState, config: NormalizationConfig) -> None:
    """Normalize every token's label bag in place."""
    for token in state.tokens:
        token.labels = normalize(token.labels, config)

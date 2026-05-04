"""Pipeline composition: stack blocks into layers and run them."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from fsm_parser.blocks import ParserBlock
from fsm_parser.labels import FORGOTTEN, RepresentationDelta
from fsm_parser.normalization import (
    NormalizationConfig,
    apply_deltas,
    normalize_state,
)
from fsm_parser.tokens import ParserState, initialize_state


@dataclass
class ParserConfig:
    decay: float = 1.0
    min_weight: float = 0.001
    max_labels_per_token: int = 64
    total_mass: float | None = None
    forgotten_label: str = FORGOTTEN
    stream_configs: dict[str, NormalizationConfig] = field(default_factory=dict)

    def to_normalization(self) -> NormalizationConfig:
        return NormalizationConfig(
            decay=self.decay,
            min_weight=self.min_weight,
            max_labels=self.max_labels_per_token,
            total_mass=self.total_mass,
            forgotten_label=self.forgotten_label,
        )


@dataclass
class LayerTrace:
    layer: int
    block_names: list[str]
    deltas: list[RepresentationDelta]
    state: ParserState  # snapshot AFTER applying deltas and normalizing


@dataclass
class Parser:
    """Stack of layers, each a list of blocks operating on the same state."""

    layers: list[list[ParserBlock]]
    config: ParserConfig = field(default_factory=ParserConfig)

    # ---- text-based entry points (existing API) ---------------------

    def parse(self, text: str) -> ParserState:
        return self.parse_state(initialize_state(text))

    def parse_with_trace(
        self, text: str
    ) -> tuple[ParserState, list[LayerTrace]]:
        return self.parse_state_with_trace(initialize_state(text))

    # ---- state-based entry points ----------------------------------

    def parse_state(self, state: ParserState) -> ParserState:
        default_cfg = self.config.to_normalization()
        for i, blocks in enumerate(self.layers):
            deltas: list[RepresentationDelta] = []
            for block in blocks:
                deltas.extend(block.apply(state))
            apply_deltas(state, deltas)
            normalize_state(
                state, default_cfg, stream_configs=self.config.stream_configs
            )
            state.layer = i + 1
        return state

    def parse_state_with_trace(
        self, state: ParserState
    ) -> tuple[ParserState, list[LayerTrace]]:
        traces: list[LayerTrace] = [
            LayerTrace(
                layer=0,
                block_names=["<init>"],
                deltas=[],
                state=deepcopy(state),
            )
        ]
        default_cfg = self.config.to_normalization()
        for i, blocks in enumerate(self.layers):
            deltas: list[RepresentationDelta] = []
            for block in blocks:
                deltas.extend(block.apply(state))
            apply_deltas(state, deltas)
            normalize_state(
                state, default_cfg, stream_configs=self.config.stream_configs
            )
            state.layer = i + 1
            traces.append(
                LayerTrace(
                    layer=i + 1,
                    block_names=[b.name for b in blocks],
                    deltas=list(deltas),
                    state=deepcopy(state),
                )
            )
        return state, traces

"""Load grammar definitions (blocks, FSMs, lexicons) from YAML files.

Format:

    layers:
      - blocks:
          - name: pos_dictionary
            type: lexical
            entries:
              the:
                POS:DET: 1.0
              book:
                POS:NOUN: 0.6
                POS:VERB: 0.4
          - name: np_rules
            type: fsm
            fsms:
              - name: det_noun_np
                pattern:
                  - has: POS:DET
                    min_weight: 0.3
                  - has: POS:NOUN
                    min_weight: 0.3
                emit:
                  - label: PHRASE:NP_HEAD
                    weight: 0.8
                    offset: 0      # relative to the firing transition
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from fsm_parser.blocks import FSMBlock, LexicalBlock, ParserBlock
from fsm_parser.fsm import (
    Always,
    Condition,
    Emission,
    HasAnyLabel,
    HasLabel,
    compile_linear,
)


class ConfigError(ValueError):
    pass


def _condition_from_dict(node: dict[str, Any]) -> Condition:
    if "has" in node:
        return HasLabel(label=node["has"], min_weight=float(node.get("min_weight", 0.0)))
    if "has_any" in node:
        labels = tuple(node["has_any"])
        return HasAnyLabel(labels=labels, min_weight=float(node.get("min_weight", 0.0)))
    if node.get("any") is True:
        return Always()
    raise ConfigError(f"unknown condition node: {node!r}")


def _emission_from_dict(node: dict[str, Any]) -> Emission:
    return Emission(
        label=node["label"],
        weight=float(node.get("weight", 1.0)),
        offset=int(node.get("offset", 0)),
    )


def _fsm_block_from_dict(node: dict[str, Any]) -> FSMBlock:
    fsms = []
    for fsm_node in node.get("fsms", []):
        if "pattern" not in fsm_node:
            raise ConfigError(
                f"FSM {fsm_node.get('name')!r} requires a 'pattern' (linear form)"
            )
        conditions = [_condition_from_dict(c) for c in fsm_node["pattern"]]
        emissions = [_emission_from_dict(e) for e in fsm_node.get("emit", [])]
        fsms.append(compile_linear(fsm_node.get("name", "fsm"), conditions, emissions))
    return FSMBlock(name=node["name"], fsms=fsms)


def _lexical_block_from_dict(node: dict[str, Any]) -> LexicalBlock:
    raw_entries = node.get("entries", {})
    entries = {
        word.lower(): {label: float(w) for label, w in labels.items()}
        for word, labels in raw_entries.items()
    }
    return LexicalBlock(name=node["name"], entries=entries)


def _block_from_dict(node: dict[str, Any]) -> ParserBlock:
    block_type = node.get("type")
    if block_type == "lexical":
        return _lexical_block_from_dict(node)
    if block_type == "fsm":
        return _fsm_block_from_dict(node)
    raise ConfigError(f"unknown block type: {block_type!r}")


@dataclass
class GrammarConfig:
    layers: list[list[ParserBlock]]


def load_grammar(path: str | Path) -> GrammarConfig:
    raw = yaml.safe_load(Path(path).read_text())
    return parse_grammar(raw)


def parse_grammar(raw: dict[str, Any]) -> GrammarConfig:
    if "layers" not in raw:
        raise ConfigError("grammar must contain top-level 'layers'")
    layers: list[list[ParserBlock]] = []
    for layer_node in raw["layers"]:
        blocks = [_block_from_dict(b) for b in layer_node.get("blocks", [])]
        layers.append(blocks)
    return GrammarConfig(layers=layers)

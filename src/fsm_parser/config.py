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
from fsm_parser.combinators import (
    alt,
    concat,
    literal,
    optional,
    plus,
    star,
)
from fsm_parser.fsm import (
    FSM,
    Always,
    And,
    AtSentenceEnd,
    AtSentenceStart,
    Capture,
    CaptureAnchor,
    Condition,
    Emission,
    EmissionAnchor,
    FiringOffset,
    HasAnyLabel,
    HasLabel,
    Not,
    Or,
    ScanEnd,
    ScanStart,
    WeightAbove,
    WeightBelow,
    compile_linear,
)
from fsm_parser.regex_compile import compile_regex


class ConfigError(ValueError):
    pass


def _condition_from_dict(node: dict[str, Any]) -> Condition:
    if "has" in node:
        return HasLabel(label=node["has"], min_weight=float(node.get("min_weight", 0.0)))
    if "has_any" in node:
        labels = tuple(node["has_any"])
        return HasAnyLabel(labels=labels, min_weight=float(node.get("min_weight", 0.0)))
    if "weight_above" in node:
        return WeightAbove(label=node["weight_above"], threshold=float(node["threshold"]))
    if "weight_below" in node:
        return WeightBelow(label=node["weight_below"], threshold=float(node["threshold"]))
    if "not" in node:
        return Not(_condition_from_dict(node["not"]))
    if "and" in node:
        return And(tuple(_condition_from_dict(p) for p in node["and"]))
    if "or" in node:
        return Or(tuple(_condition_from_dict(p) for p in node["or"]))
    if node.get("at_start") is True:
        return AtSentenceStart()
    if node.get("at_end") is True:
        return AtSentenceEnd()
    if node.get("any") is True:
        return Always()
    raise ConfigError(f"unknown condition node: {node!r}")


def _anchor_from_dict(node: dict[str, Any] | None) -> EmissionAnchor:
    if node is None:
        return FiringOffset(0)
    kind = node.get("kind", "firing")
    offset = int(node.get("offset", 0))
    if kind == "firing":
        return FiringOffset(offset)
    if kind == "capture":
        return CaptureAnchor(name=node["name"], offset=offset)
    if kind == "scan_start":
        return ScanStart(offset)
    if kind == "scan_end":
        return ScanEnd(offset)
    raise ConfigError(f"unknown anchor kind: {kind!r}")


def _emission_from_dict(node: dict[str, Any]) -> Emission:
    if "anchor" in node:
        return Emission(
            label=node["label"],
            weight=float(node.get("weight", 1.0)),
            anchor=_anchor_from_dict(node["anchor"]),
        )
    return Emission(
        label=node["label"],
        weight=float(node.get("weight", 1.0)),
        offset=int(node.get("offset", 0)),
    )


def _captures_from_list(items: Any) -> tuple[Capture, ...]:
    if not items:
        return ()
    return tuple(
        Capture(name=c["name"], kind=c.get("kind", "index")) for c in items
    )


def _machine_from_dict(node: dict[str, Any]) -> FSM:
    """Compile a combinator-style machine spec into an FSM."""
    op = node.get("op")
    name = node.get("name")
    if op == "literal" or (op is None and "match" in node):
        return literal(
            _condition_from_dict(node["match"]),
            emissions=[_emission_from_dict(e) for e in node.get("emit", [])],
            captures=_captures_from_list(node.get("capture", ())),
            weight=float(node.get("weight", 1.0)),
            name=name,
        )
    if op == "concat":
        return concat(
            *[_machine_from_dict(m) for m in node["machines"]], name=name
        )
    if op == "alt":
        return alt(*[_machine_from_dict(m) for m in node["machines"]], name=name)
    if op == "star":
        return star(_machine_from_dict(node["machine"]), name=name)
    if op == "plus":
        return plus(_machine_from_dict(node["machine"]), name=name)
    if op == "optional":
        return optional(_machine_from_dict(node["machine"]), name=name)
    raise ConfigError(f"unknown machine op: {op!r} in node {node!r}")


def _fsm_block_from_dict(node: dict[str, Any]) -> FSMBlock:
    fsms: list[FSM] = []
    for fsm_node in node.get("fsms", []):
        # Three forms: linear "pattern" (legacy), combinator "machine",
        # or a "regex" string (see fsm_parser.regex_compile for syntax).
        if "regex" in fsm_node:
            fsms.append(
                compile_regex(
                    fsm_node["regex"],
                    name=fsm_node.get("name"),
                    group_weight=float(fsm_node.get("group_weight", 1.0)),
                    emit=[_emission_from_dict(e) for e in fsm_node.get("emit", [])],
                )
            )
            continue
        if "machine" in fsm_node:
            machine = _machine_from_dict(fsm_node["machine"])
            if "name" in fsm_node:
                machine.name = fsm_node["name"]
            fsms.append(machine)
            continue
        if "pattern" not in fsm_node:
            raise ConfigError(
                f"FSM {fsm_node.get('name')!r} requires a 'pattern' or 'machine'"
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

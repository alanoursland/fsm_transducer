"""The codex loader: resolve catalogued components to built objects.

The triad: fsm_parser is the engine, codex/ is the inventory,
languages/ are assembled products. Components are FACTORIES (possibly
parameterized — the input-indexed schemas), referenced by manifest:

    from fsm_parser import codex
    machine = codex.load("story.minus")
    checker = codex.load("checker.scope.let", name="x")
    lexicon = codex.load("lexicon.mcguffey.tier1")
    bundle  = codex.load("bundle.english_tier1")   # dict of id -> loaded
    hits    = codex.search("operand")

Behaviorally identical to direct imports: the loader resolves to the
same factory functions the language runners already call.
"""

from __future__ import annotations

import importlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CODEX_ROOT = Path(__file__).parent.parent.parent / "codex"


@lru_cache(maxsize=1)
def manifests() -> dict[str, dict]:
    """All component manifests, keyed by id."""
    out: dict[str, dict] = {}
    for path in sorted(CODEX_ROOT.rglob("component.yaml")):
        m = yaml.safe_load(path.read_text())
        m["_path"] = str(path.parent.relative_to(CODEX_ROOT))
        if m["id"] in out:
            raise ValueError(f"duplicate codex id: {m['id']}")
        out[m["id"]] = m
    return out


def _resolve_factory(spec: str):
    module_name, _, attr = spec.partition(":")
    return getattr(importlib.import_module(module_name), attr)


def load(component_id: str, **overrides: Any) -> Any:
    """Build a component. Keyword args override manifest params
    (required for schema components like per-identifier checkers)."""
    m = manifests().get(component_id)
    if m is None:
        raise KeyError(f"no codex component {component_id!r}; "
                       f"try codex.search(...)")
    kind = m["kind"]
    if kind == "bundle":
        return {dep: load(dep) for dep in m["imports"]}
    if kind == "vocabulary":
        path = Path(__file__).parent.parent.parent / m["path"]
        data = yaml.safe_load(path.read_text())
        return data.get("entries", data)
    params = dict(m.get("params", {}))
    params.update(overrides)
    return _resolve_factory(m["factory"])(**params)


def search(term: str) -> list[dict]:
    """Substring search over ids, kinds, search_terms, and notes."""
    term = term.lower()
    hits = []
    for m in manifests().values():
        hay = " ".join([m["id"], m["kind"], m.get("notes", ""),
                        " ".join(map(str, m.get("search_terms", [])))]).lower()
        if term in hay:
            hits.append(m)
    return hits


def catalog_jsonl() -> str:
    """The machine-readable catalog, with I/O alphabets MEASURED via
    analysis.signature() — a component that does not build cannot be
    catalogued. Written to codex/catalog.jsonl by build_catalog.py."""
    from fsm_parser.analysis import signature

    lines = []
    for m in manifests().values():
        entry = {k: v for k, v in m.items() if not k.startswith("_")}
        entry["path"] = m["_path"]
        if m["kind"] in ("tracker", "story", "checker", "emitter_set"):
            built = load(m["id"])
            machines = built if isinstance(built, list) else [built]
            ins: set[str] = set()
            outs: set[str] = set()
            for fsm in machines:
                sig = signature(fsm)
                ins |= sig.inputs
                outs |= sig.outputs
            entry["inputs"] = sorted(ins)
            entry["outputs"] = sorted(outs)
            entry["n_machines"] = len(machines)
        lines.append(json.dumps(entry, sort_keys=True))
    return "\n".join(lines) + "\n"

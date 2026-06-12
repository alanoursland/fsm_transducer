"""The codex: every component loads, catalogs are honest, behavior is
identical to direct imports."""

import json

from fsm_parser import codex
from fsm_parser.analysis import signature


def test_every_component_loads():
    for cid, m in codex.manifests().items():
        built = codex.load(cid)
        assert built is not None, cid
        if m["kind"] in ("tracker", "story"):
            assert signature(built).inputs, cid   # a real machine


def test_loader_is_behaviorally_identical_to_direct_import():
    from fsm_parser.imp_lang import build_minus_story, build_scope_checker
    a, b = codex.load("story.minus"), build_minus_story()
    assert a.name == b.name and signature(a) == signature(b)
    c, d = codex.load("checker.scope.let", name="zz"), build_scope_checker("zz")
    assert c.name == d.name == "scope_check@zz"


def test_schema_params_override():
    deep = codex.load("tracker.bracket", max_depth=2)
    default = codex.load("tracker.bracket")
    assert len(deep.states()) < len(default.states())


def test_vocabulary_and_bundle():
    lex = codex.load("lexicon.mcguffey.tier1")
    assert lex["play"]["V"] == 0.55
    bundle = codex.load("bundle.english_tier1")
    assert set(bundle) == {"lexicon.mcguffey.tier1", "story.clause.mcguffey1",
                           "emitters.token.mcguffey1"}


def test_search():
    assert any(m["id"] == "story.minus" for m in codex.search("operand"))
    assert any(m["id"] == "tracker.angle.cpp" for m in codex.search(">>"))
    assert codex.search("zzzznope") == []


def test_catalog_is_fresh_and_measured():
    """catalog.jsonl must match the manifests (regenerate after edits),
    and its alphabets are measured, so they must match signature()."""
    on_disk = (codex.CODEX_ROOT / "catalog.jsonl").read_text()
    assert on_disk == codex.catalog_jsonl(), \
        "stale catalog: run python codex/build_catalog.py"
    entry = next(json.loads(line) for line in on_disk.split("\n")
                 if line and json.loads(line)["id"] == "story.minus")
    assert set(entry["inputs"]) == set(signature(codex.load("story.minus")).inputs)

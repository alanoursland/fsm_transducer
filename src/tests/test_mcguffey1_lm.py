"""The autoregressive LM built from the tier-1 parser machine."""

import subprocess
import sys
from pathlib import Path

from fsm_parser.mcguffey1_lang import lexicon, parse
from fsm_parser.mcguffey1_lm import (
    generate_lm,
    next_token_distribution,
    support,
)


def test_distribution_follows_the_machine():
    # after "the cat" the frontier wants a verb phrase, not a determiner
    d = next_token_distribution(["the", "cat"])
    assert d, "live frontier must predict something"
    assert "see" in d or "sees" in d
    assert "the" not in d
    # after a fronted modal, the frontier wants a subject (inversion)
    d = next_token_distribution(["can"])
    assert "ann" in d
    assert d.get("ann", 0) > 0


def test_dead_prefix_predicts_nothing():
    # three bare verbs kill every path; note "the the the" does NOT —
    # the NP determiner skip loop accepts it, and so does the parser
    assert next_token_distribution(["ran", "ran", "ran"]) == {}
    assert next_token_distribution(["the", "the", "the"])  # alive, honestly


def test_incremental_cache_equals_batch_scan():
    """The KV cache: advancing a FrontierCache one token at a time must
    reproduce, exactly, the frontier a full rescan would build — same
    states, weights, and capture positions — so generation is unchanged
    while the per-token cost drops from O(prefix) to O(1)."""
    from fsm_parser.fsm import FrontierCache
    from fsm_parser.mcguffey1_lang import _machine, token_slot
    from fsm_parser.mcguffey1_lm import _frontier, distribution_from_frontier

    def key(frontier):
        return sorted(
            (str(p.state), round(p.weight, 9),
             tuple(sorted((k, v.pos) for k, v in p.captures.items())))
            for p in frontier)

    for prefix in ([], ["the", "cat"], ["can", "ann"], ["see", "spot"],
                   ["the", "good", "child"], ["i", "like", "to", "see"],
                   ["do", "not", "rob"], ["the", "the", "the"]):
        cache = FrontierCache(_machine())
        for i, w in enumerate(prefix):
            cache.push(token_slot(w, i))
        assert key(cache.frontier) == key(_frontier(prefix)), prefix
        assert (distribution_from_frontier(cache.frontier, len(prefix))
                == next_token_distribution(prefix)), prefix


def test_support_is_soft_matches():
    from fsm_parser.fsm import And, HasLabel, Not, Or
    labels = {"N": 0.9, "V": 0.3}
    assert support(HasLabel("N"), labels) == 0.9
    assert support(And((HasLabel("N"), Not(HasLabel("DET")))), labels) == 0.9
    assert support(Or((HasLabel("DET"), HasLabel("V"))), labels) == 0.3
    assert support(HasLabel("DET"), labels) == 0.0


def test_generated_sentences_parse_and_are_covered():
    text = generate_lm(4, seed=11, temperature=0.7)
    # every emitted sentence parses to frames (the acceptance gate)
    for s in text.replace("? ", "?\n").replace(". ", ".\n").split("\n"):
        assert parse(s), s


def test_prompted_generation_continues_the_prompt():
    text = generate_lm(2, seed=3, prompt=["the", "cat"])
    for s in text.replace("? ", "?\n").replace(". ", ".\n").split("\n"):
        assert s.lower().startswith("the cat")


def test_lm_is_deterministic_under_seed():
    a = generate_lm(3, seed=42, temperature=0.7)
    b = generate_lm(3, seed=42, temperature=0.7)
    assert a == b


def test_lm_vocabulary_is_the_lexicon():
    text = generate_lm(5, seed=1, temperature=0.7)
    lex = lexicon()
    for tok in text.lower().replace("?", "").replace(".", "").replace(",", "").split():
        assert tok in lex, tok


def test_lm_module_cli_generates_text():
    src = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "fsm_parser.mcguffey1_lm",
            "2",
            "--seed",
            "1",
            "--temperature",
            "0.7",
        ],
        cwd=src,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == generate_lm(2, seed=1, temperature=0.7)


def test_lm_module_cli_accepts_prompt():
    src = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "fsm_parser.mcguffey1_lm",
            "1",
            "--seed",
            "3",
            "--prompt",
            "the cat",
        ],
        cwd=src,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.lower().startswith("the cat")

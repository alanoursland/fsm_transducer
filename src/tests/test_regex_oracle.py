"""Differential test: the regex front-end against Python's ``re``.

Random regexes over a two-letter alphabet are rendered both into this
project's syntax (``<CH:a>``) and Python ``re`` syntax (``a``), then both
engines are compared for full-match acceptance over every string up to a
fixed length. The oracle trick is borrowed from the regex_transformer
project's test approach; seeds are fixed for reproducibility.
"""

import itertools
import random
import re

from fsm_parser.analysis import accepts
from fsm_parser.regex_compile import compile_regex
from fsm_parser.slots import Slot

ALPHABET = ["a", "b"]


def _random_ast(rng, depth):
    """Return (our_syntax, python_syntax)."""
    if depth <= 0 or rng.random() < 0.4:
        ch = rng.choice(ALPHABET)
        return f"<CH:{ch}>", ch
    kind = rng.choice(["concat", "alt", "star", "plus", "opt", "rep"])
    if kind == "concat":
        pairs = [_random_ast(rng, depth - 1) for _ in range(rng.randint(2, 3))]
        return " ".join(p[0] for p in pairs), "".join(p[1] for p in pairs)
    if kind == "alt":
        pairs = [_random_ast(rng, depth - 1) for _ in range(2)]
        return (
            f"({pairs[0][0]} | {pairs[1][0]})",
            f"(?:{pairs[0][1]}|{pairs[1][1]})",
        )
    ours, py = _random_ast(rng, depth - 1)
    if kind == "star":
        return f"({ours})*", f"(?:{py})*"
    if kind == "plus":
        return f"({ours})+", f"(?:{py})+"
    if kind == "opt":
        return f"({ours})?", f"(?:{py})?"
    lo = rng.randint(0, 2)
    hi = lo + rng.randint(0, 2)
    return f"({ours}){{{lo},{hi}}}", f"(?:{py}){{{lo},{hi}}}"


def _slots(word):
    out = []
    for i, ch in enumerate(word):
        slot = Slot(id=f"token:{i}", order=float(i))
        slot.labels.add(f"CH:{ch}", 1.0)
        out.append(slot)
    return out


def test_acceptance_agrees_with_python_re():
    rng = random.Random(20260610)
    words = [
        "".join(w)
        for n in range(5)
        for w in itertools.product(ALPHABET, repeat=n)
    ]
    for _ in range(40):
        ours, py = _random_ast(rng, depth=3)
        fsm = compile_regex(ours)
        oracle = re.compile(py)
        for word in words:
            expected = oracle.fullmatch(word) is not None
            got = accepts(fsm, _slots(word))
            assert got == expected, (ours, py, word)

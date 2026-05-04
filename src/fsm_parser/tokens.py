"""Token frames and initial tokenization."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from fsm_parser.labels import LabelBag


_TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]")


@dataclass
class Token:
    index: int
    text: str
    labels: LabelBag = field(default_factory=LabelBag)


@dataclass
class ParserState:
    tokens: list[Token]
    layer: int = 0


def tokenize(text: str) -> list[str]:
    """Split text into word and punctuation tokens."""
    return _TOKEN_PATTERN.findall(text)


def _shape(text: str) -> str:
    parts = []
    for ch in text:
        if ch.isupper():
            parts.append("X")
        elif ch.islower():
            parts.append("x")
        elif ch.isdigit():
            parts.append("d")
        else:
            parts.append(ch)
    return "".join(parts)


def initialize_state(text: str) -> ParserState:
    """Tokenize text and assign initial identity labels."""
    tokens: list[Token] = []
    for i, raw in enumerate(tokenize(text)):
        token = Token(index=i, text=raw)
        token.labels.add(f"TEXT:{raw}", 1.0)
        token.labels.add(f"LOWER:{raw.lower()}", 1.0)
        token.labels.add(f"SHAPE:{_shape(raw)}", 1.0)
        token.labels.add("TOKEN", 1.0)
        if not raw.isalnum():
            token.labels.add("PUNCT", 1.0)
        tokens.append(token)
    return ParserState(tokens=tokens, layer=0)

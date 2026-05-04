"""Weighted label bags and deltas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


FORGOTTEN = "FORGOTTEN"


@dataclass
class LabelBag:
    weights: dict[str, float] = field(default_factory=dict)

    def add(self, label: str, weight: float) -> None:
        self.weights[label] = self.weights.get(label, 0.0) + weight

    def set(self, label: str, weight: float) -> None:
        self.weights[label] = weight

    def get(self, label: str, default: float = 0.0) -> float:
        return self.weights.get(label, default)

    def has(self, label: str, threshold: float = 0.0) -> bool:
        return self.weights.get(label, 0.0) >= threshold

    def remove(self, label: str) -> None:
        self.weights.pop(label, None)

    def items(self) -> Iterable[tuple[str, float]]:
        return self.weights.items()

    def total(self) -> float:
        return sum(self.weights.values())

    def top_k(self, k: int) -> list[tuple[str, float]]:
        return sorted(self.weights.items(), key=lambda x: -x[1])[:k]

    def copy(self) -> "LabelBag":
        return LabelBag(weights=dict(self.weights))

    def __len__(self) -> int:
        return len(self.weights)

    def __contains__(self, label: str) -> bool:
        return label in self.weights


@dataclass
class LabelDelta:
    token_index: int
    label: str
    weight: float
    source: str | None = None

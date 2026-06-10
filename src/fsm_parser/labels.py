"""Weighted label bags and representation deltas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Union

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


@dataclass(frozen=True, init=False)
class LabelDelta:
    """Add weight to a label on a target slot.

    Canonical form uses ``slot_id``. The legacy ``token_index`` keyword
    and integer-positional first argument are accepted and converted to
    a ``"token:<n>"`` slot ID. ``token_index`` is exposed as a read-only
    property for backwards compatibility.
    """

    slot_id: str
    label: str
    weight: float
    source: str | None

    def __init__(
        self,
        slot_id_or_token_index: "int | str | None" = None,
        label: str | None = None,
        weight: float | None = None,
        source: str | None = None,
        *,
        slot_id: str | None = None,
        token_index: int | None = None,
    ) -> None:
        # Resolve slot identity from any of the supported forms.
        if slot_id is not None:
            sid = slot_id
        elif token_index is not None:
            sid = f"token:{token_index}"
        elif isinstance(slot_id_or_token_index, int):
            sid = f"token:{slot_id_or_token_index}"
        elif isinstance(slot_id_or_token_index, str):
            sid = slot_id_or_token_index
        else:
            raise TypeError("LabelDelta requires slot_id or token_index")

        if label is None or weight is None:
            raise TypeError("LabelDelta requires label and weight")

        object.__setattr__(self, "slot_id", sid)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "weight", weight)
        object.__setattr__(self, "source", source)

    @property
    def token_index(self) -> int:
        """Integer suffix of the slot ID when it looks like ``token:<n>``.

        Returns ``-1`` if the slot is not in the ``"token"`` stream.
        """
        if self.slot_id.startswith("token:"):
            try:
                return int(self.slot_id.split(":", 1)[1])
            except ValueError:
                return -1
        return -1


# Canonical name for new code; identical to LabelDelta.
AddLabel = LabelDelta


@dataclass(frozen=True)
class AddSlot:
    """Insert a new slot into a stream."""

    stream: str
    slot: object  # Slot — typed loosely to avoid circular imports
    source: str | None = None


RepresentationDelta = Union[LabelDelta, AddSlot]

"""Weight algebras for FSM path arithmetic.

A semiring fixes two operations:

* ``times``: how transition, path, and emission weights compose along
  a single path (the old ``combine`` callable).
* ``plus``: how independent paths combine when they converge at the
  same configuration during scanning.

The default ``ProductReal`` matches the previous default of plain
multiplication. Tropical and log semirings cover best-path and
log-probability use cases.
"""

from __future__ import annotations

import math
from typing import Protocol


class Semiring(Protocol):
    one: float
    zero: float

    def times(self, a: float, b: float) -> float: ...
    def plus(self, a: float, b: float) -> float: ...


class ProductReal:
    one: float = 1.0
    zero: float = 0.0

    def times(self, a: float, b: float) -> float:
        return a * b

    def plus(self, a: float, b: float) -> float:
        return a + b


class TropicalMin:
    """Best-path semiring with min-plus algebra."""

    one: float = 0.0
    zero: float = float("inf")

    def times(self, a: float, b: float) -> float:
        return a + b

    def plus(self, a: float, b: float) -> float:
        return min(a, b)


class TropicalMax:
    """Like TropicalMin but selects the maximum-weight path."""

    one: float = 0.0
    zero: float = float("-inf")

    def times(self, a: float, b: float) -> float:
        return a + b

    def plus(self, a: float, b: float) -> float:
        return max(a, b)


class LogSemiring:
    """Negative-log probability semiring (numerically stable)."""

    one: float = 0.0
    zero: float = float("inf")

    def times(self, a: float, b: float) -> float:
        return a + b

    def plus(self, a: float, b: float) -> float:
        if a == self.zero:
            return b
        if b == self.zero:
            return a
        m = min(a, b)
        return m - math.log(math.exp(-(a - m)) + math.exp(-(b - m)))


class LegacyMul:
    """Backwards-compat shim for the previous ``combine=mul`` default.

    ``plus`` collapses to ``max`` so that converging paths keep the
    strongest weight rather than summing — preserving prior emission
    counts in tests written against the old scanner.
    """

    one: float = 1.0
    zero: float = 0.0

    def times(self, a: float, b: float) -> float:
        return a * b

    def plus(self, a: float, b: float) -> float:
        return max(a, b)

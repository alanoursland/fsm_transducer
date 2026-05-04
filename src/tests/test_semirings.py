import math

from fsm_parser.semirings import (
    LogSemiring,
    ProductReal,
    TropicalMax,
    TropicalMin,
)


def test_product_real_identities():
    s = ProductReal()
    assert s.times(s.one, 0.7) == 0.7
    assert s.plus(s.zero, 0.3) == 0.3
    assert s.times(0.5, 0.4) == 0.2
    assert s.plus(0.5, 0.4) == 0.9


def test_tropical_min_picks_smallest():
    s = TropicalMin()
    assert s.times(0.0, 0.5) == 0.5
    assert s.plus(0.3, 0.7) == 0.3
    assert s.zero == float("inf")


def test_tropical_max_picks_largest():
    s = TropicalMax()
    assert s.plus(0.3, 0.7) == 0.7


def test_log_semiring_logsumexp():
    s = LogSemiring()
    a, b = -math.log(0.4), -math.log(0.6)
    expected = -math.log(0.4 + 0.6)
    assert abs(s.plus(a, b) - expected) < 1e-9


def test_log_semiring_handles_zero():
    s = LogSemiring()
    assert s.plus(s.zero, 0.5) == 0.5
    assert s.plus(0.5, s.zero) == 0.5

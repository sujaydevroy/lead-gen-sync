"""Helpers that reproduce JavaScript number behaviour, so results match the frontend exactly."""

from __future__ import annotations

import math
from collections.abc import Iterable


def js_sum(values: Iterable[float]) -> float:
    """Left-to-right addition like Array.reduce (Python 3.12+ sum() compensates for rounding)."""
    total = 0
    for value in values:
        total = total + value
    return total


def js_number_str(value: float) -> str:
    """String(number) for the value ranges used here (e.g. 742428 not 742428.0)."""
    if isinstance(value, int):
        return str(value)
    if math.isfinite(value) and value.is_integer() and abs(value) < 1e21:
        return str(int(value))
    return repr(value)


def js_round_4(value: float) -> float:
    """Number(value.toFixed(4))."""
    return float(f"{value:.4f}")

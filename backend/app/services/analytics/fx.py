"""Currency conversion with USD-based rates (port of frontend/src/lib/fx.js)."""

from __future__ import annotations


def convert_amount(amount: float, from_currency: str, to_currency: str, rates: dict[str, float]) -> float | None:
    """Convert using "USD per 1 unit" rates. None when either currency has no rate."""
    if from_currency == to_currency:
        return amount
    from_rate = rates.get(from_currency)
    to_rate = rates.get(to_currency)
    if not from_rate or not to_rate:
        return None
    return (amount * from_rate) / to_rate

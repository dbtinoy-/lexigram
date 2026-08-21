"""Domain model for the resilient rates demo."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RateQuote:
    """One exchange-rate observation.

    Attributes:
        pair: Currency pair symbol, e.g. ``EUR/USD``.
        rate: The quoted rate.
        fetched_at: Unix timestamp of the observation.
        source: Where this instance came from: ``upstream``, ``cache``
            or ``stale``.
    """

    pair: str
    rate: Decimal
    fetched_at: float
    source: str


__all__ = ["RateQuote"]

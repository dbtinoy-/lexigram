"""Domain model for the resilient rates demo.

Convention followed: **Value type** — ``RateQuote`` is a frozen dataclass
that represents a single exchange-rate observation.  It carries no
behavior beyond serialization/deserialization and is passed freely across
layer boundaries.

The ``source`` field tracks where the quote came from:

- ``"upstream"`` — freshly fetched from the simulated provider
- ``"cache"`` — served from the cache-aside layer
- ``"stale"`` — served from the stale store while the circuit is open
"""

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

    def to_payload(self) -> dict[str, object]:
        """Return the JSON-safe payload stored in the cache backend."""
        return {
            "pair": self.pair,
            "rate": str(self.rate),
            "fetched_at": self.fetched_at,
            "source": self.source,
        }

    @classmethod
    def from_payload(cls, raw: dict[str, object]) -> RateQuote:
        """Reconstruct a quote from its stored payload."""
        return cls(
            pair=str(raw["pair"]),
            rate=Decimal(str(raw["rate"])),
            fetched_at=float(raw["fetched_at"]),  # type: ignore[arg-type]
            source=str(raw["source"]),
        )


__all__ = ["RateQuote"]

"""Service-side models for relay billing.

Contains the configuration carrier and metadata/audit code constants used
by :mod:`lexigram.ai.governance.relay_billing.service`.  Value types that
cross package boundaries live in the contracts package; this module holds
only governance-internal configuration and codes.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "DEFAULT_CURRENCY",
    "USAGE_MISSING",
    "RelayBillingConfig",
]

DEFAULT_CURRENCY = "USD"
"""Default ISO currency code for relay charges."""

USAGE_MISSING = "usage_missing"
"""Loss/metadata code recorded when a settlement has no usage object."""


@dataclass(frozen=True, slots=True)
class RelayBillingConfig:
    """Configuration for the relay billing lifecycle service.

    Attributes:
        currency: ISO currency code used for reservation and settled
            charges.  Defaults to ``USD``.
        latency_units: Structured event latency unit; reserved for
            future audit-event emission.
    """

    currency: str = DEFAULT_CURRENCY
    latency_units: str = "ms"
    metadata_codes: tuple[str, ...] = (USAGE_MISSING,)

    def __post_init__(self) -> None:
        """Reject an empty currency code."""
        if not self.currency:
            raise ValueError("currency must be non-empty")

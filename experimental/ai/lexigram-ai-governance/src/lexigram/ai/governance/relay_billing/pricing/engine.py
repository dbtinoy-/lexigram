"""Relay pricing engine over configured price snapshots.

Computes per-dimension relay charges from normalized ``RelayUsage`` and
configured price snapshots.  All arithmetic uses non-negative ``Decimal``
with explicit per-dimension rounding; every safety violation returns a
``RelayBillingError`` instead of clamping silently.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from lexigram.ai.governance.relay_billing.pricing.parser import (
    _ALLOWED_DIMENSION_NAMES,
    DEFAULT_MAX_TOKENS,
    DEFAULT_SCALE,
    _syntax_error,
    evaluate_expression,
)
from lexigram.contracts.ai.governance import (
    RelayBillingError,
    RelayChargeBreakdown,
    RelayPriceEstimatorProtocol,
    charge_overflow,
    invalid_usage,
    unknown_price,
)
from lexigram.contracts.ai.relay import RelayUsage
from lexigram.contracts.core.result import Err, Ok, Result

__all__ = [
    "BREAKDOWN_FIELDS",
    "DEFAULT_MAX_CHARGE",
    "PriceSnapshot",
    "RelayPricingEngine",
]

BREAKDOWN_FIELDS = (
    "prompt",
    "cached_prompt",
    "completion",
    "reasoning",
    "audio_input",
    "audio_output",
    "image",
)

_DIMENSION_TO_USAGE = {
    "prompt": "prompt_tokens",
    "cached_prompt": "cache_read_tokens",
    "completion": "completion_tokens",
    "reasoning": "reasoning_tokens",
    "audio_input": "audio_input_tokens",
    "audio_output": "audio_output_tokens",
    "image": "image_tokens",
}

DEFAULT_MAX_CHARGE = Decimal("1_000_000")
_PER_1M = Decimal(1_000_000)


@dataclass(frozen=True, slots=True)
class PriceSnapshot:
    """Configured per-dimension price expressions for one model.

    Each expression is evaluated against the named usage dimensions of
    ``RelayUsage``, e.g. ``"prompt_tokens * 0.0000025"``.  A dimension
    without an expression contributes zero while remaining present in
    the audit breakdown.

    Attributes:
        expressions: Mapping of breakdown field name to expression string.
    """

    expressions: Mapping[str, str]

    def __post_init__(self) -> None:
        """Validate dimension names and expression syntax."""
        unknown = set(self.expressions) - set(BREAKDOWN_FIELDS)
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"unknown price dimensions: {names}")
        for field_name, expression in self.expressions.items():
            if not expression.strip():
                raise ValueError(f"empty expression for dimension {field_name}")
            if _syntax_error(expression) is not None:
                raise ValueError(
                    f"invalid expression for dimension {field_name}: {expression}"
                )

    @classmethod
    def from_per_1m(cls, prices: Mapping[str, Decimal]) -> PriceSnapshot:
        """Build a snapshot from per-1M-token Decimal prices.

        Args:
            prices: Per-1M-token price per breakdown dimension; missing
                dimensions default to zero.

        Returns:
            A snapshot whose expressions multiply each usage dimension
            by its per-token price.

        Raises:
            ValueError: If a price is negative or a dimension is unknown.
        """
        unknown = set(prices) - set(BREAKDOWN_FIELDS)
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"unknown price dimensions: {names}")
        expressions: dict[str, str] = {}
        for field_name in BREAKDOWN_FIELDS:
            price = prices.get(field_name, Decimal(0))
            if price < 0:
                raise ValueError(f"negative price for dimension {field_name}")
            if price == 0:
                expressions[field_name] = "0"
                continue
            usage_field = _DIMENSION_TO_USAGE[field_name]
            per_token = (price / _PER_1M).normalize()
            expressions[field_name] = f"{usage_field} * {format(per_token, 'f')}"
        return cls(expressions=expressions)


class RelayPricingEngine(RelayPriceEstimatorProtocol):
    """Detailed per-dimension relay price estimator.

    Args:
        price_provider: Callable returning the ``PriceSnapshot`` for a
            ``(model, provider, channel)`` triple, or ``None`` when the
            model has no configured price.
        scale: Default decimal places retained per dimension.
        rounding: Default rounding mode applied per dimension.
        max_charge: Maximum total charge; above it fails closed.
        max_tokens: Integer maximum for any usage dimension.
        dimension_scales: Per-dimension decimal places overrides.
        dimension_roundings: Per-dimension rounding mode overrides.

    Raises:
        ValueError: If *max_charge* or *scale* is negative, or a
            dimension override references an unknown breakdown field.
    """

    def __init__(
        self,
        price_provider: Callable[[str, str, str], PriceSnapshot | None],
        *,
        scale: int = DEFAULT_SCALE,
        rounding: str = ROUND_HALF_UP,
        max_charge: Decimal = DEFAULT_MAX_CHARGE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        dimension_scales: Mapping[str, int] | None = None,
        dimension_roundings: Mapping[str, str] | None = None,
    ) -> None:
        if scale < 0:
            raise ValueError("scale must be non-negative")
        if max_charge < 0:
            raise ValueError("max_charge must be non-negative")
        unknown_scales = set(dimension_scales or {}) - set(BREAKDOWN_FIELDS)
        if unknown_scales:
            names = ", ".join(sorted(unknown_scales))
            raise ValueError(f"unknown dimension scales: {names}")
        unknown_roundings = set(dimension_roundings or {}) - set(BREAKDOWN_FIELDS)
        if unknown_roundings:
            names = ", ".join(sorted(unknown_roundings))
            raise ValueError(f"unknown dimension roundings: {names}")
        self._price_provider = price_provider
        self._scale = scale
        self._rounding = rounding
        self._max_charge = max_charge
        self._max_tokens = max_tokens
        self._dimension_scales = dict(dimension_scales or {})
        self._dimension_roundings = dict(dimension_roundings or {})

    def estimate_charge(
        self,
        model: str,
        usage: RelayUsage,
        *,
        provider: str = "",
        channel: str = "",
    ) -> Result[RelayChargeBreakdown, RelayBillingError]:
        """Compute the per-dimension charge breakdown for *usage*.

        Returns:
            Ok(breakdown) on success, Err(RelayBillingError) on unknown
            prices, negative usage, overflow, or expression failures.
        """
        for name in _ALLOWED_DIMENSION_NAMES:
            if getattr(usage, name) < 0:
                return Err(invalid_usage(message=f"negative usage dimension {name}"))
        snapshot = self._price_provider(model, provider, channel)
        if snapshot is None:
            return Err(
                unknown_price(message=f"no price configured for model {model!r}")
            )
        charges: dict[str, Decimal] = {}
        for field_name in BREAKDOWN_FIELDS:
            expression = snapshot.expressions.get(field_name, "0")
            scale = self._dimension_scales.get(field_name, self._scale)
            rounding = self._dimension_roundings.get(field_name, self._rounding)
            charge = evaluate_expression(
                expression,
                usage,
                scale=scale,
                rounding=rounding,
                max_tokens=self._max_tokens,
            )
            if charge.is_err():
                return Err(charge.unwrap_err())
            charges[field_name] = charge.unwrap()
        total = sum(charges.values(), Decimal(0))
        if total > self._max_charge:
            return Err(
                charge_overflow(
                    message=f"charge {total} exceeds configured maximum {self._max_charge}"
                )
            )
        return Ok(RelayChargeBreakdown(**charges, total=total))

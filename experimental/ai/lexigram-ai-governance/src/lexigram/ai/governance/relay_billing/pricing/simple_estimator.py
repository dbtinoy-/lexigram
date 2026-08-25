"""Simple prompt/completion relay cost estimator.

A minimal :class:`~lexigram.contracts.ai.governance.RelayPriceEstimatorProtocol`
implementation that reuses an existing LLM
:class:`~lexigram.contracts.ai.llm.CostEstimatorProtocol` for pricing; the
detailed relay dimensions are always zero.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, DecimalException

from lexigram.ai.governance.relay_billing.pricing.engine import DEFAULT_MAX_CHARGE
from lexigram.ai.governance.relay_billing.pricing.parser import DEFAULT_SCALE
from lexigram.contracts.ai.governance import (
    RelayBillingError,
    RelayChargeBreakdown,
    RelayPriceEstimatorProtocol,
    charge_overflow,
    invalid_usage,
)
from lexigram.contracts.ai.llm import CostEstimatorProtocol
from lexigram.contracts.ai.relay import RelayUsage
from lexigram.contracts.core.result import Err, Ok, Result

__all__ = ["SimpleCostEstimator"]


class SimpleCostEstimator(RelayPriceEstimatorProtocol):
    """Simple prompt/completion price estimator over ``CostEstimatorProtocol``.

    Priced at the underlying estimator's input and output rates; the
    detailed relay dimensions are always zero.  Unknown models yield a
    zero charge, matching the estimator's unknown-model-zero policy.

    Args:
        estimator: Existing LLM cost estimator reused for the simple path.
        scale: Decimal places retained on each part of the charge.
        rounding: Rounding mode applied to each part of the charge.
        max_charge: Maximum total charge; above it fails closed.
    """

    def __init__(
        self,
        estimator: CostEstimatorProtocol,
        *,
        scale: int = DEFAULT_SCALE,
        rounding: str = ROUND_HALF_UP,
        max_charge: Decimal = DEFAULT_MAX_CHARGE,
    ) -> None:
        if scale < 0:
            raise ValueError("scale must be non-negative")
        if max_charge < 0:
            raise ValueError("max_charge must be non-negative")
        self._estimator = estimator
        self._scale = scale
        self._rounding = rounding
        self._max_charge = max_charge

    def estimate_charge(
        self,
        model: str,
        usage: RelayUsage,
        *,
        provider: str = "",
        channel: str = "",
    ) -> Result[RelayChargeBreakdown, RelayBillingError]:
        """Estimate prompt and completion charges from the LLM estimator."""
        provider_arg = provider or None
        try:
            prompt_cost = float(
                self._estimator.estimate_cost(
                    model,
                    usage.prompt_tokens,
                    provider_arg,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=0,
                )
            )
            completion_cost = float(
                self._estimator.estimate_cost(
                    model,
                    usage.completion_tokens,
                    provider_arg,
                    prompt_tokens=0,
                    completion_tokens=usage.completion_tokens,
                )
            )
        except (TypeError, ValueError, OverflowError) as exc:
            return Err(invalid_usage(message=f"estimator failed: {exc}"))
        prompt = Decimal(str(prompt_cost))
        completion = Decimal(str(completion_cost))
        if not prompt.is_finite() or not completion.is_finite():
            return Err(invalid_usage(message="estimator returned a non-finite cost"))
        if prompt < 0 or completion < 0:
            return Err(invalid_usage(message="estimator returned a negative cost"))
        quantum = Decimal(1).scaleb(-self._scale)
        try:
            prompt = prompt.quantize(quantum, rounding=self._rounding)
            completion = completion.quantize(quantum, rounding=self._rounding)
        except DecimalException:
            return Err(invalid_usage(message="charge rounding failed"))
        zero = Decimal(0)
        total = prompt + completion
        if total > self._max_charge:
            return Err(
                charge_overflow(
                    message=f"charge {total} exceeds configured maximum {self._max_charge}"
                )
            )
        return Ok(
            RelayChargeBreakdown(
                prompt=prompt,
                cached_prompt=zero,
                completion=completion,
                reasoning=zero,
                audio_input=zero,
                audio_output=zero,
                image=zero,
                total=total,
            )
        )

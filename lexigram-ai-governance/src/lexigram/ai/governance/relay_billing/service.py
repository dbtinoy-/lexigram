"""Relay billing lifecycle service.

Implements :class:`~lexigram.contracts.ai.governance.RelayBillingProtocol`
for one relay request: pre-consume admission, settle-once settlement, and
release.  Prompt estimation, scope reservations, and per-dimension pricing
are delegated to the reservation manager and the injected price estimator;
actual usage always comes from ``RelayConvertResult``, never from an
estimate.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from lexigram.ai.governance.relay_billing.models import DEFAULT_CURRENCY, USAGE_MISSING
from lexigram.ai.governance.relay_billing.reservations import (
    RelayReservationManager,
    estimate_prompt_tokens,
    requested_max_output_tokens,
)
from lexigram.contracts.ai.governance import (
    RelayBillingError,
    RelayBillingProtocol,
    RelayUsageRecord,
    RelayUsageScope,
    RelayUsageStoreProtocol,
    billing_store_unavailable,
)
from lexigram.contracts.ai.relay import RelayUsage
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.identity import ambient as identity
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.ai.governance import (
        RelayPriceEstimatorProtocol,
        RelayUsageReservation,
    )
    from lexigram.contracts.ai.llm import TokenCounterProtocol
    from lexigram.contracts.ai.relay import RelayConvertResult, RelayRequestPayload

logger = get_logger(__name__)

__all__ = [
    "RelayBillingService",
    "RelayCostAdapter",
]


class RelayBillingService(RelayBillingProtocol):
    """Billing lifecycle for one relay gateway request.

    Args:
        reservation_manager: Manager holding per-scope admission quotas.
        estimator: Price estimator computing reservation and settled
            charges from normalized usage.
        store: Persistence boundary for reservations and settlement
            records.
        token_counter: Optional model-aware token counter for prompt
            estimation.
        currency: ISO currency code for charges.
    """

    def __init__(
        self,
        *,
        reservation_manager: RelayReservationManager,
        estimator: RelayPriceEstimatorProtocol,
        store: RelayUsageStoreProtocol,
        token_counter: TokenCounterProtocol | None = None,
        currency: str = DEFAULT_CURRENCY,
    ) -> None:
        self._manager = reservation_manager
        self._estimator = estimator
        self._store = store
        self._token_counter = token_counter
        self._currency = currency
        # reservation_id -> scope captured at admission time
        self._scopes: dict[str, RelayUsageScope] = {}

    async def pre_consume(
        self,
        request_id: str,
        scope: RelayUsageScope,
        payload: RelayRequestPayload,
    ) -> Result[RelayUsageReservation, RelayBillingError]:
        """Reserve admission capacity for a request before upstream I/O.

        Args:
            request_id: Gateway request identifier.
            scope: Accounting scope of the request.
            payload: Relay request payload used for prompt estimation.

        Returns:
            Ok(reservation) after the reservation is persisted, or
            Err when admission cannot be proven (quota, pricing, or
            persistence failure).  On persistence failure the in-memory
            reservation is released, leaving none behind.
        """
        prompt_tokens = estimate_prompt_tokens(payload, self._token_counter)
        max_output = requested_max_output_tokens(payload)
        estimate_tokens = prompt_tokens + max_output

        estimated_charge = await self._max_charge(scope, prompt_tokens, max_output)
        if estimated_charge.is_err():
            return Err(
                RelayBillingError(
                    code=estimated_charge.unwrap_err().code,
                    message=estimated_charge.unwrap_err().message,
                    request_id=request_id,
                    tenant_id=scope.tenant_id,
                )
            )

        reservation_result = await self._manager.reserve(
            request_id,
            scope,
            estimate_tokens,
            estimated_charge.unwrap(),
        )
        if reservation_result.is_err():
            return Err(reservation_result.unwrap_err())
        reservation = reservation_result.unwrap()

        try:
            await self._store.save_reservation(reservation)
        except Exception as exc:  # noqa: BLE001 - infrastructure boundary
            await self._manager.release(reservation.reservation_id)
            logger.warning(
                "relay_billing_persist_reservation_failed",
                reservation_id=reservation.reservation_id,
                request_id=request_id,
                tenant_id=scope.tenant_id,
                error=str(exc),
            )
            return Err(
                billing_store_unavailable(
                    message="cannot persist reservation; admission rejected",
                    request_id=request_id,
                    tenant_id=scope.tenant_id,
                )
            )

        self._scopes[reservation.reservation_id] = scope
        return Ok(reservation)

    async def _max_charge(
        self,
        scope: RelayUsageScope,
        prompt_tokens: int,
        max_output: int,
    ) -> Result[Decimal, RelayBillingError]:
        """Return the maximum reservation charge for the estimate.

        Args:
            scope: Accounting scope of the request.
            prompt_tokens: Estimated prompt tokens.
            max_output: Requested max output tokens.

        Returns:
            Ok(worst-case charge) for the full completion budget, or Err
            when pricing is unavailable for the model.
        """
        usage = RelayUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=max_output,
        )
        result = self._estimator.estimate_charge(
            scope.model,
            usage,
            provider=scope.provider,
            channel=scope.channel,
        )
        if result.is_err():
            return Err(
                RelayBillingError(
                    code=result.unwrap_err().code,
                    message=result.unwrap_err().message,
                    tenant_id=scope.tenant_id,
                )
            )
        return Ok(result.unwrap().total)

    async def settle(
        self,
        reservation: RelayUsageReservation,
        result: RelayConvertResult,
        *,
        status: Literal["completed", "failed", "cancelled", "truncated"],
    ) -> Result[RelayUsageRecord, RelayBillingError]:
        """Settle actual usage for a request attempt exactly once.

        The final usage comes from ``result.usage``.  The attempt key is
        the reservation identifier, so retries with the same reservation
        map to the same ``(request_id, attempt_id)`` record and never
        charge twice.

        Args:
            reservation: The pre-consume reservation for this attempt.
            result: Converter result carrying the normalized final usage.
            status: Terminal status of the attempt.

        Returns:
            Ok(record) with the settled usage and charge, or Err when
            pricing or persistence fails.  A missing final usage object
            settles as zero usage with an explicit ``usage_missing``
            metadata code; the prompt estimate is never billed.
        """
        scope = self._scopes.get(reservation.reservation_id)
        if scope is None:
            return Err(
                RelayBillingError(
                    code="invalid_usage",
                    message="settle without pre_consume admission",
                    request_id=reservation.request_id,
                )
            )
        usage, loss_codes = self._usage_for_result(result)

        charge_result = self._estimator.estimate_charge(
            scope.model,
            usage,
            provider=scope.provider,
            channel=scope.channel,
        )
        if charge_result.is_err():
            return Err(
                RelayBillingError(
                    code=charge_result.unwrap_err().code,
                    message=charge_result.unwrap_err().message,
                    request_id=reservation.request_id,
                    tenant_id=scope.tenant_id,
                )
            )
        charge = charge_result.unwrap().total

        record = RelayUsageRecord(
            request_id=reservation.request_id,
            attempt_id=reservation.reservation_id,
            scope=scope,
            usage=usage,
            charge=charge,
            currency=self._currency,
            status=status,
            converter_id=result.converter_id,
            loss_codes=loss_codes,
        )

        try:
            stored = await self._store.settle_once(record)
        except Exception as exc:  # noqa: BLE001 - infrastructure boundary
            logger.warning(
                "relay_billing_settle_store_failed",
                request_id=reservation.request_id,
                error=str(exc),
            )
            return Err(
                billing_store_unavailable(
                    message="could not persist settlement",
                    request_id=reservation.request_id,
                    tenant_id=scope.tenant_id,
                )
            )

        await self._manager.settle(reservation.reservation_id)
        logger.info(
            "relay_billing_settled",
            request_id=reservation.request_id,
            attempt_id=stored.attempt_id,
            charge=str(stored.charge),
            tokens=usage.total_tokens,
        )
        return Ok(stored)

    def _usage_for_result(
        self,
        result: RelayConvertResult,
    ) -> tuple[RelayUsage, tuple[str, ...]]:
        """Extract the usage and loss codes to bill for an attempt.

        ``completed``, ``cancelled``, and ``truncated`` bill observed
        usage; ``failed`` bills only provider-reported usage.  A missing
        usage object always settles as zero usage with an explicit
        ``usage_missing`` loss code.

        Args:
            result: Converter result carrying normalized usage.

        Returns:
            Billed usage and the loss codes to attach to the record.
        """
        usage = result.usage or RelayUsage()
        loss_codes = tuple(item.reason for item in result.losses)
        if result.usage is None:
            loss_codes = (*loss_codes, USAGE_MISSING)
        return usage, loss_codes

    async def release(self, reservation: RelayUsageReservation) -> None:
        """Release a reservation when the request never reached upstream.

        Args:
            reservation: The reservation to release.
        """
        await self._manager.release(reservation.reservation_id)
        await self._store.release(reservation.reservation_id)
        self._scopes.pop(reservation.reservation_id, None)


class RelayCostAdapter:
    """Cost-tracking adapter over the relay billing store.

    Preserves compatibility with :class:`CostTrackingProtocol` callers:
    :meth:`track_cost` records a completed, generic usage record and
    :meth:`get_budget` delegates to a configured tenant/account budget
    resolver.  Existing governance callers keep working without importing
    relay types.

    Args:
        store: Persistence boundary for settled records.
        currency: Default currency code.
        budget: Optional callable returning the remaining budget for a
            user; ``None`` means an unbounded budget of 0.
    """

    def __init__(
        self,
        *,
        store: RelayUsageStoreProtocol,
        currency: str = DEFAULT_CURRENCY,
        budget: Callable[[str | None], Decimal] | None = None,
    ) -> None:
        self._store = store
        self._currency = currency
        self._budget = budget

    async def track_cost(
        self,
        cost: float,
        model: str,
        user_id: str | None = None,
        *,
        tenant_id: str = "global",
    ) -> None:
        """Track a cost by recording a completed generic usage record.

        Args:
            cost: USD cost to record.
            model: Model the cost belongs to.
            user_id: User the cost belongs to, when applicable.
            tenant_id: Tenant the charge is attributed to.
        """
        request_id = f"adapter:{identity.new_uuid()}"
        record = RelayUsageRecord(
            request_id=request_id,
            attempt_id=request_id,
            scope=RelayUsageScope(
                tenant_id=tenant_id,
                model=model,
                user_id=user_id or None,
            ),
            usage=RelayUsage(),
            charge=Decimal(str(cost)),
            currency=self._currency,
            status="completed",
        )
        await self._store.settle_once(record)

    async def get_budget(self, user_id: str | None = None) -> Decimal:
        """Return the configured remaining budget.

        Args:
            user_id: User the budget applies to.

        Returns:
            The resolver's remaining budget, or ``0`` when unconfigured.
        """
        if self._budget is None:
            return Decimal(0)
        return self._budget(user_id)

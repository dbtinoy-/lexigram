"""DI registrations and gateway hooks for relay billing.

The governance provider root registers the billing hierarchy by contract
during ``register()`` and swaps the concrete lifecycle in ``boot()``:

- :func:`register_relay_billing` binds ``RelayBillingProtocol`` to a
  no-op admission policy (:class:`NoopRelayBilling`) when billing is
  disabled, and to the placeholder instances the boot phase replaces
  when billing is enabled.
- :func:`boot_relay_billing` resolves the token counter, price
  estimator, event bus, audit store, database, and reservation manager
  through their contracts, builds ``RelayBillingService``, and rebinds
  it behind :class:`RelayBillingHooks` so audit/budget emission and
  gateway calls share one protocol binding.

Nothing in this module imports gateway or converter implementations.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import time
from typing import TYPE_CHECKING, Literal

from lexigram.ai.governance import GovernanceConfig
from lexigram.ai.governance.budget import BudgetTracker
from lexigram.ai.governance.relay_billing.models import RelayBillingConfig
from lexigram.ai.governance.relay_billing.persistence import DatabaseRelayUsageStore
from lexigram.ai.governance.relay_billing.pricing import SimpleCostEstimator
from lexigram.ai.governance.relay_billing.reservations import RelayReservationManager
from lexigram.ai.governance.relay_billing.service import RelayBillingService
from lexigram.contracts.ai.governance import (
    AIAuditEvent,
    AIAuditStoreProtocol,
    AuditEventType,
    RelayBillingError,
    RelayBillingProtocol,
    RelayPriceEstimatorProtocol,
    RelayUsageRecord,
    RelayUsageReservation,
    RelayUsageScope,
    RelayUsageStoreProtocol,
)
from lexigram.contracts.ai.llm import (
    CostEstimatorProtocol,
    TokenCounterProtocol,
)
from lexigram.contracts.ai.relay import (
    RelayConvertResult,
    RelayRequestPayload,
    RelayUsage,
)
from lexigram.contracts.core.result import Ok, Result
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.contracts.events import EventBusProtocol
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )

logger = get_logger(__name__)

__all__ = [
    "NoopRelayBilling",
    "RelayBillingHooks",
    "boot_relay_billing",
    "register_relay_billing",
]


class NoopRelayBilling(RelayBillingProtocol):
    """Admit-everything billing policy used when billing is disabled.

    ``pre_consume`` always grants a zero-cost reservation, ``settle``
    returns a zero-charge record built from the converter result, and
    ``release`` does nothing.  The gateway can therefore drive the same
    protocol-shaped code path whether or not billing is enabled.

    Attributes:
        _scopes: Reservation identifier to scope map captured at
            admission time (mirrors the real service for settle).
    """

    def __init__(self) -> None:
        """Bind an empty scope map."""
        self._scopes: dict[str, RelayUsageScope] = {}

    async def pre_consume(
        self,
        request_id: str,
        scope: RelayUsageScope,
        payload: RelayRequestPayload,
    ) -> Result[RelayUsageReservation, RelayBillingError]:
        """Always admit with a zero-cost no-op reservation.

        Args:
            request_id: Gateway request identifier.
            scope: Accounting scope of the request.
            payload: Relay request payload (unused by the no-op policy).

        Returns:
            ``Ok`` with a non-expiring zero-cost reservation.
        """
        del payload
        reservation_id = f"noop:{request_id}"
        self._scopes[reservation_id] = scope
        return Ok(
            RelayUsageReservation(
                reservation_id=reservation_id,
                request_id=request_id,
                estimated_tokens=0,
                estimated_charge=Decimal(0),
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
        )

    async def settle(
        self,
        reservation: RelayUsageReservation,
        result: RelayConvertResult,
        *,
        status: Literal["completed", "failed", "cancelled", "truncated"],
    ) -> Result[RelayUsageRecord, RelayBillingError]:
        """Return a zero-charge record for the attempt.

        Args:
            reservation: The no-op reservation issued by
                :meth:`pre_consume`.
            result: Converter result carrying the normalized usage.
            status: Terminal status of the attempt.

        Returns:
            ``Ok`` with a zero-charge record (billing disabled).
        """
        scope = self._scopes.get(reservation.reservation_id) or RelayUsageScope(
            tenant_id=reservation.request_id,
        )
        return Ok(
            RelayUsageRecord(
                request_id=reservation.request_id,
                attempt_id=reservation.reservation_id,
                scope=scope,
                usage=result.usage or RelayUsage(),
                charge=Decimal(0),
                currency="USD",
                status=status,
                converter_id=result.converter_id,
                loss_codes=tuple(loss.reason for loss in result.losses),
            )
        )

    async def release(self, reservation: RelayUsageReservation) -> None:
        """Do nothing; the no-op policy holds no capacity."""
        self._scopes.pop(reservation.reservation_id, None)


_TERMINAL_AUDIT_STATUS = {
    "completed": "success",
    "failed": "error",
    "truncated": "truncated",
    "cancelled": "cancelled",
}


class RelayBillingHooks(RelayBillingProtocol):
    """Billing protocol wrapper that emits audit and budget events.

    Delegates the lifecycle to the inner ``RelayBillingProtocol`` and,
    after a successful settlement, records a redacted
    :class:`~lexigram.contracts.ai.governance.AIAuditEvent` through the
    optional audit store and feeds the settled usage into the optional
    budget tracker (whose threshold alerts flow out over the event bus).
    Both emissions happen on a background task so the caller never waits
    on the persistence store.

    Args:
        delegate: The inner billing lifecycle (or a no-op policy).
        audit_store: Audit event store; ``None`` disables audit events.
        budget_tracker: Budget tracker emitting threshold alerts over
            its event bus; ``None`` disables budget alerts.
    """

    def __init__(
        self,
        delegate: RelayBillingProtocol,
        *,
        audit_store: AIAuditStoreProtocol | None = None,
        budget_tracker: BudgetTracker | None = None,
    ) -> None:
        """Bind the wrapper to the inner lifecycle and observers."""
        self._delegate = delegate
        self._audit_store = audit_store
        self._budget_tracker = budget_tracker
        self._started: dict[str, float] = {}
        self._background_tasks: set[asyncio.Task[object]] = set()

    async def pre_consume(
        self,
        request_id: str,
        scope: RelayUsageScope,
        payload: RelayRequestPayload,
    ) -> Result[RelayUsageReservation, RelayBillingError]:
        """Start a latency window and delegate admission to the service.

        Args:
            request_id: Gateway request identifier.
            scope: Accounting scope of the request.
            payload: Relay request payload used for prompt estimation.

        Returns:
            The inner admission result.
        """
        result = await self._delegate.pre_consume(request_id, scope, payload)
        if result.is_ok():
            reservation = result.unwrap()
            self._started[reservation.reservation_id] = time.monotonic()
        return result

    async def settle(
        self,
        reservation: RelayUsageReservation,
        result: RelayConvertResult,
        *,
        status: Literal["completed", "failed", "cancelled", "truncated"],
    ) -> Result[RelayUsageRecord, RelayBillingError]:
        """Settle through the inner service and emit observer events.

        Args:
            reservation: The pre-consume reservation for this attempt.
            result: Converter result carrying the normalized usage.
            status: Terminal status of the attempt.

        Returns:
            The settled record, or the inner error when settlement fails.
            Observer events are scheduled only after a successful settle.
        """
        outcome = await self._delegate.settle(
            reservation,
            result,
            status=status,
        )
        if outcome.is_err():
            return outcome
        record = outcome.unwrap()
        latency_ms = self._started.pop(reservation.reservation_id, None)
        if latency_ms is not None:
            duration = max(0.0, time.monotonic() - latency_ms) * 1000.0
        else:
            duration = 0.0
        self._schedule(self._emit(record, duration))
        return outcome

    async def release(self, reservation: RelayUsageReservation) -> None:
        """Release through the inner service and drop latency state."""
        self._started.pop(reservation.reservation_id, None)
        await self._delegate.release(reservation)

    def _schedule(self, coro: object) -> None:
        """Start *coro* as a tracked background task (fire and forget)."""
        loop = asyncio.get_running_loop()
        task: asyncio.Task[object] = loop.create_task(coro)  # type: ignore[arg-type]
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _emit(
        self,
        record: RelayUsageRecord,
        latency_ms: float,
    ) -> None:
        """Record the audit event and budget usage for one settlement.

        Args:
            record: The settled usage record.
            latency_ms: Measured request latency, or ``0.0`` when unknown.
        """
        scope = record.scope
        if self._audit_store is not None:
            await self._audit_store.record(
                AIAuditEvent(
                    event_type=AuditEventType.LLM_CALL,
                    model=scope.model,
                    provider=scope.provider,
                    user_id=scope.user_id,
                    status=_TERMINAL_AUDIT_STATUS.get(record.status, "success"),
                    tokens=record.usage.total_tokens,
                    cost=float(record.charge),
                    latency_ms=round(latency_ms, 2),
                    metadata={
                        "request_id": record.request_id,
                        "attempt_id": record.attempt_id,
                        "tenant_id": scope.tenant_id,
                        "account_id": scope.account_id,
                        "channel": scope.channel,
                        "converter_id": record.converter_id,
                        "loss_codes": list(record.loss_codes),
                        "currency": record.currency,
                    },
                )
            )
        if self._budget_tracker is not None:
            await self._budget_tracker.record_usage(
                scope.model,
                record.usage.total_tokens,
                float(record.charge),
                tenant_id=scope.tenant_id or None,
            )


def register_relay_billing(
    container: ContainerRegistrarProtocol,
    config: object,
) -> None:
    """Register the relay billing hierarchy by contract.

    The root always exposes ``RelayBillingProtocol`` so the gateway can
    resolve an admission policy even when billing is disabled.  When
    billing is enabled, the concrete lifecycle is built from resolved
    contracts during :func:`boot_relay_billing`; until then the no-op
    instance is the registered singleton the boot phase rebinds.

    Args:
        container: The container registrar to bind into.
        config: Governance configuration; ``enabled`` gates billing.
    """
    relay_config = RelayBillingConfig()
    container.singleton(RelayBillingConfig, relay_config)
    if not isinstance(config, GovernanceConfig) or not config.enabled:
        container.singleton(RelayBillingProtocol, NoopRelayBilling())
        logger.info("relay_billing_disabled", reason="governance disabled")
        return

    container.singleton(RelayReservationManager, RelayReservationManager())
    container.singleton(RelayBillingProtocol, NoopRelayBilling())
    logger.info("relay_billing_registered")


async def boot_relay_billing(
    container: BootContainerProtocol,
    config: object,
) -> None:
    """Build the live relay billing service and rebind it into the container.

    Resolution is contract-scoped (database, estimator, token counter,
    audit store, reservation manager).  When a required contract is
    missing (for example no database backend), the no-op admission
    policy from :func:`register_relay_billing` remains bound and a
    startup diagnostic is logged so the missing dependency is
    discoverable.

    Args:
        container: The boot container used to resolve contracts.
        config: Relay configuration driving the bootstrap.
    """
    if not isinstance(config, GovernanceConfig) or not config.enabled:
        logger.info("relay_billing_boot_skipped", reason="governance disabled")
        return

    database = await container.resolve_optional(DatabaseProviderProtocol)
    estimator = await container.resolve_optional(RelayPriceEstimatorProtocol)
    token_counter = await container.resolve_optional(TokenCounterProtocol)
    event_bus = await container.resolve_optional(EventBusProtocol)

    if database is None:
        logger.warning(
            "relay_billing_missing_dependency",
            missing="DatabaseProviderProtocol",
        )
        return
    if estimator is None:
        cost_estimator = await container.resolve_optional(CostEstimatorProtocol)
        if cost_estimator is not None:
            estimator = SimpleCostEstimator(cost_estimator)
    if estimator is None:
        logger.warning(
            "relay_billing_missing_dependency",
            missing="RelayPriceEstimatorProtocol",
        )
        return

    store: RelayUsageStoreProtocol = DatabaseRelayUsageStore(database)
    manager = await container.resolve(RelayReservationManager)
    relay_config = await container.resolve(RelayBillingConfig)
    budget_tracker = (
        BudgetTracker(
            tpm_limit=config.tpm_limit,
            cost_limit_hourly=config.monthly_budget,
            event_bus=event_bus,
        )
        if event_bus is not None
        else None
    )
    audit_store = await container.resolve_optional(AIAuditStoreProtocol)

    billing = RelayBillingService(
        reservation_manager=manager,
        estimator=estimator,
        store=store,
        token_counter=token_counter,
        currency=relay_config.currency,
    )
    hooks = RelayBillingHooks(
        billing,
        audit_store=audit_store,
        budget_tracker=budget_tracker,
    )
    container.bind(RelayBillingProtocol, hooks)  # type: ignore[type-abstract]
    logger.info("relay_billing_booted")

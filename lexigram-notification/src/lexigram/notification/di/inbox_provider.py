"""InboxProvider — DI provider for the user inbox subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core import HealthCheckResult, HealthStatus, ProviderPriority
from lexigram.contracts.notification.inbox import InboxStoreProtocol
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)


class InboxProvider(Provider):
    """Register the inbox store and service into the DI container.

    Registers :class:`~lexigram.contracts.notification.inbox.InboxStoreProtocol`
    (defaulting to :class:`~lexigram.notification.inbox_memory.InMemoryInboxStore`)
    and :class:`~lexigram.notification.inbox_service.InboxService` for constructor
    injection.
    """

    name = "inbox"
    priority = ProviderPriority.INFRASTRUCTURE

    def __init__(self) -> None:
        super().__init__()
        self._store: InboxStoreProtocol | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind inbox store and service into the container.

        Args:
            container: DI registrar received from the framework.
        """
        from lexigram.notification.inbox.memory import InMemoryInboxStore
        from lexigram.notification.inbox.service import InboxService

        container.singleton(InboxStoreProtocol, InMemoryInboxStore)
        container.singleton(InboxService, InboxService)
        logger.info("inbox_registered", backend="memory")

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve the inbox store for health checking.

        Args:
            container: DI resolver used to obtain the registered store.
        """
        from lexigram.notification.inbox.service import InboxService

        self._store = await container.resolve(InboxStoreProtocol)
        await container.resolve(InboxService)
        logger.info("inbox_booted")

    async def shutdown(self) -> None:
        """Release store reference on shutdown."""
        self._store = None

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Delegate health check to the registered inbox store.

        Returns degraded status before :meth:`boot` has been called.

        Args:
            timeout: Max seconds to wait for the store health probe.

        Returns:
            :class:`~lexigram.contracts.core.HealthCheckResult`.
        """
        if self._store is None:
            return HealthCheckResult(
                component="inbox",
                status=HealthStatus.DEGRADED,
                message="inbox store not initialized",
            )

        store_result = await self._store.health_check(timeout=timeout)
        return HealthCheckResult(
            component="inbox",
            status=store_result.status,
            message=store_result.message,
            details=store_result.details,
            error=store_result.error,
            duration_ms=store_result.duration_ms,
        )


__all__ = ["InboxProvider"]

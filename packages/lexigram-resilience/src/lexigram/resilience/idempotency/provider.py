"""DI provider for the in-memory idempotency store.

Registers InMemoryIdempotencyStore as the IdempotencyStoreProtocol singleton.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core.idempotency import IdempotencyStoreProtocol
from lexigram.di.provider import Provider, ProviderPriority
from lexigram.logging import get_logger
from lexigram.resilience.config import IdempotencyConfig
from lexigram.resilience.idempotency.store import InMemoryIdempotencyStore

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)


class IdempotencyProvider(Provider):
    """DI provider for the in-memory idempotency store.

    Registers InMemoryIdempotencyStore as the IdempotencyStoreProtocol singleton
    with optional capacity and cleanup configuration.

    Args:
        config: Idempotency configuration. Defaults to IdempotencyConfig().
    """

    name = "idempotency"
    priority = ProviderPriority.INFRASTRUCTURE

    def __init__(self, config: IdempotencyConfig | None = None) -> None:
        """Create the IdempotencyProvider.

        Args:
            config: Idempotency configuration. Defaults to IdempotencyConfig().
        """
        super().__init__()
        self._config = config or IdempotencyConfig()
        self._store: InMemoryIdempotencyStore | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind IdempotencyStoreProtocol to an InMemoryIdempotencyStore singleton.

        Args:
            container: The DI container registrar.
        """
        auto_cleanup_interval = (
            self._config.cleanup_interval if self._config.auto_cleanup else None
        )
        self._store = InMemoryIdempotencyStore(
            auto_cleanup_interval=auto_cleanup_interval,
            max_entries=self._config.max_entries,
        )
        container.singleton(IdempotencyStoreProtocol, instance=self._store)
        logger.debug(
            "idempotency.provider.registered",
            max_entries=self._config.max_entries,
            auto_cleanup=self._config.auto_cleanup,
        )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """No boot-time work required for the in-memory store.

        Args:
            container: The DI container resolver.
        """

    async def shutdown(self) -> None:
        """Stop the background cleanup task if running."""
        if self._store is not None:
            await self._store.stop_auto_cleanup()
            self._store = None
        logger.debug("idempotency.provider.shutdown")


__all__ = ["IdempotencyProvider"]

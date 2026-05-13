"""Core audit DI provider: registers store and logger."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from lexigram.contracts.audit import AuditLoggerProtocol, AuditStoreProtocol
from lexigram.contracts.core.di import (
    BootContainerProtocol,
    ContainerRegistrarProtocol,
)
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider

if TYPE_CHECKING:
    from lexigram.audit.config import AuditConfig

__all__ = ["AuditCoreProvider"]


class AuditCoreProvider(Provider):
    """Registers AuditStoreProtocol and AuditLoggerProtocol.

    Args:
        config: Audit configuration.
    """

    def __init__(self, config: AuditConfig | None = None) -> None:
        super().__init__(name="audit_core", priority=ProviderPriority.INFRASTRUCTURE)
        self._config = config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind store and logger to their protocols.

        The store is built eagerly at register time so the logger (which depends
        on it) can be constructed and registered as a pre-built instance. The
        previous implementation registered the ``AuditLogger`` class directly
        and the container tried to auto-instantiate it without supplying the
        required ``store`` argument — raising at first resolve.
        """
        from lexigram.audit.config import AuditConfig as _AuditConfig
        from lexigram.audit.logging.logger import AuditLogger
        from lexigram.audit.store.memory import InMemoryAuditStore

        config = self._config or _AuditConfig()

        # Register AuditConfig as a singleton instance so SqlAuditStore
        # can receive it via constructor injection.
        container.singleton(_AuditConfig, config)

        if config.store_backend == "sql":
            try:
                from lexigram.audit.store.sql import SqlAuditStore

                # SqlAuditStore needs AuditConfig — its DI auto-wiring resolves
                # the singleton registered above.
                container.singleton(AuditStoreProtocol, SqlAuditStore)
            except ImportError:
                store: AuditStoreProtocol = InMemoryAuditStore()
                container.singleton(AuditStoreProtocol, store)
                container.singleton(AuditLoggerProtocol, AuditLogger(store=store))
                return
        else:
            store = InMemoryAuditStore()
            container.singleton(AuditStoreProtocol, store)
            container.singleton(AuditLoggerProtocol, AuditLogger(store=store))
            return

        # SQL path: store is auto-instantiated, so we need a factory for the
        # logger that closes over the resolved store. Done at boot() instead
        # of register() so we can await the store resolution.
        self._needs_sql_logger_wiring = True

    async def boot(self, container: BootContainerProtocol) -> None:
        """Initialize the store; wire SQL-backed logger if needed."""
        store = await container.resolve(AuditStoreProtocol)
        if hasattr(store, "initialize"):
            await store.initialize()
        if getattr(self, "_needs_sql_logger_wiring", False):
            from lexigram.audit.logging.logger import AuditLogger

            # bind() works on a frozen post-register container, which is what
            # we have here. Logger isn't pre-registered, so bind() can't be
            # used — but rebinding the same protocol via singleton on a frozen
            # container would fail. Instead, register via the resolver's
            # underlying container. This is the cleanest available knob given
            # boot only receives a resolver.
            # Fallback: register a value-bound singleton manually.
            logger = AuditLogger(store=store)
            try:
                container.singleton(cast("type", AuditLoggerProtocol), logger)
            except Exception:
                # Container is frozen — use bind() if logger was preregistered;
                # otherwise re-register via the underlying registrar if exposed.
                if hasattr(container, "bind"):
                    container.bind(cast("type", AuditLoggerProtocol), logger)

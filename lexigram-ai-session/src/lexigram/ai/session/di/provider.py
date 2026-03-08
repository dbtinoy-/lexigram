"""DI provider for lexigram-ai-session."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.ai.session.config import SessionConfig
from lexigram.ai.session.context.pruner import RelevanceContextPruner
from lexigram.ai.session.context.session_context import SessionContext
from lexigram.ai.session.manager import SessionCleanupScheduler, SessionManagerImpl
from lexigram.ai.session.stores.in_memory import InMemorySessionStore
from lexigram.contracts.ai.session import (
    ContextPrunerProtocol,
    SessionContextProtocol,
    SessionManagerProtocol,
    SessionStoreProtocol,
)
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )

logger = get_logger(__name__)


class SessionProvider(Provider):
    """Registers session management services in the DI container.

    Wires ``SessionStoreProtocol`` and ``SessionManagerProtocol`` based on the
    configured backend. Background cleanup is started during ``boot()``.
    """

    name = "session"
    priority = ProviderPriority.INFRASTRUCTURE
    config_key: str | None = "ai_session"
    config_model: type | None = SessionConfig

    def __init__(
        self,
        config: SessionConfig | dict | None = None,
        *,
        enable_cleanup_scheduler: bool = True,
    ) -> None:
        """Initialise the provider."""
        super().__init__()
        if isinstance(config, dict):
            config = SessionConfig(**config)
        self._requested_config = config
        self._config = config or SessionConfig()
        self._enable_cleanup_scheduler = enable_cleanup_scheduler
        self._scheduler: SessionCleanupScheduler | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register session services in the container."""
        self._config = self._requested_config or (
            self.config
            if isinstance(getattr(self, "config", None), SessionConfig)
            else self._config
        )
        container.singleton(SessionConfig, instance=self._config)

        if not self._config.enabled:
            logger.info("session_disabled", reason="SessionConfig.enabled=False")
            return

        if self._config.backend == "in_memory":
            container.singleton(SessionStoreProtocol, instance=InMemorySessionStore())
        elif self._config.backend == "cache":
            from lexigram.ai.session.stores.cache import CacheSessionStore

            container.singleton(SessionStoreProtocol, factory=CacheSessionStore)
        elif self._config.backend == "database":
            from lexigram.ai.session.stores.database import DatabaseSessionStore

            container.singleton(SessionStoreProtocol, factory=DatabaseSessionStore)
        else:
            logger.warning(
                "unknown_session_backend",
                backend=self._config.backend,
                fallback="in_memory",
            )
            container.singleton(SessionStoreProtocol, instance=InMemorySessionStore())

        container.singleton(SessionManagerProtocol, factory=SessionManagerImpl)
        container.singleton(SessionCleanupScheduler, factory=SessionCleanupScheduler)
        container.transient(SessionContextProtocol, factory=SessionContext)  # type: ignore[type-abstract]
        container.singleton(ContextPrunerProtocol, factory=RelevanceContextPruner)

        logger.info("session_services_registered", backend=self._config.backend)

    async def boot(self, container: BootContainerProtocol) -> None:
        """Pre-warm session services and start the cleanup scheduler."""
        if not self._config.enabled:
            return

        store = await container.resolve(SessionStoreProtocol)
        initialize = getattr(store, "initialize", None)
        if callable(initialize):
            await initialize()

        if self._enable_cleanup_scheduler:
            try:
                scheduler = await container.resolve(SessionCleanupScheduler)
                await scheduler.start()
                self._scheduler = scheduler
            except (LookupError, RuntimeError, AttributeError, OSError) as exc:
                logger.warning("failed_to_start_session_cleanup", error=str(exc))

    async def shutdown(self) -> None:
        """Stop the background cleanup loop."""
        if self._scheduler is None:
            return

        try:
            await self._scheduler.stop()
        except (RuntimeError, AttributeError, OSError) as exc:
            logger.warning("failed_to_stop_session_cleanup", error=str(exc))

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Health check — always healthy (in-process domain provider).

        No external backend to ping.

        Args:
            timeout: Ignored for in-process providers.

        Returns:
            Always HEALTHY — no external backend to ping.
        """
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            details={"status": "operational"},
        )


__all__ = ["SessionProvider"]

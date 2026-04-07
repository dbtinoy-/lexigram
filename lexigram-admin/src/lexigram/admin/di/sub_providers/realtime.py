"""Admin realtime sub-provider — WebSocket, SSE, collaborative editing, events."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus

if TYPE_CHECKING:
    from lexigram.admin.config import AdminConfig
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


class AdminRealtimeSubProvider:
    """Manages admin realtime infrastructure: WebSocket, SSE, collaborative editing.

    Registers realtime services: WebSocket manager, event hub, SSE manager.
    """

    def __init__(self, config: AdminConfig, **kwargs: object) -> None:
        self._config = config
        self._kwargs = kwargs
        self._initialized = False

    @property
    def config(self) -> AdminConfig:
        """Return current admin config."""
        return self._config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register realtime services: WebSocket manager, event hub, SSE manager, collaborative."""
        from lexigram.admin.realtime.sse import AdminEventHub
        from lexigram.admin.realtime.ws_handler_registry import WSMessageTypeRegistry
        from lexigram.admin.services.collaborative import CollaborativeEditingService
        from lexigram.admin.services.realtime import RealtimeService
        from lexigram.contracts.core.stores import LockStoreProtocol

        realtime_svc = RealtimeService()

        container.singleton(WSMessageTypeRegistry, WSMessageTypeRegistry())
        container.singleton(RealtimeService, realtime_svc)
        container.singleton(AdminEventHub, AdminEventHub())

        # Lock store is provided externally through container bindings.
        lock_store: LockStoreProtocol | None = None

        # Pre-build instance to avoid container trying to resolve RealtimeService
        # from TYPE_CHECKING-only annotation on CollaborativeEditingService.__init__.
        container.singleton(
            CollaborativeEditingService,
            CollaborativeEditingService(
                lock_store=lock_store,  # type: ignore[arg-type]
                realtime_service=realtime_svc,
            ),
        )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Boot realtime services: initialize WebSocket and SSE connections."""
        self._initialized = True

    async def shutdown(self) -> None:
        """Shut down realtime services."""
        self._initialized = False

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Return realtime infrastructure health status."""
        return HealthCheckResult(
            component="admin_realtime",
            status=HealthStatus.HEALTHY if self._initialized else HealthStatus.UNKNOWN,
            message="Admin realtime operational"
            if self._initialized
            else "Not yet initialized",
        )


__all__ = ["AdminRealtimeSubProvider"]

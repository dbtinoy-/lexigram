"""Admin realtime sub-provider — WebSocket, SSE, collaborative editing, events."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.config import AdminConfig
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)


class AdminRealtimeSubProvider:
    """Manages admin realtime infrastructure: WebSocket, SSE, collaborative editing.

    Registers realtime services: WebSocket manager, event hub, SSE manager.
    """

    def __init__(self, config: AdminConfig, **kwargs: object) -> None:
        self._config = config
        self._kwargs = kwargs
        self._initialized = False
        self._hub: Any = None
        self._inbox_bridge_wired = False

    @property
    def config(self) -> AdminConfig:
        """Return current admin config."""
        return self._config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register realtime services: WebSocket manager, event hub, SSE manager, collaborative."""
        from lexigram.admin.realtime.sse import AdminEventHub
        from lexigram.admin.realtime.subject_hub import SubjectAdminEventHub
        from lexigram.admin.realtime.ws_handler_registry import WSMessageTypeRegistry
        from lexigram.admin.services.collaborative import CollaborativeEditingService
        from lexigram.admin.services.realtime import RealtimeService
        from lexigram.contracts.core.stores import LockStoreProtocol

        realtime_svc = RealtimeService()

        container.singleton(WSMessageTypeRegistry, WSMessageTypeRegistry())
        container.singleton(RealtimeService, realtime_svc)
        container.singleton(AdminEventHub, AdminEventHub())
        container.singleton(SubjectAdminEventHub, SubjectAdminEventHub())

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
        from lexigram.admin.realtime.sse import AdminEventHub
        from lexigram.contracts.notification.inbox import INBOX_SENT_HOOK
        from lexigram.hooks.ambient import register_action

        try:
            self._hub = await container.resolve(AdminEventHub)
        except Exception:  # noqa: BLE001 — hub is optional
            self._hub = None
            logger.debug("admin_realtime.no_event_hub")

        if self._hub is not None and not self._inbox_bridge_wired:
            register_action(INBOX_SENT_HOOK, self._publish_inbox_sent)
            self._inbox_bridge_wired = True
            logger.info("admin_realtime.inbox_bridge_wired", hook=INBOX_SENT_HOOK)

        self._initialized = True

    async def _publish_inbox_sent(self, **kwargs: Any) -> None:
        """Push an inbox message to the SSE hub for its recipient."""
        if self._hub is None:
            return

        message = kwargs.get("message")
        metadata = getattr(message, "metadata", None)
        level = metadata.get("level", "info") if isinstance(metadata, dict) else "info"

        await self._hub.publish_notification(
            title=kwargs.get("title", "Notification"),
            message=kwargs.get("body", ""),
            level=str(level),
            target_users=[kwargs["user_id"]] if kwargs.get("user_id") else None,
        )

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

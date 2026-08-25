"""Provider for the realtime monitor demo.

Canonical shape: ``register()`` declares bindings (the event-stream factory
derives its knobs from the injected ``demo:`` configuration); ``boot()``
resolves the stream, starts the supervised heartbeat, and stops it in
:meth:`shutdown`. Controllers are plain class bindings — the container
constructs them from their type-hinted dependencies.
"""

from __future__ import annotations

import asyncio

from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.core.health import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
)
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from ops_console.config import RealtimeConfig
from ops_console.controllers.api import ConsoleController, EventsStreamHandler
from ops_console.controllers.operator import OperatorHandler
from ops_console.domain import Severity, SystemEvent
from ops_console.services.event_stream import EventStreamService

HEARTBEAT_EVENTS = (
    ("disk", "disk/root 41%", "info"),
    ("cpu", "load 0.12", "info"),
    ("net", "traffic 1.2 KiB/s", "info"),
)

logger = get_logger(__name__)

__all__ = ["RealtimeProvider"]


class RealtimeProvider(Provider):
    """Provide the shared event stream plus the realtime endpoints."""

    name = "realtime"
    priority = ProviderPriority.COMMS

    config_key: str | None = "demo"
    config_model: type | None = RealtimeConfig

    def __init__(self, config: RealtimeConfig | None = None) -> None:
        super().__init__()
        self._config = config or RealtimeConfig()
        self._stream: EventStreamService | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._stopping = False

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Declare bindings; the router constructs controllers itself."""
        cfg = self.config or RealtimeConfig()

        container.singleton(RealtimeConfig, instance=cfg)
        container.singleton(
            EventStreamService,
            factory=lambda: EventStreamService(
                history_size=cfg.history_size,
                queue_capacity=cfg.queue_capacity,
            ),
        )
        container.singleton(ConsoleController, ConsoleController)
        container.singleton(EventsStreamHandler, EventsStreamHandler)
        container.singleton(OperatorHandler, OperatorHandler)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve the shared stream and start the heartbeat producer."""
        self._stream = await container.resolve(EventStreamService)
        self._start_heartbeat()

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report stream liveness and volume."""
        stats = (
            self._stream.stats()
            if self._stream is not None
            else EventStreamService().stats()
        )
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            category=HealthCheckCategory.READINESS,
            details={
                "subscribers": stats.subscribers,
                "history": stats.events,
                "stopping": self._stopping,
            },
        )

    def _start_heartbeat(self) -> None:
        """Start the heartbeat producer under done-callback supervision."""
        self._heartbeat_task = asyncio.create_task(self._heartbeat())
        self._heartbeat_task.add_done_callback(self._on_heartbeat_done)

    def _on_heartbeat_done(self, task: asyncio.Task[None]) -> None:
        """Log unexpected heartbeat death and restart unless shutting down."""
        if task.cancelled() or self._stopping:
            return
        exc = task.exception()
        if exc is not None:
            logger.error("heartbeat_task_died", error=str(exc))
            self._start_heartbeat()

    async def _heartbeat(self) -> None:
        """Emit a rotating heartbeat event every interval until shutdown."""
        assert self._stream is not None  # booted before heartbeat starts
        index = 0
        while True:
            await asyncio.sleep(self._config.heartbeat_interval_seconds)
            kind = HEARTBEAT_EVENTS[index % len(HEARTBEAT_EVENTS)]
            index += 1
            await self._stream.publish(
                SystemEvent(
                    kind=kind[0],
                    message=kind[1],
                    severity=Severity.from_name(kind[2]),
                    source="heartbeat",
                )
            )

    async def shutdown(self) -> None:
        """Cancel the heartbeat producer cleanly."""
        self._stopping = True
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

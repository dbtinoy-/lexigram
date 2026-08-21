"""Provider for the realtime monitor demo.

Registers the event stream service and its streaming entry points, then on
boot wires the WebSocket operator route (appended after the web layer boots)
and starts a background heartbeat producer so dashboards see live traffic
even before anyone publishes a manual event.
"""

from __future__ import annotations

import asyncio

from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from ops_console.controllers.console import EventsStreamHandler
from ops_console.controllers.operator import OperatorHandler
from ops_console.domain import Severity, SystemEvent
from ops_console.services.event_stream import EventStreamService

HEARTBEAT_EVENTS = (
    ("disk", "disk/root 41%", "info"),
    ("cpu", "load 0.12", "info"),
    ("net", "traffic 1.2 KiB/s", "info"),
)

logger = get_logger(__name__)


class RealtimeProvider(Provider):
    """Provide the shared event stream plus the realtime endpoints."""

    name = "realtime"
    priority = ProviderPriority.COMMS

    def __init__(self, heartbeat_interval: float = 15.0) -> None:
        super().__init__()
        self.heartbeat_interval = heartbeat_interval
        self.events = EventStreamService()
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._stopping = False

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(EventStreamService, self.events)
        container.singleton(EventsStreamHandler, EventsStreamHandler(self.events))
        container.singleton(OperatorHandler, OperatorHandler(self.events))

    def _make_endpoint(self, container: ContainerResolverProtocol):
        """Build the ASGI endpoint that wraps the operator WebSocket handler."""

        async def endpoint(starlette_ws) -> None:
            from lexigram.web import WebSocket

            ws = WebSocket(starlette_ws)
            handler = await container.resolve(OperatorHandler)
            await handler.handle(ws)

        return endpoint

    async def boot(self, container: ContainerResolverProtocol) -> None:
        from starlette.routing import WebSocketRoute

        from lexigram.web.di.provider import WebProvider

        web = await container.resolve(WebProvider)
        if web.starlette is not None:
            web.starlette.router.routes.append(
                WebSocketRoute("/api/ws/operator", self._make_endpoint(container))
            )
        self._start_heartbeat()

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
        index = 0
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            kind = HEARTBEAT_EVENTS[index % len(HEARTBEAT_EVENTS)]
            index += 1
            await self.events.publish(
                SystemEvent(
                    kind=kind[0],
                    message=kind[1],
                    severity=Severity.from_name(kind[2]),
                    source="heartbeat",
                )
            )

    async def shutdown(self) -> None:
        self._stopping = True
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None


__all__ = ["RealtimeProvider"]

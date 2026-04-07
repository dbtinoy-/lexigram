"""Real-time Data Service - WebSocket and SSE support for live updates."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from lexigram.serialization import dumps_str, loads_str

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class UpdateType(StrEnum):
    """Types of real-time updates."""

    METRIC = "metric"
    CHART = "chart"
    TABLE = "table"
    NOTIFICATION = "notification"
    CUSTOM = "custom"


@dataclass
class RealtimeUpdate:
    """Real-time update message."""

    type: UpdateType
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    target: str = ""  # Target element ID

    def to_json(self) -> str:
        """Serialize to JSON."""
        return dumps_str(
            {
                "type": self.type.value,
                "data": self.data,
                "timestamp": self.timestamp.isoformat(),
                "target": self.target,
            },
        )

    @classmethod
    def from_json(cls, data: str) -> RealtimeUpdate:
        """Deserialize from JSON."""
        obj = loads_str(data)
        return cls(
            type=UpdateType(obj["type"]),
            data=obj["data"],
            timestamp=datetime.fromisoformat(obj["timestamp"]),
            target=obj.get("target", ""),
        )


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        self.active_connections: dict[str, Any] = {}
        self.subscriptions: dict[str, set[str]] = {}  # topic -> set of connection_ids

    async def connect(self, connection_id: str, websocket: Any) -> None:
        """Connect a WebSocket client."""
        self.active_connections[connection_id] = websocket

    def disconnect(self, connection_id: str) -> None:
        """Disconnect a WebSocket client."""
        self.active_connections.pop(connection_id, None)
        # Remove from all subscriptions
        for topic_subs in self.subscriptions.values():
            topic_subs.discard(connection_id)

    def subscribe(self, connection_id: str, topic: str) -> None:
        """Subscribe a connection to a topic."""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()
        self.subscriptions[topic].add(connection_id)

    def unsubscribe(self, connection_id: str, topic: str) -> None:
        """Unsubscribe a connection from a topic."""
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(connection_id)

    async def send_personal(self, connection_id: str, message: str) -> None:
        """Send message to specific connection."""
        websocket = self.active_connections.get(connection_id)
        if websocket:
            try:
                await websocket.send_text(message)
            except (ConnectionError, OSError, RuntimeError) as e:
                from lexigram.logging import get_logger

                logger = get_logger(__name__)
                logger.debug(
                    "Error sending message to connection %s: %s",
                    connection_id,
                    e,
                )
                # Ensure the faulty connection is removed
                self.disconnect(connection_id)

    async def broadcast(self, message: str, topic: str | None = None) -> None:
        """Broadcast message to all connections or specific topic."""
        if topic and topic in self.subscriptions:
            targets = self.subscriptions[topic]
        else:
            targets = set(self.active_connections.keys())

        for connection_id in list(targets):
            await self.send_personal(connection_id, message)

    def get_connection_count(self, topic: str | None = None) -> int:
        """Get number of active connections."""
        if topic:
            return len(self.subscriptions.get(topic, set()))
        return len(self.active_connections)


class RealtimeService:
    """DI-injectable real-time data service."""

    def __init__(self) -> None:
        """Initialize real-time service."""
        self.connection_manager = ConnectionManager()
        self.update_handlers: dict[
            str,
            Callable[[RealtimeUpdate], Awaitable[None]],
        ] = {}

    async def connect(self, connection_id: str, websocket: Any) -> None:
        """Connect a WebSocket client."""
        await self.connection_manager.connect(connection_id, websocket)

    def disconnect(self, connection_id: str) -> None:
        """Disconnect a WebSocket client."""
        self.connection_manager.disconnect(connection_id)

    def subscribe(self, connection_id: str, topic: str) -> None:
        """Subscribe connection to topic."""
        self.connection_manager.subscribe(connection_id, topic)

    def unsubscribe(self, connection_id: str, topic: str) -> None:
        """Unsubscribe connection from topic."""
        self.connection_manager.unsubscribe(connection_id, topic)

    async def send_update(
        self,
        update: RealtimeUpdate,
        connection_id: str | None = None,
        topic: str | None = None,
    ) -> None:
        """
        Send real-time update.

        Args:
            update: Update to send
            connection_id: Send to specific connection (optional)
            topic: Broadcast to topic (optional)
        """
        message = update.to_json()

        if connection_id:
            await self.connection_manager.send_personal(connection_id, message)
        else:
            await self.connection_manager.broadcast(message, topic)

    async def send_metric_update(
        self,
        metric_name: str,
        value: Any,
        target: str = "",
        topic: str | None = None,
    ) -> None:
        """Send metric update."""
        update = RealtimeUpdate(
            type=UpdateType.METRIC,
            data={"name": metric_name, "value": value},
            target=target,
        )
        await self.send_update(update, topic=topic)

    async def send_chart_update(
        self,
        chart_data: dict[str, Any],
        target: str = "",
        topic: str | None = None,
    ) -> None:
        """Send chart data update."""
        update = RealtimeUpdate(type=UpdateType.CHART, data=chart_data, target=target)
        await self.send_update(update, topic=topic)

    async def send_notification(
        self,
        message: str,
        severity: str = "info",
        topic: str | None = None,
    ) -> None:
        """Send notification."""
        update = RealtimeUpdate(
            type=UpdateType.NOTIFICATION,
            data={"message": message, "severity": severity},
        )
        await self.send_update(update, topic=topic)

    def register_handler(
        self,
        update_type: UpdateType,
        handler: Callable[[RealtimeUpdate], Awaitable[None]],
    ) -> None:
        """Register update handler."""
        self.update_handlers[update_type.value] = handler

    async def handle_update(self, update: RealtimeUpdate) -> None:
        """Handle incoming update."""
        handler = self.update_handlers.get(update.type.value)
        if handler:
            await handler(update)

    def get_stats(self) -> dict[str, Any]:
        """Get service statistics."""
        return {
            "total_connections": self.connection_manager.get_connection_count(),
            "topics": {
                topic: self.connection_manager.get_connection_count(topic)
                for topic in self.connection_manager.subscriptions
            },
            "handlers": list(self.update_handlers.keys()),
        }


class SSEEmitter:
    """Server-Sent Events emitter as fallback."""

    def __init__(self) -> None:
        """Initialize SSE emitter."""
        self.clients: dict[str, asyncio.Queue] = {}

    def connect(self, client_id: str) -> asyncio.Queue:
        """Connect SSE client."""
        queue: asyncio.Queue = asyncio.Queue()
        self.clients[client_id] = queue
        return queue

    def disconnect(self, client_id: str) -> None:
        """Disconnect SSE client."""
        self.clients.pop(client_id, None)

    async def emit(
        self,
        event: str,
        data: dict[str, Any],
        client_id: str | None = None,
    ) -> None:
        """Emit SSE event."""
        # Prepare message payload, logging failures to serialize
        try:
            payload = dumps_str(data)
        except (TypeError, ValueError):
            from lexigram.logging import get_logger

            logger = get_logger(__name__)
            logger.exception("Failed to JSON-serialize SSE data for event %s", event)
            payload = str(data)

        message = f"event: {event}\ndata: {payload}\n\n"

        if client_id and client_id in self.clients:
            try:
                await self.clients[client_id].put(message)
            except RuntimeError:
                from lexigram.logging import get_logger

                logger = get_logger(__name__)
                logger.exception("Failed to put message on client queue %s", client_id)
        else:
            # Broadcast to all
            for queue in list(self.clients.values()):
                try:
                    await queue.put(message)
                except (RuntimeError, OSError) as e:
                    from lexigram.logging import get_logger

                    logger = get_logger(__name__)
                    logger.debug("Failed to put message on broadcast queue: %s", e)

    def get_client_count(self) -> int:
        """Get number of connected clients."""
        return len(self.clients)

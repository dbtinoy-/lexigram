"""WebSocket support for lexigram-admin real-time updates.

This module provides WebSocket handlers for bidirectional
real-time communication in admin.

INT-03: WebSocket support for real-time updates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.realtime.messages import WSMessage, WSMessageType

if TYPE_CHECKING:
    from collections.abc import Callable


# ============================================================================
# Protocols for optional web integration
# ============================================================================

# Placeholder types for when lexigram-web is not available
# These are replaced via container registration when lexigram-web is present


class WebSocket:
    """Base WebSocket protocol.

    This is a local implementation that does not depend on lexigram-web.
    When lexigram-web is available, its WebSocket is registered in the container
    and resolved through IoC.
    """

    async def send(self, data: str) -> None:
        """Send data through WebSocket."""

    async def receive(self) -> str:
        """Receive data from WebSocket."""
        return ""


class WebSocketHandler:
    """Base WebSocket handler class.

    Subclass this to implement WebSocket handlers.
    """

    async def on_connect(self, websocket: WebSocket) -> None:
        """Called when a client connects."""

    async def on_disconnect(self, websocket: WebSocket) -> None:
        """Called when a client disconnects."""

    async def on_message(self, websocket: WebSocket, message: str) -> None:
        """Called when a message is received."""


# ============================================================================
# Connection Manager
# ============================================================================


class AdminWebSocketManager:
    """Manager for admin WebSocket connections.

    Handles connection tracking, subscriptions, and message routing.
    Delegates connection state management to ConnectionTracker.

    Example:
        >>> manager = AdminWebSocketManager()
        >>> await manager.connect(websocket, user_id=1)
        >>> await manager.subscribe(websocket, resources=["users"])
        >>> await manager.broadcast(message, resource="users")
    """

    def __init__(self, tracker: Any | None = None) -> None:
        """Initialize the manager.

        Args:
            tracker: Optional ConnectionTracker instance. Creates one if not provided.
        """
        from lexigram.admin.realtime.connection_tracker import ConnectionTracker

        self._tracker = tracker or ConnectionTracker()

    async def connect(
        self,
        websocket: Any,
        user_id: Any | None = None,
    ) -> str:
        """Register a new connection.

        Args:
            websocket: WebSocket connection
            user_id: Optional user ID

        Returns:
            Connection ID
        """
        return await self._tracker.connect(websocket, user_id)

    async def disconnect(self, connection_id: str) -> None:
        """Unregister a connection.

        Args:
            connection_id: Connection to remove
        """
        await self._tracker.disconnect(connection_id)

    async def subscribe(
        self,
        connection_id: str,
        resources: list[str],
    ) -> None:
        """Subscribe connection to resources.

        Args:
            connection_id: Connection ID
            resources: List of resource types to subscribe to
        """
        await self._tracker.subscribe(connection_id, resources)

    async def unsubscribe(
        self,
        connection_id: str,
        resources: list[str],
    ) -> None:
        """Unsubscribe connection from resources.

        Args:
            connection_id: Connection ID
            resources: List of resource types to unsubscribe from
        """
        await self._tracker.unsubscribe(connection_id, resources)

    async def send(
        self,
        connection_id: str,
        message: WSMessage | dict[str, Any],
    ) -> bool:
        """Send message to specific connection.

        Args:
            connection_id: Target connection
            message: Message to send

        Returns:
            True if sent successfully
        """
        websocket = self._tracker.get_connection(connection_id)
        if not websocket:
            return False

        try:
            data = message.to_dict() if isinstance(message, WSMessage) else message
            await websocket.send_json(data)
            return True
        except (RuntimeError, ValueError, OSError):
            return False

    async def broadcast(
        self,
        message: WSMessage | dict[str, Any],
        resource: str | None = None,
        user_ids: list[Any] | None = None,
        exclude_connections: list[str] | None = None,
    ) -> int:
        """Broadcast message to connections.

        Args:
            message: Message to broadcast
            resource: Optional resource filter
            user_ids: Optional user IDs to target
            exclude_connections: Connection IDs to exclude

        Returns:
            Number of connections that received the message
        """
        target_connections = self._tracker.resolve_targets(
            resource=resource,
            user_ids=user_ids,
            exclude_connections=exclude_connections,
        )

        sent = 0
        for conn_id in target_connections:
            if await self.send(conn_id, message):
                sent += 1

        return sent

    async def send_to_user(
        self,
        user_id: Any,
        message: WSMessage | dict[str, Any],
    ) -> int:
        """Send message to all connections of a user.

        Args:
            user_id: Target user
            message: Message to send

        Returns:
            Number of connections that received the message
        """
        return await self.broadcast(message, user_ids=[user_id])

    @property
    def connection_count(self) -> int:
        """Get total number of connections."""
        return self._tracker.connection_count

    def get_user_connection_count(self, user_id: Any) -> int:
        """Get number of connections for a user."""
        return self._tracker.get_user_connection_count(user_id)


HAS_WEBSOCKET = True  # local placeholder is always available

# ============================================================================
# Admin WebSocket Handler
# ============================================================================


class AdminWebSocketHandler(WebSocketHandler if HAS_WEBSOCKET else object):  # type: ignore[misc]
    """WebSocket handler for admin real-time updates.

    Handles:
    - Subscription management for resources
    - Real-time event broadcasting
    - Client actions (HTMX-like operations)

    Usage with lexigram.web:
        >>> @websocket_handler("/admin/ws")
        ... class AdminWSEndpoint(AdminWebSocketHandler):
        ...     pass
    """

    ping_interval: int = 30
    ping_timeout: int = 10

    def __init__(self) -> None:
        if HAS_WEBSOCKET:
            super().__init__()
        self._manager = AdminWebSocketManager()
        self._connection_ids: dict[Any, str] = {}  # websocket -> connection_id
        self._action_handlers: dict[str, Callable[..., Any]] = {}

    def register_action(
        self,
        action_name: str,
        handler: Callable[..., Any],
    ) -> None:
        """Register an action handler.

        Args:
            action_name: Name of the action
            handler: Async function to handle the action
        """
        self._action_handlers[action_name] = handler

    async def on_connect(self, websocket: Any) -> None:
        """Handle WebSocket connection."""
        await websocket.accept()

        # Get user from websocket state/scope
        user = getattr(websocket, "user", None)
        if not user and hasattr(websocket, "scope"):
            user = websocket.scope.get("user")

        user_id = getattr(user, "id", None) if user else None

        connection_id = await self._manager.connect(websocket, user_id)
        self._connection_ids[websocket] = connection_id

        # Send welcome message
        await websocket.send_json(
            WSMessage(
                type=WSMessageType.ACK,
                data={
                    "connection_id": connection_id,
                    "message": "Connected to admin WebSocket",
                },
            ).to_dict(),
        )

    async def on_message(self, websocket: Any, message: dict[str, Any]) -> None:
        """Handle incoming WebSocket message."""
        connection_id = self._connection_ids.get(websocket)
        if not connection_id:
            return

        try:
            msg = WSMessage.from_dict(message)

            from lexigram.admin.realtime.ws_handler_registry import (
                get_ws_message_type_registry,
            )

            registry = get_ws_message_type_registry()
            await registry.handle_message(
                msg.type,
                websocket,
                msg,
                connection_id,
                self._manager,
            )

        except (RuntimeError, ValueError, OSError) as e:
            await websocket.send_json(
                WSMessage(
                    type=WSMessageType.ERROR,
                    data={"message": str(e)},
                ).to_dict(),
            )

    async def _handle_action(self, websocket: Any, msg: WSMessage) -> None:
        """Handle an action request."""
        action_name = msg.data.get("action")
        if not action_name:
            await websocket.send_json(
                WSMessage(
                    type=WSMessageType.ERROR,
                    data={"message": "Action name required"},
                    id=msg.id,
                ).to_dict(),
            )
            return

        handler = self._action_handlers.get(action_name)
        if not handler:
            await websocket.send_json(
                WSMessage(
                    type=WSMessageType.ERROR,
                    data={"message": f"Unknown action: {action_name}"},
                    id=msg.id,
                ).to_dict(),
            )
            return

        try:
            result = await handler(msg.data)
            await websocket.send_json(
                WSMessage(
                    type=WSMessageType.ACK,
                    data={"result": result},
                    id=msg.id,
                ).to_dict(),
            )
        except (RuntimeError, ValueError, OSError) as e:
            await websocket.send_json(
                WSMessage(
                    type=WSMessageType.ERROR,
                    data={"message": str(e)},
                    id=msg.id,
                ).to_dict(),
            )

    async def on_disconnect(self, websocket: Any) -> None:
        """Handle WebSocket disconnection."""
        connection_id = self._connection_ids.pop(websocket, None)
        if connection_id:
            await self._manager.disconnect(connection_id)


# ============================================================================
# Resource Change Notifier
# ============================================================================


class ResourceChangeNotifier:
    """Notifies WebSocket clients of resource changes.

    Integrate with your data layer to automatically notify
    clients when resources are created, updated, or deleted.

    Example:
        >>> notifier = ResourceChangeNotifier()
        >>>
        >>> # After creating a user
        >>> await notifier.notify_created("users", user.id, user.to_dict())
    """

    def __init__(self, manager: AdminWebSocketManager | None = None):
        self._manager = manager or AdminWebSocketManager()

    async def notify_created(
        self,
        resource: str,
        resource_id: Any,
        data: dict[str, Any] | None = None,
    ) -> int:
        """Notify clients of resource creation."""
        message = WSMessage(
            type=WSMessageType.EVENT,
            data={
                "event": "resource.created",
                "resource": resource,
                "resource_id": resource_id,
                "data": data,
            },
        )
        return await self._manager.broadcast(message, resource=resource)

    async def notify_updated(
        self,
        resource: str,
        resource_id: Any,
        changes: dict[str, Any] | None = None,
    ) -> int:
        """Notify clients of resource update."""
        message = WSMessage(
            type=WSMessageType.EVENT,
            data={
                "event": "resource.updated",
                "resource": resource,
                "resource_id": resource_id,
                "changes": changes,
            },
        )
        return await self._manager.broadcast(message, resource=resource)

    async def notify_deleted(
        self,
        resource: str,
        resource_id: Any,
    ) -> int:
        """Notify clients of resource deletion."""
        message = WSMessage(
            type=WSMessageType.EVENT,
            data={
                "event": "resource.deleted",
                "resource": resource,
                "resource_id": resource_id,
            },
        )
        return await self._manager.broadcast(message, resource=resource)

    async def notify_bulk_progress(
        self,
        resource: str,
        operation_id: str,
        progress: dict[str, Any],
    ) -> int:
        """Notify clients of bulk operation progress."""
        message = WSMessage(
            type=WSMessageType.EVENT,
            data={
                "event": "bulk.progress",
                "resource": resource,
                "operation_id": operation_id,
                "progress": progress,
            },
        )
        return await self._manager.broadcast(message, resource=resource)


__all__ = [
    # Flags
    "HAS_WEBSOCKET",
    # Handler
    "AdminWebSocketHandler",
    # Manager
    "AdminWebSocketManager",
    # Notifier
    "ResourceChangeNotifier",
    "WSMessage",
    # Message types
    "WSMessageType",
]

"""ConnectionTracker — extracted connection and subscription state management."""

from __future__ import annotations

from typing import Any


class ConnectionTracker:
    """Tracks WebSocket connections, user mappings, and resource subscriptions.

    Extracted from AdminWebSocketManager to separate connection state
    management from message sending and broadcasting logic.
    """

    def __init__(self) -> None:
        self._connections: dict[str, Any] = {}
        self._user_connections: dict[Any, set[str]] = {}
        self._resource_subscriptions: dict[str, set[str]] = {}
        self._connection_resources: dict[str, set[str]] = {}
        self._connection_users: dict[str, Any] = {}

    def _generate_connection_id(self) -> str:
        """Generate unique connection ID."""
        import uuid

        return str(uuid.uuid4())[:12]

    async def connect(
        self,
        websocket: Any,
        user_id: Any | None = None,
    ) -> str:
        """Register a new connection and return its ID."""
        connection_id = self._generate_connection_id()
        self._connections[connection_id] = websocket
        self._connection_resources[connection_id] = set()

        if user_id:
            self._connection_users[connection_id] = user_id
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(connection_id)

        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        """Unregister a connection and clean up all state."""
        if connection_id in self._connection_resources:
            for resource in self._connection_resources[connection_id]:
                if resource in self._resource_subscriptions:
                    self._resource_subscriptions[resource].discard(connection_id)
            del self._connection_resources[connection_id]

        if connection_id in self._connection_users:
            user_id = self._connection_users[connection_id]
            if user_id in self._user_connections:
                self._user_connections[user_id].discard(connection_id)
            del self._connection_users[connection_id]

        self._connections.pop(connection_id, None)

    async def subscribe(
        self,
        connection_id: str,
        resources: list[str],
    ) -> None:
        """Subscribe connection to resources."""
        for resource in resources:
            if resource not in self._resource_subscriptions:
                self._resource_subscriptions[resource] = set()
            self._resource_subscriptions[resource].add(connection_id)
            if connection_id in self._connection_resources:
                self._connection_resources[connection_id].add(resource)

    async def unsubscribe(
        self,
        connection_id: str,
        resources: list[str],
    ) -> None:
        """Unsubscribe connection from resources."""
        for resource in resources:
            if resource in self._resource_subscriptions:
                self._resource_subscriptions[resource].discard(connection_id)
            if connection_id in self._connection_resources:
                self._connection_resources[connection_id].discard(resource)

    def get_connection(self, connection_id: str) -> Any | None:
        """Get websocket for a connection ID."""
        return self._connections.get(connection_id)

    def get_resource_subscribers(self, resource: str) -> set[str]:
        """Get connection IDs subscribed to a resource."""
        return set(self._resource_subscriptions.get(resource, set()))

    def get_connection_resources(self, connection_id: str) -> set[str]:
        """Get resources a connection is subscribed to."""
        return set(self._connection_resources.get(connection_id, set()))

    def get_user_connection_count(self, user_id: Any) -> int:
        """Get number of connections for a user."""
        return len(self._user_connections.get(user_id, set()))

    @property
    def connection_count(self) -> int:
        """Total number of active connections."""
        return len(self._connections)

    def resolve_targets(
        self,
        resource: str | None = None,
        user_ids: list[Any] | None = None,
        exclude_connections: list[str] | None = None,
    ) -> set[str]:
        """Resolve target connection IDs based on filters."""
        exclude = set(exclude_connections or [])
        targets: set[str] = set()

        if user_ids:
            for user_id in user_ids:
                if user_id in self._user_connections:
                    targets.update(self._user_connections[user_id])
        elif resource:
            targets.update(self._resource_subscriptions.get(resource, set()))
        else:
            targets.update(self._connections.keys())

        return targets - exclude

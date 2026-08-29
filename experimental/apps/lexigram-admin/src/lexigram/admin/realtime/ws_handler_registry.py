"""WebSocket message handler registry for real-time communication."""

from __future__ import annotations

from typing import Any, Protocol


class WSMessageHandler(Protocol):
    """Protocol for WebSocket message handlers."""

    async def handle(
        self,
        websocket: Any,
        msg: Any,
        connection_id: str,
        manager: Any,
    ) -> None:
        """Handle the WebSocket message."""
        ...


class PingHandler:
    """Handler for PING messages."""

    async def handle(
        self,
        websocket: Any,
        msg: Any,
        connection_id: str,
        manager: Any,
    ) -> None:
        from lexigram.admin.realtime.websocket import WSMessage, WSMessageType

        await websocket.send_json(
            WSMessage(
                type=WSMessageType.PONG,
                id=msg.id,
            ).to_dict(),
        )


class SubscribeHandler:
    """Handler for SUBSCRIBE messages."""

    async def handle(
        self,
        websocket: Any,
        msg: Any,
        connection_id: str,
        manager: Any,
    ) -> None:
        from lexigram.admin.realtime.websocket import WSMessage, WSMessageType

        resources = msg.data.get("resources", [])
        await manager.subscribe(connection_id, resources)
        await websocket.send_json(
            WSMessage(
                type=WSMessageType.ACK,
                data={"subscribed": resources},
                id=msg.id,
            ).to_dict(),
        )


class UnsubscribeHandler:
    """Handler for UNSUBSCRIBE messages."""

    async def handle(
        self,
        websocket: Any,
        msg: Any,
        connection_id: str,
        manager: Any,
    ) -> None:
        from lexigram.admin.realtime.websocket import WSMessage, WSMessageType

        resources = msg.data.get("resources", [])
        await manager.unsubscribe(connection_id, resources)
        await websocket.send_json(
            WSMessage(
                type=WSMessageType.ACK,
                data={"unsubscribed": resources},
                id=msg.id,
            ).to_dict(),
        )


class ActionHandler:
    """Handler for ACTION messages."""

    async def handle(
        self,
        websocket: Any,
        msg: Any,
        connection_id: str,
        manager: Any,
    ) -> None:
        from lexigram.admin.realtime.websocket import WebSocketHandler

        handler = WebSocketHandler(manager)  # type: ignore[call-arg]
        await handler._handle_action(websocket, msg)  # type: ignore[attr-defined]


class WSMessageTypeRegistry:
    """Central registry for WebSocket message type handlers."""

    def __init__(self) -> None:
        self._handlers: dict[Any, WSMessageHandler] = {}

    @classmethod
    def _default_entries(cls) -> dict[Any, WSMessageHandler]:
        """Declare the built-in WebSocket message handlers."""
        from lexigram.admin.realtime.websocket import WSMessageType

        return {
            WSMessageType.PING: PingHandler(),
            WSMessageType.SUBSCRIBE: SubscribeHandler(),
            WSMessageType.UNSUBSCRIBE: UnsubscribeHandler(),
            WSMessageType.ACTION: ActionHandler(),
        }

    @classmethod
    def with_defaults(cls) -> WSMessageTypeRegistry:
        """Return a new instance with default message handlers registered."""
        registry = cls()
        for key, handler in cls._default_entries().items():
            registry.register(key, handler)
        return registry

    def register(self, msg_type: Any, handler: WSMessageHandler) -> None:
        """Register a new message handler."""
        self._handlers[msg_type] = handler

    async def handle_message(
        self,
        msg_type: Any,
        websocket: Any,
        msg: Any,
        connection_id: str,
        manager: Any,
    ) -> None:
        """Handle a message using the appropriate handler."""
        handler = self._handlers.get(msg_type)
        if handler:
            await handler.handle(websocket, msg, connection_id, manager)


_ws_message_type_registry = WSMessageTypeRegistry.with_defaults()


def get_ws_message_type_registry() -> WSMessageTypeRegistry:
    """Get the global WebSocket message type registry."""
    return _ws_message_type_registry
